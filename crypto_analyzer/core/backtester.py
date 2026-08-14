import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from core.indicators import TechnicalIndicators
from core.scorer import AnalysisScorer

@dataclass
class Trade:
    trade_id: int
    symbol: str
    entry_time: pd.Timestamp
    entry_price: float
    entry_score: float
    exit_time: Optional[pd.Timestamp] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    quantity: float = 0.0
    pnl: float = 0.0
    pnl_pct: float = 0.0
    fee_paid: float = 0.0
    duration_candles: int = 0
    is_open: bool = True

@dataclass
class BacktestConfig:
    initial_capital: float = 1000.0
    position_size_pct: float = 100.0  # Portföyün % kaçı ile pozisyona girilsin
    commission_pct: float = 0.1       # Borsa alım/satım komisyonu (%)
    entry_score_threshold: int = 65   # Pozisyona giriş için minimum skor
    exit_score_threshold: int = 40    # Pozisyondan çıkış için skor eşiği
    take_profit_pct: Optional[float] = None   # Örn: 5.0 (%5 Kâr Al)
    stop_loss_pct: Optional[float] = None     # Örn: 3.0 (%3 Zarar Durdur)
    trailing_stop_pct: Optional[float] = None # Örn: 2.0 (%2 İz Süren Stop)

@dataclass
class BacktestResult:
    symbol: str
    timeframe: str
    config: BacktestConfig
    initial_capital: float
    final_capital: float
    net_profit: float
    net_profit_pct: float
    buy_and_hold_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown_pct: float
    max_drawdown_usd: float
    avg_trade_pct: float
    avg_win_pct: float
    avg_loss_pct: float
    risk_reward_ratio: float
    sharpe_ratio: float
    trades: List[Trade] = field(default_factory=list)
    trades_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    equity_curve: pd.DataFrame = field(default_factory=pd.DataFrame)

class Backtester:
    def __init__(self, config: Optional[BacktestConfig] = None):
        self.config = config or BacktestConfig()
        self.scorer = AnalysisScorer()

    def run(self, df: pd.DataFrame, symbol: str = "BTC/USDT", timeframe: str = "4h") -> BacktestResult:
        """
        Verilen OHLCV verisi üzerinde simülasyonu çalıştırır ve metrikleri hesaplar.
        """
        if df.empty or len(df) < 50:
            raise ValueError("Backtest için en az 50 mumluk veri gereklidir.")

        # 1. İndikatörleri ekle
        df = df.copy()
        df = TechnicalIndicators.add_all_indicators(df)

        # 2. Simülasyon Değişkenleri
        capital = self.config.initial_capital
        commission_rate = self.config.commission_pct / 100.0
        
        trades: List[Trade] = []
        current_trade: Optional[Trade] = None
        trade_counter = 0
        peak_price = 0.0

        equity_history = []
        first_close = df.iloc[49]['close']

        # 3. Mum mum simülasyon (İlk 49 mum indikatör ısınması)
        for i in range(49, len(df)):
            row = df.iloc[i]
            timestamp = row['timestamp']
            close_price = row['close']
            high_price = row['high']
            low_price = row['low']

            # Mevcut mumun skorunu hesapla
            eval_result = self.scorer.evaluate(symbol, close_price, row)
            score = eval_result['score']

            # Pozisyonda mıyız?
            if current_trade is not None:
                current_trade.duration_candles += 1
                entry_p = current_trade.entry_price
                if high_price > peak_price:
                    peak_price = high_price

                exit_triggered = False
                exit_price = close_price
                exit_reason = ""

                # A) Stop-Loss Kontrolü
                if self.config.stop_loss_pct is not None:
                    sl_price = entry_p * (1.0 - (self.config.stop_loss_pct / 100.0))
                    if low_price <= sl_price:
                        exit_triggered = True
                        exit_price = sl_price
                        exit_reason = f"Stop Loss (%{self.config.stop_loss_pct})"

                # B) Take-Profit Kontrolü (SL tetiklenmediyse)
                if not exit_triggered and self.config.take_profit_pct is not None:
                    tp_price = entry_p * (1.0 + (self.config.take_profit_pct / 100.0))
                    if high_price >= tp_price:
                        exit_triggered = True
                        exit_price = tp_price
                        exit_reason = f"Take Profit (%{self.config.take_profit_pct})"

                # C) Trailing Stop Kontrolü
                if not exit_triggered and self.config.trailing_stop_pct is not None:
                    trail_price = peak_price * (1.0 - (self.config.trailing_stop_pct / 100.0))
                    if low_price <= trail_price and trail_price > entry_p:
                        exit_triggered = True
                        exit_price = trail_price
                        exit_reason = f"Trailing Stop (%{self.config.trailing_stop_pct})"

                # D) Skor Bazlı Çıkış (Sinyal Zayıflaması)
                if not exit_triggered and score <= self.config.exit_score_threshold:
                    exit_triggered = True
                    exit_price = close_price
                    exit_reason = f"Sinyal Çıkışı (Skor: {score})"

                # Çıkış işlemi yap
                if exit_triggered:
                    gross_return = current_trade.quantity * exit_price
                    exit_fee = gross_return * commission_rate
                    net_return = gross_return - exit_fee
                    
                    pnl = net_return - (current_trade.quantity * entry_p)
                    pnl_pct = ((exit_price - entry_p) / entry_p) * 100.0 - (self.config.commission_pct * 2)
                    
                    capital += net_return
                    current_trade.exit_time = timestamp
                    current_trade.exit_price = round(exit_price, 4)
                    current_trade.exit_reason = exit_reason
                    current_trade.pnl = round(pnl, 2)
                    current_trade.pnl_pct = round(pnl_pct, 2)
                    current_trade.fee_paid += round(exit_fee, 2)
                    current_trade.is_open = False

                    trades.append(current_trade)
                    current_trade = None
                    peak_price = 0.0

            else:
                # Pozisyonda değiliz - Giriş Şartını Kontrol Et
                if score >= self.config.entry_score_threshold:
                    trade_capital = capital * (self.config.position_size_pct / 100.0)
                    entry_fee = trade_capital * commission_rate
                    usable_capital = trade_capital - entry_fee
                    quantity = usable_capital / close_price

                    capital -= trade_capital
                    trade_counter += 1

                    current_trade = Trade(
                        trade_id=trade_counter,
                        symbol=symbol,
                        entry_time=timestamp,
                        entry_price=round(close_price, 4),
                        entry_score=score,
                        quantity=quantity,
                        fee_paid=round(entry_fee, 2),
                        is_open=True
                    )
                    peak_price = close_price

            # Anlık portföy değerini hesapla
            current_portfolio_value = capital
            if current_trade is not None:
                current_portfolio_value += current_trade.quantity * close_price

            # Buy & Hold değer karşılaştırması
            bnh_value = (self.config.initial_capital / first_close) * close_price

            equity_history.append({
                'timestamp': timestamp,
                'equity': round(current_portfolio_value, 2),
                'buy_and_hold': round(bnh_value, 2),
                'close': close_price,
                'in_position': 1 if current_trade is not None else 0
            })

        # Son mumda açık kalan pozisyon varsa son fiyatla kapat
        if current_trade is not None:
            last_row = df.iloc[-1]
            last_close = last_row['close']
            gross_return = current_trade.quantity * last_close
            exit_fee = gross_return * commission_rate
            net_return = gross_return - exit_fee
            pnl = net_return - (current_trade.quantity * current_trade.entry_price)
            pnl_pct = ((last_close - current_trade.entry_price) / current_trade.entry_price) * 100.0 - (self.config.commission_pct * 2)
            
            capital += net_return
            current_trade.exit_time = last_row['timestamp']
            current_trade.exit_price = round(last_close, 4)
            current_trade.exit_reason = "Simülasyon Sonu (Açık)"
            current_trade.pnl = round(pnl, 2)
            current_trade.pnl_pct = round(pnl_pct, 2)
            current_trade.fee_paid += round(exit_fee, 2)
            current_trade.is_open = False
            trades.append(current_trade)

        # 4. Performans Metriklerini Hesapla
        equity_df = pd.DataFrame(equity_history)
        return self._calculate_metrics(symbol, timeframe, equity_df, trades, first_close, df.iloc[-1]['close'])

    def _calculate_metrics(self, symbol: str, timeframe: str, equity_df: pd.DataFrame, trades: List[Trade], first_price: float, last_price: float) -> BacktestResult:
        final_capital = equity_df['equity'].iloc[-1] if not equity_df.empty else self.config.initial_capital
        net_profit = final_capital - self.config.initial_capital
        net_profit_pct = (net_profit / self.config.initial_capital) * 100.0

        buy_and_hold_pct = ((last_price - first_price) / first_price) * 100.0

        # Drawdown hesaplama
        equity_df['peak'] = equity_df['equity'].cummax()
        equity_df['drawdown'] = (equity_df['equity'] - equity_df['peak']) / equity_df['peak'] * 100.0
        max_dd_pct = abs(equity_df['drawdown'].min()) if not equity_df.empty else 0.0
        max_dd_usd = abs((equity_df['equity'] - equity_df['peak']).min()) if not equity_df.empty else 0.0

        # İşlem İstatistikleri
        total_trades = len(trades)
        winning_trades = [t for t in trades if t.pnl > 0]
        losing_trades = [t for t in trades if t.pnl <= 0]

        win_count = len(winning_trades)
        loss_count = len(losing_trades)
        win_rate = (win_count / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum(t.pnl for t in winning_trades)
        gross_loss = abs(sum(t.pnl for t in losing_trades))

        if gross_loss > 0:
            profit_factor = round(gross_profit / gross_loss, 2)
        elif gross_profit > 0:
            profit_factor = 999.0
        else:
            profit_factor = 0.0

        avg_trade_pct = np.mean([t.pnl_pct for t in trades]) if trades else 0.0
        avg_win_pct = np.mean([t.pnl_pct for t in winning_trades]) if winning_trades else 0.0
        avg_loss_pct = np.mean([t.pnl_pct for t in losing_trades]) if losing_trades else 0.0

        risk_reward_ratio = abs(avg_win_pct / avg_loss_pct) if avg_loss_pct != 0 else 0.0

        # Sharpe Oranı (Periyodik getiriler üzerinden)
        equity_returns = equity_df['equity'].pct_change().dropna()
        if len(equity_returns) > 1 and equity_returns.std() > 0:
            # Yıllıklandırma çarpanı (4h için günde 6 mum * 365 = 2190)
            annual_factor = np.sqrt(2190) if timeframe == '4h' else (np.sqrt(365) if timeframe == '1d' else np.sqrt(8760))
            sharpe_ratio = round((equity_returns.mean() / equity_returns.std()) * annual_factor, 2)
        else:
            sharpe_ratio = 0.0

        # Trade listesini DataFrame'e dönüştür
        trade_rows = []
        for t in trades:
            trade_rows.append({
                '#': t.trade_id,
                'Giriş Zamanı': t.entry_time.strftime('%Y-%m-%d %H:%M') if pd.notnull(t.entry_time) else '-',
                'Giriş ($)': t.entry_price,
                'Giriş Skoru': t.entry_score,
                'Çıkış Zamanı': t.exit_time.strftime('%Y-%m-%d %H:%M') if pd.notnull(t.exit_time) else '-',
                'Çıkış ($)': t.exit_price,
                'Çıkış Nedeni': t.exit_reason,
                'Kâr/Zarar ($)': t.pnl,
                'Getiri (%)': f"%{t.pnl_pct:+.2f}",
                'Komisyon ($)': t.fee_paid,
                'Süre (Mum)': t.duration_candles
            })
        trades_df = pd.DataFrame(trade_rows)

        return BacktestResult(
            symbol=symbol,
            timeframe=timeframe,
            config=self.config,
            initial_capital=round(self.config.initial_capital, 2),
            final_capital=round(final_capital, 2),
            net_profit=round(net_profit, 2),
            net_profit_pct=round(net_profit_pct, 2),
            buy_and_hold_pct=round(buy_and_hold_pct, 2),
            total_trades=total_trades,
            winning_trades=win_count,
            losing_trades=loss_count,
            win_rate=round(win_rate, 2),
            profit_factor=profit_factor,
            max_drawdown_pct=round(max_dd_pct, 2),
            max_drawdown_usd=round(max_dd_usd, 2),
            avg_trade_pct=round(avg_trade_pct, 2),
            avg_win_pct=round(avg_win_pct, 2),
            avg_loss_pct=round(avg_loss_pct, 2),
            risk_reward_ratio=round(risk_reward_ratio, 2),
            sharpe_ratio=sharpe_ratio,
            trades=trades,
            trades_df=trades_df,
            equity_curve=equity_df
        )

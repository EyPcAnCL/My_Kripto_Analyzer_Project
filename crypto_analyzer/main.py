import sys
import argparse

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config.settings import TIMEFRAME, CANDLE_LIMIT
from services.exchange_service import ExchangeService
from core.indicators import TechnicalIndicators
from core.scorer import AnalysisScorer
from core.backtester import Backtester, BacktestConfig
from database.connection import init_db, get_watchlist

init_db()

def run_scanner(symbols=None, timeframe: str = TIMEFRAME, limit: int = CANDLE_LIMIT):
    print("=" * 65)
    print(f"🚀 KRİPTO TEKNİK ANALİZ PİYASA TARAYICISI ({timeframe.upper()})")
    print("=" * 65)
    
    if not symbols:
        symbols = get_watchlist()
        if not symbols:
            symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'PEPE/USDT']

    exchange = ExchangeService(exchange_id='binance')
    scorer = AnalysisScorer()

    for raw_symbol in symbols:
        symbol = ExchangeService.normalize_symbol(raw_symbol)
        df = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        
        if df.empty or len(df) < 50:
            print(f"⚠️ {symbol} için yeterli veri alınamadı, atlanıyor.")
            continue

        df = TechnicalIndicators.add_all_indicators(df)
        last_row = df.iloc[-1]
        current_price = last_row['close']
        
        result = scorer.evaluate(symbol, current_price, last_row)

        print(f"🪙 Parite  : {result['symbol']}")
        print(f"💰 Fiyat   : {result['price']} USDT")
        print(f"📊 Skor    : {result['score']}/100 --> Durum: {result['verdict']}")
        print(f"📈 RSI     : {result['rsi']}")
        print("📝 Analiz Notları:")
        for note in result['notes']:
            print(f"   • {note}")
        print("-" * 65)

def run_cli_backtest(symbol: str = 'BTC/USDT', timeframe: str = '4h', candles: int = 1000, tp: float = 6.0, sl: float = 3.5):
    symbol = ExchangeService.normalize_symbol(symbol)
    print("=" * 65)
    print(f"🧪 STRATEJİ BACKTEST SİMÜLATÖRÜ: {symbol} ({timeframe.upper()})")
    print("=" * 65)

    exchange = ExchangeService(exchange_id='binance')
    df = exchange.fetch_historical_ohlcv(symbol, timeframe=timeframe, total_candles=candles)

    if df.empty or len(df) < 50:
        print(f"❌ {symbol} için yeterli geçmiş veri temin edilemedi.")
        return

    cfg = BacktestConfig(
        initial_capital=1000.0,
        position_size_pct=100.0,
        commission_pct=0.1,
        entry_score_threshold=65,
        exit_score_threshold=40,
        take_profit_pct=tp,
        stop_loss_pct=sl
    )

    backtester = Backtester(config=cfg)
    res = backtester.run(df, symbol=symbol, timeframe=timeframe)

    print(f"💰 Başlangıç Sermayesi : {res.initial_capital:,.2f} $")
    print(f"💵 Son Bakiye          : {res.final_capital:,.2f} $")
    print(f"📈 Net Kâr / Zarar     : {res.net_profit:+.2f} $ (%{res.net_profit_pct:+.2f})")
    print(f"📊 Buy & Hold Getirisi : %{res.buy_and_hold_pct:+.2f}")
    print(f"🎯 Kazanma Oranı       : %{res.win_rate:.1f} ({res.winning_trades}/{res.total_trades} Kazanç)")
    print(f"⚖️ Profit Factor       : {res.profit_factor:.2f}")
    print(f"📉 Max Drawdown        : %{res.max_drawdown_pct:.2f} (-{res.max_drawdown_usd:.2f} $)")
    print(f"📐 Sharpe Oranı        : {res.sharpe_ratio:.2f}")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="Kripto Analiz ve Backtesting Aracı")
    parser.add_argument("--mode", choices=["scan", "backtest"], default="scan", help="Çalışma modu: scan (piyasa tarama) veya backtest")
    parser.add_argument("--symbol", default="BTC/USDT", help="Coin paritesi (Örn: PEPE, SUI, DOGE, BTC/USDT)")
    parser.add_argument("--timeframe", default="4h", help="Zaman dilimi (15m, 1h, 4h, 1d)")
    parser.add_argument("--candles", type=int, default=1000, help="Backtest mum sayısı")
    parser.add_argument("--tp", type=float, default=6.0, help="Kar al yuzdesi (oran: %%6.0)")
    parser.add_argument("--sl", type=float, default=3.5, help="Zarar kes yuzdesi (oran: %%3.5)")

    args = parser.parse_args()

    if args.mode == "backtest":
        run_cli_backtest(symbol=args.symbol, timeframe=args.timeframe, candles=args.candles, tp=args.tp, sl=args.sl)
    else:
        run_scanner(timeframe=args.timeframe)

if __name__ == "__main__":
    main()
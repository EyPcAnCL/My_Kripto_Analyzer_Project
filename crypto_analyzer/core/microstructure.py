"""
Piyasa Mikro Yapısı ve Emir Defteri (Market Microstructure & Order Book) Analiz Motoru
Hesaplanan Bileşenler:
  1. Order Book Imbalance (OBI): (BidVol - AskVol) / (BidVol + AskVol)
  2. Bid/Ask Spread (Mutlak, Yüzde, Bps)
  3. Likidite Derinliği (0.5%, 1.0%, 2.0% Depth Buffers)
  4. Trade Imbalance (Taker Alış vs. Taker Satış Hacmi)
  5. Cumulative Volume Delta (CVD)
  6. Slippage (Fiyat Kayması) & Market Impact Simülatörü ($1k, $5k, $10k, $25k, $50k, $100k)
  7. VWAP & TWAP Fiyat Seviyeleri
  8. Doğal Dil Piyasa Baskı Raporu (Microstructure Verdict)
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class DepthBuffer:
    depth_05_pct_bid: float = 0.0
    depth_05_pct_ask: float = 0.0
    depth_10_pct_bid: float = 0.0
    depth_10_pct_ask: float = 0.0
    depth_20_pct_bid: float = 0.0
    depth_20_pct_ask: float = 0.0
    ratio_05_pct: float = 1.0
    ratio_10_pct: float = 1.0

@dataclass
class SlippageQuote:
    order_size_usd: float
    side: str                   # 'BUY' veya 'SELL'
    avg_exec_price: float       # Ağırlıklı ortalama gerçekleşme fiyatı
    slippage_pct: float         # Mid price'a göre kayma yüzdesi (%)
    slippage_usd: float         # Fiyat farkı tutarı ($)
    effective_cost: float       # Toplam ödenen / alınan tutar ($)
    impact_level: str           # 'DÜŞÜK', 'ORTA', 'YÜKSEK', 'AŞIRI'

@dataclass
class MicrostructureResult:
    symbol: str
    timestamp: pd.Timestamp
    best_bid: float
    best_ask: float
    mid_price: float
    spread: float
    spread_pct: float
    spread_bps: float
    bid_vol_total: float
    ask_vol_total: float
    bid_usd_total: float
    ask_usd_total: float
    obi: float                  # -1.0 ile +1.0 arası
    obi_pct: float              # Yüzdesel OBI (%+35 vb.)
    trade_imbalance: float      # -1.0 ile +1.0 arası
    taker_buy_vol: float
    taker_sell_vol: float
    taker_buy_usd: float
    taker_sell_usd: float
    taker_buy_count: int
    taker_sell_count: int
    cvd_current: float
    vwap: float
    twap: float
    depth_buffers: DepthBuffer = field(default_factory=DepthBuffer)
    slippage_matrix: List[SlippageQuote] = field(default_factory=list)
    pressure_verdict: str = "NÖTR"
    pressure_badge: str = "⚪ DENGELİ PİYASA"
    statement: str = ""
    summary_notes: List[str] = field(default_factory=list)
    cvd_series: pd.DataFrame = field(default_factory=pd.DataFrame)
    bids_df: pd.DataFrame = field(default_factory=pd.DataFrame)
    asks_df: pd.DataFrame = field(default_factory=pd.DataFrame)

class MarketMicrostructureAnalyzer:
    """
    Emir defteri (Order Book) ve gerçekleşen işlem akışını (Trade Flow)
    analiz eden mikro yapı motoru.
    """

    @staticmethod
    def format_price(price: float) -> str:
        """Düşük fiyatlı coinler (PEPE, SHIB) ve yüksek fiyatlılar (BTC) için dinamik fiyat formatı."""
        if price is None or price == 0:
            return "0.00"
        if price < 0.0001:
            return f"{price:.8f}"
        elif price < 1.0:
            return f"{price:.6f}"
        elif price < 100.0:
            return f"{price:.4f}"
        else:
            return f"{price:,.2f}"

    @classmethod
    def analyze(
        cls,
        symbol: str,
        order_book: dict,
        trades: list,
        ticker_24h: Optional[dict] = None
    ) -> MicrostructureResult:
        """
        Emir defteri ve trade listesini işleyerek tüm mikro yapı metriklerini hesaplar.
        """
        now = pd.Timestamp.utcnow()

        bids = order_book.get('bids', [])
        asks = order_book.get('asks', [])

        if not bids or not asks:
            return MicrostructureResult(
                symbol=symbol,
                timestamp=now,
                best_bid=0.0, best_ask=0.0, mid_price=0.0,
                spread=0.0, spread_pct=0.0, spread_bps=0.0,
                bid_vol_total=0.0, ask_vol_total=0.0, bid_usd_total=0.0, ask_usd_total=0.0,
                obi=0.0, obi_pct=0.0, trade_imbalance=0.0,
                taker_buy_vol=0.0, taker_sell_vol=0.0, taker_buy_usd=0.0, taker_sell_usd=0.0,
                taker_buy_count=0, taker_sell_count=0, cvd_current=0.0, vwap=0.0, twap=0.0,
                statement=f"{symbol} için anlık emir defteri verisi alınamadı."
            )

        best_bid = float(bids[0][0])
        best_ask = float(asks[0][0])
        mid_price = (best_bid + best_ask) / 2.0

        # -------------------------------------------------------------
        # 1. SPREAD HESAPLAMALARI
        # -------------------------------------------------------------
        spread = best_ask - best_bid
        spread_pct = (spread / mid_price) * 100.0 if mid_price > 0 else 0.0
        spread_bps = spread_pct * 100.0

        # -------------------------------------------------------------
        # 2. EMİR DEFTERİ DERİNLİĞİ & OBI HESAPLAMASI
        # -------------------------------------------------------------
        bids_data = []
        cum_bid_usd = 0.0
        for p, a in bids:
            price = float(p)
            amount = float(a)
            usd_val = price * amount
            cum_bid_usd += usd_val
            bids_data.append({'price': price, 'amount': amount, 'value_usd': usd_val, 'cum_usd': cum_bid_usd})

        asks_data = []
        cum_ask_usd = 0.0
        for p, a in asks:
            price = float(p)
            amount = float(a)
            usd_val = price * amount
            cum_ask_usd += usd_val
            asks_data.append({'price': price, 'amount': amount, 'value_usd': usd_val, 'cum_usd': cum_ask_usd})

        bids_df = pd.DataFrame(bids_data)
        asks_df = pd.DataFrame(asks_data)

        total_bid_vol = bids_df['amount'].sum() if not bids_df.empty else 0.0
        total_ask_vol = asks_df['amount'].sum() if not asks_df.empty else 0.0
        total_bid_usd = bids_df['value_usd'].sum() if not bids_df.empty else 0.0
        total_ask_usd = asks_df['value_usd'].sum() if not asks_df.empty else 0.0

        vol_sum = total_bid_vol + total_ask_vol
        obi = (total_bid_vol - total_ask_vol) / vol_sum if vol_sum > 0 else 0.0
        obi_pct = round(obi * 100.0, 2)

        # -------------------------------------------------------------
        # 3. YÜZDESEL LİKİDİTE TAMPONLARI (DEPTH BUFFERS)
        # -------------------------------------------------------------
        depth = DepthBuffer()
        if mid_price > 0:
            # 0.5% Derinlik
            p_05_low = mid_price * 0.995
            p_05_high = mid_price * 1.005
            depth.depth_05_pct_bid = bids_df[bids_df['price'] >= p_05_low]['value_usd'].sum() if not bids_df.empty else 0.0
            depth.depth_05_pct_ask = asks_df[asks_df['price'] <= p_05_high]['value_usd'].sum() if not asks_df.empty else 0.0
            depth.ratio_05_pct = round(depth.depth_05_pct_bid / depth.depth_05_pct_ask, 2) if depth.depth_05_pct_ask > 0 else 1.0

            # 1.0% Derinlik
            p_10_low = mid_price * 0.990
            p_10_high = mid_price * 1.010
            depth.depth_10_pct_bid = bids_df[bids_df['price'] >= p_10_low]['value_usd'].sum() if not bids_df.empty else 0.0
            depth.depth_10_pct_ask = asks_df[asks_df['price'] <= p_10_high]['value_usd'].sum() if not asks_df.empty else 0.0
            depth.ratio_10_pct = round(depth.depth_10_pct_bid / depth.depth_10_pct_ask, 2) if depth.depth_10_pct_ask > 0 else 1.0

            # 2.0% Derinlik
            p_20_low = mid_price * 0.980
            p_20_high = mid_price * 1.020
            depth.depth_20_pct_bid = bids_df[bids_df['price'] >= p_20_low]['value_usd'].sum() if not bids_df.empty else 0.0
            depth.depth_20_pct_ask = asks_df[asks_df['price'] <= p_20_high]['value_usd'].sum() if not asks_df.empty else 0.0

        # -------------------------------------------------------------
        # 4. TRADE FLOW, TRADE IMBALANCE & CVD (CUMULATIVE VOLUME DELTA)
        # -------------------------------------------------------------
        taker_buy_vol = 0.0
        taker_sell_vol = 0.0
        taker_buy_usd = 0.0
        taker_sell_usd = 0.0
        taker_buy_count = 0
        taker_sell_count = 0

        cvd_rows = []
        running_cvd = 0.0

        if trades:
            sorted_trades = sorted(trades, key=lambda t: t.get('timestamp', 0))
            for t in sorted_trades:
                side = t.get('side', '').lower()
                amount = float(t.get('amount', 0))
                price = float(t.get('price', 0))
                cost = float(t.get('cost', price * amount))
                ts = pd.to_datetime(t.get('timestamp', 0), unit='ms') if t.get('timestamp') else now

                if side == 'buy':
                    taker_buy_vol += amount
                    taker_buy_usd += cost
                    taker_buy_count += 1
                    delta = amount
                else:
                    taker_sell_vol += amount
                    taker_sell_usd += cost
                    taker_sell_count += 1
                    delta = -amount

                running_cvd += delta
                cvd_rows.append({
                    'timestamp': ts,
                    'price': price,
                    'side': side,
                    'amount': amount,
                    'cost': cost,
                    'delta': delta,
                    'cvd': running_cvd
                })

        cvd_df = pd.DataFrame(cvd_rows)

        total_trade_vol = taker_buy_vol + taker_sell_vol
        trade_imbalance = (taker_buy_vol - taker_sell_vol) / total_trade_vol if total_trade_vol > 0 else 0.0

        # -------------------------------------------------------------
        # 5. VWAP & TWAP HESAPLAMASI
        # -------------------------------------------------------------
        if not cvd_df.empty and total_trade_vol > 0:
            vwap = (cvd_df['price'] * cvd_df['amount']).sum() / cvd_df['amount'].sum()
            twap = cvd_df['price'].mean()
        elif ticker_24h and ticker_24h.get('vwap'):
            vwap = float(ticker_24h['vwap'])
            twap = mid_price
        else:
            vwap = mid_price
            twap = mid_price

        # -------------------------------------------------------------
        # 6. SLIPPAGE & MARKET IMPACT SİMÜLASYONU
        # -------------------------------------------------------------
        slippage_matrix = []
        for size in [1000.0, 10000.0, 50000.0, 100000.0]:
            buy_quote = cls._simulate_order_execution(asks, size, is_buy=True, mid_price=mid_price)
            slippage_matrix.append(buy_quote)
            sell_quote = cls._simulate_order_execution(bids, size, is_buy=False, mid_price=mid_price)
            slippage_matrix.append(sell_quote)

        # -------------------------------------------------------------
        # 7. BİLEŞİK PİYASA BASKI RAPORU (PRESSURE VERDICT)
        # -------------------------------------------------------------
        pressure_score = (obi * 0.45) + (trade_imbalance * 0.40) + ((depth.ratio_05_pct - 1.0) * 0.15)

        if pressure_score >= 0.25:
            verdict = "GÜÇLÜ ALIŞ BASKISI"
            badge = "🟢 GÜÇLÜ ALIŞ BASKISI (Bid Wall / Alıcı Üstünlüğü)"
        elif pressure_score <= -0.25:
            verdict = "GÜÇLÜ SATIŞ BASKISI"
            badge = "🔴 GÜÇLÜ SATIŞ BASKISI (Ask Wall / Satıcı Üstünlüğü)"
        else:
            verdict = "DENGELİ / NÖTR"
            badge = "🟡 DENGELİ LİKİDİTE (Nötr Mikro Yapı)"

        mid_str = cls.format_price(mid_price)
        spread_str = cls.format_price(spread)

        statement = (
            f"**{symbol}** mikro yapısında **{verdict}** tespit edildi. "
            f"Order Book Imbalance (OBI): `%{obi_pct:+.2f}`, Trade Imbalance: `%{trade_imbalance * 100:+.2f}`. "
            f"En iyi Spread: `{spread_str} USDT` (%{spread_pct:.3f})."
        )

        notes = [
            f"**Emir Defteri Dengesizliği (OBI):** %{obi_pct:+.2f} ({'Alıcılar daha baskın' if obi > 0 else 'Satıcılar daha baskın'}).",
            f"**0.5% Likidite Oranı (Bid/Ask):** {depth.ratio_05_pct:.2f}x ({depth.depth_05_pct_bid:,.0f} $ Alış / {depth.depth_05_pct_ask:,.0f} $ Satış).",
            f"**Son Trade Akışı:** {taker_buy_count} Alış ({taker_buy_usd:,.0f} $) vs {taker_sell_count} Satış ({taker_sell_usd:,.0f} $).",
            f"**Cumulative Volume Delta (CVD):** {running_cvd:+.4f} birim ({'Kümülatif alım baskısı' if running_cvd > 0 else 'Kümülatif satış baskısı'}).",
            f"**Referans Fiyatlar:** VWAP: `{cls.format_price(vwap)} USDT` | TWAP: `{cls.format_price(twap)} USDT` | Mid: `{mid_str} USDT`."
        ]

        return MicrostructureResult(
            symbol=symbol,
            timestamp=now,
            best_bid=best_bid,
            best_ask=best_ask,
            mid_price=mid_price,
            spread=spread,
            spread_pct=round(spread_pct, 4),
            spread_bps=round(spread_bps, 2),
            bid_vol_total=round(total_bid_vol, 4),
            ask_vol_total=round(total_ask_vol, 4),
            bid_usd_total=round(total_bid_usd, 2),
            ask_usd_total=round(total_ask_usd, 2),
            obi=round(obi, 4),
            obi_pct=obi_pct,
            trade_imbalance=round(trade_imbalance, 4),
            taker_buy_vol=round(taker_buy_vol, 4),
            taker_sell_vol=round(taker_sell_vol, 4),
            taker_buy_usd=round(taker_buy_usd, 2),
            taker_sell_usd=round(taker_sell_usd, 2),
            taker_buy_count=taker_buy_count,
            taker_sell_count=taker_sell_count,
            cvd_current=round(running_cvd, 4),
            vwap=vwap,
            twap=twap,
            depth_buffers=depth,
            slippage_matrix=slippage_matrix,
            pressure_verdict=verdict,
            pressure_badge=badge,
            statement=statement,
            summary_notes=notes,
            cvd_series=cvd_df,
            bids_df=bids_df,
            asks_df=asks_df
        )

    @classmethod
    def _simulate_order_execution(cls, book_levels: list, order_size_usd: float, is_buy: bool, mid_price: float) -> SlippageQuote:
        """
        Emir defteri üzerinde belirli bir dolar büyüklüğündeki piyasa emrinin
        gerçekleşmesini simüle ederek ağırlıklı ortalama fiyatı ve slippage oranını hesaplar.
        """
        remaining_usd = order_size_usd
        total_coins = 0.0
        total_spent = 0.0

        for p, a in book_levels:
            price = float(p)
            amount = float(a)
            level_usd = price * amount

            if remaining_usd <= level_usd:
                fill_amount = remaining_usd / price
                total_coins += fill_amount
                total_spent += remaining_usd
                remaining_usd = 0.0
                break
            else:
                total_coins += amount
                total_spent += level_usd
                remaining_usd -= level_usd

        if remaining_usd > 0:
            avg_price = total_spent / total_coins if total_coins > 0 else mid_price
            slippage_pct = 9.99
            impact = "AŞIRI (Likidite Yetersiz)"
        else:
            avg_price = total_spent / total_coins if total_coins > 0 else mid_price
            slippage_pct = abs((avg_price - mid_price) / mid_price) * 100.0 if mid_price > 0 else 0.0
            if slippage_pct < 0.05:
                impact = "ÇOK DÜŞÜK"
            elif slippage_pct < 0.20:
                impact = "DÜŞÜK"
            elif slippage_pct < 0.80:
                impact = "ORTA"
            else:
                impact = "YÜKSEK"

        slippage_usd = abs(avg_price - mid_price)

        return SlippageQuote(
            order_size_usd=order_size_usd,
            side='BUY (Alış)' if is_buy else 'SELL (Satış)',
            avg_exec_price=avg_price,
            slippage_pct=round(slippage_pct, 4),
            slippage_usd=slippage_usd,
            effective_cost=round(total_spent, 2),
            impact_level=impact
        )

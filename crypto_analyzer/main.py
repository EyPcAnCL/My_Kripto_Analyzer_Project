import sys
import argparse
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from config.settings import SUPPORTED_TIMEFRAMES, DEFAULT_TIMEFRAME, DEFAULT_CANDLE_LIMIT
from services.market_data_service import MarketDataService
from services.indicator_service import IndicatorService
from core.structure import PriceStructureAnalyzer

def handle_collect(service: MarketDataService, symbol: str, timeframe: str, limit: int):
    print(f"📥 Veri Toplama Başlatılıyor: {symbol} [{timeframe}] (Limit: {limit})...")
    df = service.fetch_and_store(symbol=symbol, timeframe=timeframe, limit=limit)
    if not df.empty:
        print(f"✅ Başarılı! {len(df)} mum çekildi ve veritabanına kaydedildi.")
        print(f"   İlk Mum: {df.iloc[0]['timestamp']} | Son Mum: {df.iloc[-1]['timestamp']}")
        print(f"   Son Kapanış Fiyatı: {df.iloc[-1]['close']} USDT")
    else:
        print(f"❌ {symbol} için veri toplanamadı.")

def handle_collect_all(service: MarketDataService, symbol: str, candles: int):
    print("=" * 65)
    print(f"🚀 TÜM ZAMAN DİLİMLERİ İÇİN VERİ TOPLAMA: {symbol}")
    print(f"   Zaman Dilimleri: {', '.join(SUPPORTED_TIMEFRAMES)}")
    print(f"   Mum Adedi: {candles} / zaman dilimi")
    print("=" * 65)
    
    results = service.collect_all_timeframes(symbol=symbol, candles_per_tf=candles)
    print("\n📊 Toplama Sonuçları:")
    for tf, count in results.items():
        print(f"   • {tf.ljust(5)} : {count} mum başarıyla kaydedildi.")
    print("=" * 65)

def handle_backfill(service: MarketDataService, symbol: str, timeframe: str, candles: int):
    print(f"⏳ Geçmiş Veri Arşivleme (Backfill): {symbol} [{timeframe}] (Hedef: {candles} mum)...")
    count = service.backfill_history(symbol=symbol, timeframe=timeframe, total_candles=candles)
    print(f"💾 Arşivleme Tamamlandı! {count} yeni mum veritabanına eklendi.")

def handle_status(service: MarketDataService):
    print("=" * 65)
    print("💾 VERİTABANI SAKLAMA DURUMU (OHLCV ARŞİVİ)")
    print("=" * 65)
    df_summary = service.get_summary()
    if not df_summary.empty:
        print(df_summary.to_string(index=False))
    else:
        print("ℹ️ Veritabanında henüz kayıtlı mum verisi bulunmuyor.")
    print("=" * 65)

def handle_show(service: MarketDataService, symbol: str, timeframe: str, limit: int):
    print(f"🔍 {symbol} [{timeframe}] Veritabanındaki Son {limit} Mum:")
    df = service.get_candles(symbol=symbol, timeframe=timeframe, limit=limit, auto_fetch=False)
    if not df.empty:
        print(df.to_string(index=False))
    else:
        print(f"ℹ️ {symbol} [{timeframe}] için veritabanında kayıtlı veri bulunamadı.")

def handle_indicators(indicator_service: IndicatorService, symbol: str, timeframe: str, candles: int):
    print("=" * 65)
    print(f"📊 8 TEMEL TEKNİK GÖSTERGE SAYISAL RAPORU: {symbol} [{timeframe.upper()}]")
    print("   (Al/Sat sinyali üretilmeden saf matematiksel değerler raporlanır)")
    print("=" * 65)

    metrics = indicator_service.get_latest_numerical_metrics(symbol=symbol, timeframe=timeframe)
    if not metrics:
        print(f"❌ {symbol} [{timeframe}] için indikatörler hesaplanamadı.")
        return

    print(f"🪙 Sembol          : {symbol}")
    print(f"🕒 Son Mum Zamanı  : {metrics.get('timestamp')}")
    print(f"💰 Son Fiyat       : {metrics.get('close')} USDT")
    print("-" * 65)
    print("1. SMA (Basit Hareketli Ortalamalar):")
    print(f"   • sma_20        = {metrics.get('sma_20')}")
    print(f"   • sma_50        = {metrics.get('sma_50')}")
    print(f"   • sma_200       = {metrics.get('sma_200')}")
    print("-" * 65)
    print("2. EMA (Üstel Hareketli Ortalamalar):")
    print(f"   • ema_9         = {metrics.get('ema_9')}")
    print(f"   • ema_21        = {metrics.get('ema_21')}")
    print(f"   • ema_50        = {metrics.get('ema_50')}")
    print(f"   • ema_200       = {metrics.get('ema_200')}")
    print("-" * 65)
    print("3. RSI (Bağıl Güç Endeksi - 14):")
    print(f"   • rsi           = {metrics.get('rsi')}")
    print("-" * 65)
    print("4. MACD (12, 26, 9):")
    print(f"   • macd          = {metrics.get('macd')}")
    print(f"   • macd_signal   = {metrics.get('macd_signal')}")
    print(f"   • macd_hist     = {metrics.get('macd_hist')}")
    print("-" * 65)
    print("5. Bollinger Bands (20, 2):")
    print(f"   • bb_high       = {metrics.get('bb_high')}")
    print(f"   • bb_mid        = {metrics.get('bb_mid')}")
    print(f"   • bb_low        = {metrics.get('bb_low')}")
    print(f"   • bb_width (%%)  = %{metrics.get('bb_width')}")
    print(f"   • bb_pctb       = {metrics.get('bb_pctb')}")
    print("-" * 65)
    print("6. ATR (Average True Range - 14):")
    print(f"   • atr           = {metrics.get('atr')} USDT")
    print("-" * 65)
    print("7. Stochastic RSI (14, 3, 3):")
    print(f"   • stoch_k       = {metrics.get('stoch_k')}")
    print(f"   • stoch_d       = {metrics.get('stoch_d')}")
    print("-" * 65)
    print("8. ADX (Trend Gücü - 14):")
    print(f"   • adx           = {metrics.get('adx')}")
    print(f"   • adx_pos_di    = {metrics.get('adx_pos_di')}")
    print(f"   • adx_neg_di    = {metrics.get('adx_neg_di')}")
    print("=" * 65)
    print("💾 Tüm sayısal indikatör kayıtları SQLite veritabanına kaydedildi.")

def handle_structure(market_service: MarketDataService, symbol: str, timeframe: str, candles: int):
    print("=" * 65)
    print(f"🏛️ FİYAT YAPISI (MARKET STRUCTURE) RAPORU: {symbol} [{timeframe.upper()}]")
    print("=" * 65)

    df = market_service.get_candles(symbol=symbol, timeframe=timeframe, limit=candles, auto_fetch=True)
    if df.empty or len(df) < 20:
        print(f"❌ {symbol} [{timeframe}] için yeterli veri alınamadı.")
        return

    res = PriceStructureAnalyzer.analyze(df, symbol=symbol, timeframe=timeframe)

    print(f"📢 DURUM BİLDİRİMİ : {res.statement}")
    print(f"🧭 TREND DURUMU    : {res.trend_badge} ({res.trend_name_tr})")
    print(f"💰 ANLIK FİYAT     : {res.current_price:,.2f} USDT")
    print("-" * 65)
    print("🧱 DESTEK VE DİRENÇ SEVİYELERİ:")
    print(f"   • En Yakın Destek  : {res.nearest_support:,.2f} USDT (%{res.dist_to_support_pct} aşağıda)" if res.nearest_support else "   • En Yakın Destek  : -")
    print(f"   • En Yakın Direnç  : {res.nearest_resistance:,.2f} USDT (%{res.dist_to_resistance_pct} yukarıda)" if res.nearest_resistance else "   • En Yakın Direnç  : -")
    print("-" * 65)
    print("📍 SON FİYAT YAPISI NOKTALARI (Pivots):")
    for pt in res.points[-6:]:
        pt_badge = "🔴 Tepe" if pt.is_high else "🟢 Dip"
        print(f"   • {pt_badge} [{pt.point_type.ljust(4)}] : {pt.price:,.2f} USDT ({pt.candles_ago} mum önce)")
    print("-" * 65)
    if res.is_breakout:
        print(f"⚡ {res.breakout_details}")
    if res.is_breakdown:
        print(f"⚡ {res.breakout_details}")
    print("📝 ANALİZ NOTLARI:")
    for note in res.summary_notes:
        print(f"   • {note}")
    print("=" * 65)

def main():
    parser = argparse.ArgumentParser(description="Kripto Fiyat Verisi, İndikatör ve Fiyat Yapısı CLI")
    parser.add_argument("--action", choices=["collect", "collect-all", "backfill", "status", "show", "indicators", "structure"], default="structure",
                        help="İşlem türü: collect, collect-all, backfill, status, show, indicators, structure")
    parser.add_argument("--symbol", default="BTC/USDT", help="Coin sembolü (Örn: BTC, ETH, SOL, PEPE, AVAX)")
    parser.add_argument("--timeframe", default=DEFAULT_TIMEFRAME, choices=SUPPORTED_TIMEFRAMES, help="Zaman dilimi (1m, 5m, 15m, 1h, 4h, 1d)")
    parser.add_argument("--candles", type=int, default=DEFAULT_CANDLE_LIMIT, help="Mum sayısı")
    parser.add_argument("--limit", type=int, default=10, help="Görüntülenecek mum sayısı")
    parser.add_argument("--exchange", default="binance", help="Borsa adı (binance, kucoin, gate, bybit, okx)")

    args = parser.parse_args()
    market_service = MarketDataService(exchange_id=args.exchange)
    indicator_service = IndicatorService(exchange_id=args.exchange)

    if args.action == "collect":
        handle_collect(market_service, args.symbol, args.timeframe, args.candles)
    elif args.action == "collect-all":
        handle_collect_all(market_service, args.symbol, args.candles)
    elif args.action == "backfill":
        handle_backfill(market_service, args.symbol, args.timeframe, args.candles)
    elif args.action == "status":
        handle_status(market_service)
    elif args.action == "show":
        handle_show(market_service, args.symbol, args.timeframe, args.limit)
    elif args.action == "indicators":
        handle_indicators(indicator_service, args.symbol, args.timeframe, args.candles)
    elif args.action == "structure":
        handle_structure(market_service, args.symbol, args.timeframe, args.candles)

if __name__ == "__main__":
    main()
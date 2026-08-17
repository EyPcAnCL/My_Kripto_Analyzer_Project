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

def main():
    parser = argparse.ArgumentParser(description="Kripto Fiyat Verisi (OHLCV) Yönetim CLI")
    parser.add_argument("--action", choices=["collect", "collect-all", "backfill", "status", "show"], default="status",
                        help="İşlem türü: collect, collect-all, backfill, status, show")
    parser.add_argument("--symbol", default="BTC/USDT", help="Coin sembolü (Örn: BTC, ETH, SOL, PEPE, AVAX)")
    parser.add_argument("--timeframe", default=DEFAULT_TIMEFRAME, choices=SUPPORTED_TIMEFRAMES, help="Zaman dilimi (1m, 5m, 15m, 1h, 4h, 1d)")
    parser.add_argument("--candles", type=int, default=DEFAULT_CANDLE_LIMIT, help="Mum sayısı")
    parser.add_argument("--limit", type=int, default=10, help="Görüntülenecek mum sayısı")
    parser.add_argument("--exchange", default="binance", help="Borsa adı (binance, kucoin, gate, bybit, okx)")

    args = parser.parse_args()
    service = MarketDataService(exchange_id=args.exchange)

    if args.action == "collect":
        handle_collect(service, args.symbol, args.timeframe, args.candles)
    elif args.action == "collect-all":
        handle_collect_all(service, args.symbol, args.candles)
    elif args.action == "backfill":
        handle_backfill(service, args.symbol, args.timeframe, args.candles)
    elif args.action == "status":
        handle_status(service)
    elif args.action == "show":
        handle_show(service, args.symbol, args.timeframe, args.limit)

if __name__ == "__main__":
    main()
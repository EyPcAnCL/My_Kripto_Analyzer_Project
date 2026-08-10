from config.settings import DEFAULT_WATCHLIST, TIMEFRAME, CANDLE_LIMIT
from services.exchange_service import ExchangeService
from core.indicators import TechnicalIndicators
from core.scorer import AnalysisScorer

def main():
    print("🚀 Kripto Teknik Analizör Başlatılıyor...\n")
    
    # Servisleri başlat
    exchange = ExchangeService(exchange_id='binance')
    scorer = AnalysisScorer()

    print(f"Takip Listesindeki Coinler Taranıyor ({TIMEFRAME} Zaman Dilimi)...\n")
    print("-" * 60)

    for symbol in DEFAULT_WATCHLIST:
        # 1. Veriyi Çek
        df = exchange.fetch_ohlcv(symbol, timeframe=TIMEFRAME, limit=CANDLE_LIMIT)
        
        if df.empty:
            print(f"⚠️ {symbol} için veri alınamadı, atlanıyor.")
            continue

        # 2. İndikatörleri Hesapla
        df = TechnicalIndicators.add_all_indicators(df)
        
        # 3. Son mumu al ve puanla
        last_row = df.iloc[-1]
        current_price = last_row['close']
        
        result = scorer.evaluate(symbol, current_price, last_row)

        # 4. Raporu Konsola Yazdır
        print(f"🪙 Coin  : {result['symbol']}")
        print(f"💰 Fiyat : {result['price']} USDT")
        print(f"📊 Skor  : {result['score']}/100 --> Durum: {result['verdict']}")
        print(f"📈 RSI   : {result['rsi']}")
        print("📝 Analiz Notları:")
        for note in result['notes']:
            print(f"   • {note}")
        print("-" * 60)

if __name__ == "__main__":
    main()
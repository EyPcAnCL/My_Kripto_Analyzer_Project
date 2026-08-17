import pandas as pd
import logging
from typing import List, Optional
from datetime import datetime

from config.settings import SUPPORTED_TIMEFRAMES, DEFAULT_TIMEFRAME, DEFAULT_CANDLE_LIMIT
from services.exchange_service import ExchangeService
from database.connection import bulk_save_candles, query_candles, get_storage_summary, delete_candles

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Kripto Fiyat Verisi (OHLCV) Yönetim ve Saklama Servisi.
    Borsadan veri çekme, SQLite veritabanına kaydetme, mükerrer kontrolü ve hızlı sorgulamaları yönetir.
    """

    def __init__(self, exchange_id: str = 'binance'):
        self.exchange = ExchangeService(exchange_id=exchange_id)

    def fetch_and_store(self, symbol: str, timeframe: str = DEFAULT_TIMEFRAME, limit: int = DEFAULT_CANDLE_LIMIT) -> pd.DataFrame:
        """
        Borsadan belirtilen parite ve zaman dilimindeki güncel mumları çeker,
        veritabanına kaydeder ve Pandas DataFrame olarak döner.
        """
        symbol = self.exchange.normalize_symbol(symbol)
        timeframe = self.exchange.normalize_timeframe(timeframe)

        # 1. Borsadan canlı veriyi çek
        df = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
        
        if df.empty:
            logger.warning(f"Borsadan veri alınamadı: {symbol} ({timeframe})")
            return pd.DataFrame()

        # 2. Veritabanına kaydet (Mükerrerleri güvenle atlar)
        saved_count = bulk_save_candles(symbol=symbol, timeframe=timeframe, df=df)
        logger.info(f"✅ {symbol} ({timeframe}): {len(df)} mum çekildi, {saved_count} yeni mum veritabanına eklendi.")

        return df

    def backfill_history(self, symbol: str, timeframe: str = DEFAULT_TIMEFRAME, total_candles: int = 1000) -> int:
        """
        Geçmişe dönük büyük hacimli (örn: 1000-2000) mumu sayfalayarak indirir
        ve veritabanına depolar.
        """
        symbol = self.exchange.normalize_symbol(symbol)
        timeframe = self.exchange.normalize_timeframe(timeframe)

        logger.info(f"⏳ {symbol} ({timeframe}) için {total_candles} adet geçmiş mum indiriliyor...")
        df_hist = self.exchange.fetch_historical_ohlcv(symbol, timeframe=timeframe, total_candles=total_candles)

        if df_hist.empty:
            logger.warning(f"Geçmiş veri indirilemedi: {symbol} ({timeframe})")
            return 0

        saved_count = bulk_save_candles(symbol=symbol, timeframe=timeframe, df=df_hist)
        logger.info(f"💾 {symbol} ({timeframe}) Arşivlendi: Toplam {len(df_hist)} mumdan {saved_count} adedi veritabanına yazıldı.")
        return saved_count

    def collect_all_timeframes(self, symbol: str, timeframes: List[str] = None, candles_per_tf: int = 500) -> dict:
        """
        Belirtilen coin için tüm desteklenen zaman dilimlerini (1m, 5m, 15m, 1h, 4h, 1d)
        tek seferde indirip veritabanına kaydeder.
        """
        symbol = self.exchange.normalize_symbol(symbol)
        tfs = timeframes or SUPPORTED_TIMEFRAMES
        results = {}

        logger.info(f"🚀 {symbol} için tüm zaman dilimleri toplanıyor: {tfs}")

        for tf in tfs:
            try:
                df = self.fetch_and_store(symbol=symbol, timeframe=tf, limit=candles_per_tf)
                results[tf] = len(df)
            except Exception as e:
                logger.error(f"Hata oluştu ({symbol} {tf}): {e}")
                results[tf] = 0

        return results

    def get_candles(self, symbol: str, timeframe: str = DEFAULT_TIMEFRAME, limit: int = DEFAULT_CANDLE_LIMIT, auto_fetch: bool = True) -> pd.DataFrame:
        """
        Öncelikle yerel veritabanından mum verilerini sorgular.
        Eğer veritabanında veri yoksa veya yetersizse otomatik olarak borsadan çeker ve veritabanına kaydeder.
        """
        symbol = self.exchange.normalize_symbol(symbol)
        timeframe = self.exchange.normalize_timeframe(timeframe)

        # 1. Yerel veritabanından oku
        df = query_candles(symbol=symbol, timeframe=timeframe, limit=limit)

        # 2. Eğer yerelde veri yoksa veya eksikse ve auto_fetch aktifse borsadan çek
        if (df.empty or len(df) < limit) and auto_fetch:
            logger.info(f"Yerel veritabanında {symbol} ({timeframe}) yetersiz, borsadan tamamlanıyor...")
            df = self.fetch_and_store(symbol=symbol, timeframe=timeframe, limit=limit)

        return df

    def get_summary(self) -> pd.DataFrame:
        """Veritabanında kayıtlı tüm veri arşivinin özetini döner."""
        return get_storage_summary()

    def remove_coin_data(self, symbol: str, timeframe: str = None) -> int:
        """Belirtilen coinin veritabanındaki kayıtlarını siler."""
        symbol = self.exchange.normalize_symbol(symbol)
        return delete_candles(symbol=symbol, timeframe=timeframe)

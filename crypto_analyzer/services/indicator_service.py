import pandas as pd
import logging
from typing import Optional, Dict

from config.settings import DEFAULT_TIMEFRAME, DEFAULT_CANDLE_LIMIT
from core.indicators import TechnicalIndicators
from services.market_data_service import MarketDataService
from database.connection import bulk_save_indicators, query_indicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class IndicatorService:
    """
    8 Temel Teknik Göstergenin Sayısal Verilerini Hesaplayan ve
    Veritabanına Kaydeden Servis.
    """

    def __init__(self, exchange_id: str = 'binance'):
        self.market_service = MarketDataService(exchange_id=exchange_id)

    def compute_and_save(self, symbol: str, timeframe: str = DEFAULT_TIMEFRAME, limit: int = DEFAULT_CANDLE_LIMIT) -> pd.DataFrame:
        """
        1. OHLCV mum verilerini yerel DB veya borsadan temin eder.
        2. 8 temel indikatörün sayısal değerlerini hesaplar.
        3. Sonuçları SQLite veritabanına kaydeder.
        4. Tüm sayısal göstergeleri içeren DataFrame döndürür.
        """
        symbol = self.market_service.exchange.normalize_symbol(symbol)
        timeframe = self.market_service.exchange.normalize_timeframe(timeframe)

        # 1. OHLCV verisini al
        df_ohlcv = self.market_service.get_candles(symbol=symbol, timeframe=timeframe, limit=limit, auto_fetch=True)
        if df_ohlcv.empty or len(df_ohlcv) < 14:
            logger.warning(f"İndikatör hesabı için yetersiz veri: {symbol} ({timeframe})")
            return pd.DataFrame()

        # 2. İndikatörleri hesapla
        df_indicators = TechnicalIndicators.calculate_all(df_ohlcv)

        # 3. Veritabanına kaydet
        saved_count = bulk_save_indicators(symbol=symbol, timeframe=timeframe, df=df_indicators)
        logger.info(f"📊 {symbol} ({timeframe}): {len(df_indicators)} mumluk indikatör hesaplandı, {saved_count} yeni kayıt DB'ye eklendi.")

        return df_indicators

    def get_latest_numerical_metrics(self, symbol: str, timeframe: str = DEFAULT_TIMEFRAME) -> Dict:
        """
        En güncel mumun tüm 8 indikatör sayısal değerlerini sözlük (dict) olarak döner.
        """
        df = self.compute_and_save(symbol=symbol, timeframe=timeframe, limit=250)
        if df.empty:
            return {}
        return TechnicalIndicators.extract_latest_metrics(df)

    def get_history(self, symbol: str, timeframe: str = DEFAULT_TIMEFRAME, limit: int = 100) -> pd.DataFrame:
        """
        Veritabanından hesaplanmış indikatör geçmişini çeker.
        """
        symbol = self.market_service.exchange.normalize_symbol(symbol)
        timeframe = self.market_service.exchange.normalize_timeframe(timeframe)
        return query_indicators(symbol=symbol, timeframe=timeframe, limit=limit)

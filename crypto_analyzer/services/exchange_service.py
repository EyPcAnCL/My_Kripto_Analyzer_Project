import ccxt
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ExchangeService:
    def __init__(self, exchange_id='binance'):
        """Seçilen borsa API'sini başlatır."""
        try:
            exchange_class = getattr(ccxt, exchange_id)
            self.exchange = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'spot'}
            })
            logger.info(f"{exchange_id.capitalize()} borsası başarıyla başlatıldı.")
        except Exception as e:
            logger.error(f"Borsa başlatılamadı ({exchange_id}): {e}")
            raise e

    def fetch_ohlcv(self, symbol: str, timeframe: str = '4h', limit: int = 100) -> pd.DataFrame:
        """
        Belirtilen parite için OHLCV (Mum) verilerini çeker ve DataFrame döndürür.
        """
        try:
            logger.info(f"{symbol} için {timeframe} verileri çekiliyor...")
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            logger.error(f"Veri çekilirken hata oluştu ({symbol}): {e}")
            return pd.DataFrame()
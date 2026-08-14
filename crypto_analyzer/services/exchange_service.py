import ccxt
import pandas as pd
import logging
import time

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

    @staticmethod
    def normalize_symbol(symbol: str) -> str:
        """
        Kullanıcının girdiği coin sembolünü borsa standart formatına dönüştürür.
        Örnekler:
          'btc' -> 'BTC/USDT'
          'pepe' -> 'PEPE/USDT'
          'sol/usdt' -> 'SOL/USDT'
          'ethusdt' -> 'ETH/USDT'
          'doge-usdt' -> 'DOGE/USDT'
          'ada/btc' -> 'ADA/BTC'
        """
        if not symbol:
            return ""
        
        s = symbol.strip().upper().replace("-", "/")
        
        if "/" in s:
            return s
        
        if s.endswith("USDT") and len(s) > 4:
            return f"{s[:-4]}/USDT"
        elif s.endswith("USDC") and len(s) > 4:
            return f"{s[:-4]}/USDC"
        elif s.endswith("TRY") and len(s) > 3:
            return f"{s[:-3]}/TRY"
        elif s.endswith("BTC") and len(s) > 3 and s != "BTC":
            return f"{s[:-3]}/BTC"
        else:
            return f"{s}/USDT"

    def fetch_ohlcv(self, symbol: str, timeframe: str = '4h', limit: int = 100) -> pd.DataFrame:
        """
        Belirtilen parite için OHLCV (Mum) verilerini çeker ve DataFrame döndürür.
        """
        symbol = self.normalize_symbol(symbol)
        try:
            logger.info(f"{symbol} için {timeframe} verileri çekiliyor (Limit: {limit})...")
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
            
            if not ohlcv:
                logger.warning(f"{symbol} için boş veri döndü.")
                return pd.DataFrame()
            
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            
            return df
        except Exception as e:
            logger.error(f"Veri çekilirken hata oluştu ({symbol}): {e}")
            return pd.DataFrame()

    def fetch_historical_ohlcv(self, symbol: str, timeframe: str = '4h', total_candles: int = 500) -> pd.DataFrame:
        """
        Geriye dönük daha büyük hacimli (Backtest için 500-2000+) mum verisi çeker.
        Gerektiğinde sayfalama (pagination) yaparak verileri birleştirir.
        """
        symbol = self.normalize_symbol(symbol)
        try:
            if total_candles <= 500:
                return self.fetch_ohlcv(symbol, timeframe=timeframe, limit=total_candles)
            
            all_ohlcv = []
            candles_per_request = 500
            current_limit = min(candles_per_request, total_candles)
            
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=current_limit)
            if not ohlcv:
                return pd.DataFrame()
            
            all_ohlcv.extend(ohlcv)
            
            while len(all_ohlcv) < total_candles:
                oldest_timestamp = all_ohlcv[0][0]
                tf_ms = self.exchange.parse_timeframe(timeframe) * 1000
                since = oldest_timestamp - (candles_per_request * tf_ms)
                
                earlier_ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=since, limit=candles_per_request)
                if not earlier_ohlcv or earlier_ohlcv[0][0] >= oldest_timestamp:
                    break
                
                unique_earlier = [c for c in earlier_ohlcv if c[0] < oldest_timestamp]
                if not unique_earlier:
                    break
                
                all_ohlcv = unique_earlier + all_ohlcv
                time.sleep(self.exchange.rateLimit / 1000.0)
            
            df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df = df.drop_duplicates(subset=['timestamp']).sort_values('timestamp').reset_index(drop=True)
            
            if len(df) > total_candles:
                df = df.iloc[-total_candles:].reset_index(drop=True)
                
            return df
        except Exception as e:
            logger.error(f"Geçmiş veri çekilirken hata oluştu ({symbol}): {e}")
            return self.fetch_ohlcv(symbol, timeframe=timeframe, limit=min(total_candles, 500))
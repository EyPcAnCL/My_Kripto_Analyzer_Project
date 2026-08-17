import os
from pathlib import Path

# Projenin ana dizini
BASE_DIR = Path(__file__).resolve().parent.parent

# Veritabanı dosya yolu
DATABASE_DIR = os.path.join(BASE_DIR, "database")
DB_PATH = os.path.join(DATABASE_DIR, "crypto_data.db")

# Desteklenen Zaman Dilimleri (OHLCV)
SUPPORTED_TIMEFRAMES = [
    '1m',   # 1 Dakika
    '5m',   # 5 Dakika
    '15m',  # 15 Dakika
    '1h',   # 1 Saat
    '4h',   # 4 Saat
    '1d'    # 1 Gün
]

DEFAULT_TIMEFRAME = '4h'
DEFAULT_CANDLE_LIMIT = 500

# Varsayılan Borsa
DEFAULT_EXCHANGE = 'binance'
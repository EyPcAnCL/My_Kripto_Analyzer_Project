import os
from pathlib import Path

# Projenin ana dizini
BASE_DIR = Path(__file__).resolve().parent.parent

# Veritabanı dosya yolu
DB_PATH = os.path.join(BASE_DIR, "database", "crypto_data.db")

# Varsayılan Takip Listesi
DEFAULT_WATCHLIST = [
    'BTC/USDT', 
    'ETH/USDT', 
    'SOL/USDT', 
    'AVAX/USDT', 
    'BNB/USDT'
]

# Analiz Parametreleri
TIMEFRAME = '4h'
CANDLE_LIMIT = 100

# Skor Eşikleri
SCORE_STRONG_BUY = 75
SCORE_BUY = 60
SCORE_RISKY = 40
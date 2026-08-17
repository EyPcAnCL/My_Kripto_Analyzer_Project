import os
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import pandas as pd
from datetime import datetime

from config.settings import DB_PATH, DATABASE_DIR
from database.models import Base, Candle, TechnicalIndicatorData

# Veritabanı motoru ve bağlantısı
os.makedirs(DATABASE_DIR, exist_ok=True)
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False}
)
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    """Tüm veritabanı tablolarını oluşturur ve indeksleri hazırlar."""
    os.makedirs(DATABASE_DIR, exist_ok=True)
    Base.metadata.create_all(bind=engine)

# =========================================================================
# 1. OHLCV MUM VERİSİ İŞLEMLERİ
# =========================================================================

def bulk_save_candles(symbol: str, timeframe: str, df: pd.DataFrame) -> int:
    """
    Pandas DataFrame formatındaki OHLCV verilerini SQLite veritabanına
    mükerrer kayıtları güvenle atlayarak (INSERT OR IGNORE) yüksek hızda yazar.
    """
    if df is None or df.empty:
        return 0

    init_db()
    
    records = []
    for _, row in df.iterrows():
        ts = row['timestamp']
        if not isinstance(ts, datetime):
            ts = pd.to_datetime(ts).to_pydatetime()

        records.append({
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': ts,
            'open': float(row['open']),
            'high': float(row['high']),
            'low': float(row['low']),
            'close': float(row['close']),
            'volume': float(row['volume']),
            'created_at': datetime.utcnow()
        })

    if not records:
        return 0

    session = SessionLocal()
    try:
        stmt = sqlite_insert(Candle).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['symbol', 'timeframe', 'timestamp']
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def query_candles(symbol: str, timeframe: str, limit: int = 500, start_time: datetime = None, end_time: datetime = None) -> pd.DataFrame:
    """
    Veritabanından belirtilen parite ve zaman dilimine ait mum verilerini çeker.
    """
    init_db()
    session = SessionLocal()
    try:
        query = session.query(Candle).filter(
            Candle.symbol == symbol,
            Candle.timeframe == timeframe
        )

        if start_time:
            query = query.filter(Candle.timestamp >= start_time)
        if end_time:
            query = query.filter(Candle.timestamp <= end_time)

        candles = query.order_by(Candle.timestamp.desc()).limit(limit).all()
        candles.reverse()

        if not candles:
            return pd.DataFrame()

        data = [{
            'timestamp': c.timestamp,
            'open': c.open,
            'high': c.high,
            'low': c.low,
            'close': c.close,
            'volume': c.volume
        } for c in candles]

        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    finally:
        session.close()

def get_storage_summary() -> pd.DataFrame:
    """
    Veritabanında kayıtlı tüm paritelerin zaman dilimlerine göre özet istatistiklerini döner.
    """
    init_db()
    session = SessionLocal()
    try:
        results = session.query(
            Candle.symbol,
            Candle.timeframe,
            func.count(Candle.id).label('candle_count'),
            func.min(Candle.timestamp).label('first_candle'),
            func.max(Candle.timestamp).label('last_candle')
        ).group_by(Candle.symbol, Candle.timeframe).order_by(Candle.symbol, Candle.timeframe).all()

        if not results:
            return pd.DataFrame(columns=['Sembol', 'Zaman Dilimi', 'Mum Sayısı', 'İlk Tarih', 'Son Tarih'])

        data = [{
            'Sembol': r.symbol,
            'Zaman Dilimi': r.timeframe,
            'Mum Sayısı': r.candle_count,
            'İlk Tarih': r.first_candle.strftime('%Y-%m-%d %H:%M') if r.first_candle else '-',
            'Son Tarih': r.last_candle.strftime('%Y-%m-%d %H:%M') if r.last_candle else '-'
        } for r in results]

        return pd.DataFrame(data)
    finally:
        session.close()

def delete_candles(symbol: str, timeframe: str = None) -> int:
    """Veritabanından belirli bir coinin veya zaman diliminin mumlarını siler."""
    init_db()
    session = SessionLocal()
    try:
        query = session.query(Candle).filter(Candle.symbol == symbol)
        if timeframe:
            query = query.filter(Candle.timeframe == timeframe)
        count = query.delete()
        session.commit()
        return count
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

# =========================================================================
# 2. TEKNİK İNDİKATÖR SAYISAL VERİLERİ İŞLEMLERİ
# =========================================================================

def bulk_save_indicators(symbol: str, timeframe: str, df: pd.DataFrame) -> int:
    """
    Hesaplanan 8 temel teknik indikatörün sayısal verilerini
    TechnicalIndicatorData tablosuna toplu yazar (mükerrer kayıtlar atlanır).
    """
    if df is None or df.empty:
        return 0

    init_db()

    def get_num(row, col):
        val = row.get(col)
        if pd.isna(val) or val is None:
            return None
        return float(val)

    records = []
    for _, row in df.iterrows():
        ts = row['timestamp']
        if not isinstance(ts, datetime):
            ts = pd.to_datetime(ts).to_pydatetime()

        records.append({
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': ts,
            'close_price': float(row['close']),
            'sma_20': get_num(row, 'SMA_20'),
            'sma_50': get_num(row, 'SMA_50'),
            'sma_200': get_num(row, 'SMA_200'),
            'ema_9': get_num(row, 'EMA_9'),
            'ema_21': get_num(row, 'EMA_21'),
            'ema_50': get_num(row, 'EMA_50'),
            'ema_200': get_num(row, 'EMA_200'),
            'rsi': get_num(row, 'RSI'),
            'macd': get_num(row, 'MACD'),
            'macd_signal': get_num(row, 'MACD_Signal'),
            'macd_hist': get_num(row, 'MACD_Hist'),
            'bb_high': get_num(row, 'BB_High'),
            'bb_mid': get_num(row, 'BB_Mid'),
            'bb_low': get_num(row, 'BB_Low'),
            'bb_width': get_num(row, 'BB_Width'),
            'bb_pctb': get_num(row, 'BB_PctB'),
            'atr': get_num(row, 'ATR'),
            'stoch_k': get_num(row, 'Stoch_K'),
            'stoch_d': get_num(row, 'Stoch_D'),
            'adx': get_num(row, 'ADX'),
            'adx_pos_di': get_num(row, 'ADX_Pos_DI'),
            'adx_neg_di': get_num(row, 'ADX_Neg_DI'),
            'created_at': datetime.utcnow()
        })

    if not records:
        return 0

    session = SessionLocal()
    try:
        stmt = sqlite_insert(TechnicalIndicatorData).values(records)
        stmt = stmt.on_conflict_do_nothing(
            index_elements=['symbol', 'timeframe', 'timestamp']
        )
        result = session.execute(stmt)
        session.commit()
        return result.rowcount
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def query_indicators(symbol: str, timeframe: str, limit: int = 500) -> pd.DataFrame:
    """
    Veritabanından hesaplanmış teknik indikatör kayıtlarını çeker.
    """
    init_db()
    session = SessionLocal()
    try:
        records = session.query(TechnicalIndicatorData).filter(
            TechnicalIndicatorData.symbol == symbol,
            TechnicalIndicatorData.timeframe == timeframe
        ).order_by(TechnicalIndicatorData.timestamp.desc()).limit(limit).all()

        records.reverse()
        if not records:
            return pd.DataFrame()

        data = [r.to_dict() for r in records]
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        return df
    finally:
        session.close()

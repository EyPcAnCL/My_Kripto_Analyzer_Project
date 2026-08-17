import os
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import pandas as pd
from datetime import datetime

from config.settings import DB_PATH, DATABASE_DIR
from database.models import Base, Candle

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

def bulk_save_candles(symbol: str, timeframe: str, df: pd.DataFrame) -> int:
    """
    Pandas DataFrame formatındaki OHLCV verilerini SQLite veritabanına
    mükerrer kayıtları güvenle atlayarak (INSERT OR IGNORE) yüksek hızda yazar.
    Eklenen yeni mum sayısını döner.
    """
    if df is None or df.empty:
        return 0

    init_db()
    
    # Gerekli sütun kontrolü
    required_cols = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
    if not required_cols.issubset(df.columns):
        raise ValueError(f"DataFrame şu sütunları içermelidir: {required_cols}")

    records = []
    for _, row in df.iterrows():
        # Timestamp datetime formatında olmalı
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
        # SQLite için yüksek performanslı INSERT OR IGNORE
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
    Veritabanından belirtilen parite ve zaman dilimine ait mum verilerini çeker
    ve sıralı bir Pandas DataFrame olarak döndürür.
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

        # En son mumları almak için ters sıralayıp limitle, sonra kronolojik düzene çevir
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

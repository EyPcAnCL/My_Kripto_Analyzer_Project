from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, Index
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class Candle(Base):
    """
    OHLCV (Open, High, Low, Close, Volume) Mum Verisi Tablosu
    """
    __tablename__ = 'ohlcv_candles'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Bir sembol, zaman dilimi ve zaman damgası için yalnızca 1 kayıt bulunabilir (Mükerrerlik engeli)
    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uix_symbol_tf_time'),
        Index('idx_symbol_tf_time_desc', 'symbol', 'timeframe', timestamp.desc()),
    )

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'open': self.open,
            'high': self.high,
            'low': self.low,
            'close': self.close,
            'volume': self.volume
        }

    def __repr__(self):
        return f"<Candle {self.symbol} {self.timeframe} {self.timestamp} C:{self.close} V:{self.volume}>"

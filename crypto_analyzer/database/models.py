from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class WatchlistCoin(Base):
    __tablename__ = 'watchlist'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), unique=True, nullable=False)
    added_at = Column(DateTime, default=datetime.utcnow)
    notes = Column(String(255), default="")
    target_buy_price = Column(Float, nullable=True)
    target_sell_price = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "symbol": self.symbol,
            "added_at": self.added_at.strftime('%Y-%m-%d %H:%M') if self.added_at else "-",
            "notes": self.notes,
            "target_buy_price": self.target_buy_price,
            "target_sell_price": self.target_sell_price,
            "is_active": self.is_active
        }

class AnalysisLog(Base):
    __tablename__ = 'analysis_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False)
    timeframe = Column(String(10), default='4h')
    price = Column(Float, nullable=False)
    score = Column(Integer, nullable=False)
    verdict = Column(String(50), nullable=False)
    rsi = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

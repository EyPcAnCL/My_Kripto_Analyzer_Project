import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from config.settings import DB_PATH
from database.models import Base, WatchlistCoin, AnalysisLog

# Veritabanı motoru
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False})
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))

def init_db():
    """Tabloları oluşturur."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    Base.metadata.create_all(bind=engine)

def get_watchlist():
    """Aktif takip listesindeki coinleri döner."""
    session = SessionLocal()
    try:
        coins = session.query(WatchlistCoin).filter(WatchlistCoin.is_active == True).order_by(WatchlistCoin.added_at.desc()).all()
        return [c.symbol for c in coins]
    finally:
        session.close()

def get_watchlist_details():
    """Takip listesindeki tüm detaylı modelleri döner."""
    session = SessionLocal()
    try:
        coins = session.query(WatchlistCoin).filter(WatchlistCoin.is_active == True).order_by(WatchlistCoin.added_at.desc()).all()
        return [c.to_dict() for c in coins]
    finally:
        session.close()

def is_in_watchlist(symbol: str) -> bool:
    """Belirtilen coin takip listesinde var mı kontrol eder."""
    session = SessionLocal()
    try:
        symbol = symbol.strip().upper()
        coin = session.query(WatchlistCoin).filter(WatchlistCoin.symbol == symbol, WatchlistCoin.is_active == True).first()
        return coin is not None
    finally:
        session.close()

def add_to_watchlist(symbol: str, notes: str = "", target_buy: float = None, target_sell: float = None) -> bool:
    """Takip listesine yeni coin ekler veya günceller."""
    session = SessionLocal()
    try:
        symbol = symbol.strip().upper()
        if not symbol:
            return False
        
        existing = session.query(WatchlistCoin).filter(WatchlistCoin.symbol == symbol).first()
        if existing:
            existing.is_active = True
            if notes:
                existing.notes = notes
            if target_buy is not None and target_buy > 0:
                existing.target_buy_price = target_buy
            if target_sell is not None and target_sell > 0:
                existing.target_sell_price = target_sell
        else:
            new_coin = WatchlistCoin(
                symbol=symbol,
                notes=notes,
                target_buy_price=target_buy if target_buy and target_buy > 0 else None,
                target_sell_price=target_sell if target_sell and target_sell > 0 else None,
                is_active=True
            )
            session.add(new_coin)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        return False
    finally:
        session.close()

def remove_from_watchlist(symbol: str) -> bool:
    """Takip listesinden coini tamamen siler."""
    session = SessionLocal()
    try:
        symbol = symbol.strip().upper()
        coin = session.query(WatchlistCoin).filter(WatchlistCoin.symbol == symbol).first()
        if coin:
            session.delete(coin)
            session.commit()
            return True
        return False
    except Exception as e:
        session.rollback()
        return False
    finally:
        session.close()

def clear_watchlist() -> bool:
    """Takip listesindeki tüm coinleri temizler."""
    session = SessionLocal()
    try:
        session.query(WatchlistCoin).delete()
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()

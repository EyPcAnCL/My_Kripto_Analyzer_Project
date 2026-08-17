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


class TechnicalIndicatorData(Base):
    """
    8 Temel Teknik Göstergenin Sayısal Verileri Tablosu:
    SMA (20, 50, 200), EMA (9, 21, 50, 200), RSI, MACD, Bollinger Bands, ATR, StochRSI, ADX
    """
    __tablename__ = 'technical_indicators'

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    close_price = Column(Float, nullable=False)

    # 1. SMA Değerleri
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    sma_200 = Column(Float, nullable=True)

    # 2. EMA Değerleri
    ema_9 = Column(Float, nullable=True)
    ema_21 = Column(Float, nullable=True)
    ema_50 = Column(Float, nullable=True)
    ema_200 = Column(Float, nullable=True)

    # 3. RSI Değeri
    rsi = Column(Float, nullable=True)

    # 4. MACD Değerleri
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)

    # 5. Bollinger Bands Değerleri
    bb_high = Column(Float, nullable=True)
    bb_mid = Column(Float, nullable=True)
    bb_low = Column(Float, nullable=True)
    bb_width = Column(Float, nullable=True)
    bb_pctb = Column(Float, nullable=True)

    # 6. ATR Değeri
    atr = Column(Float, nullable=True)

    # 7. Stochastic RSI Değerleri
    stoch_k = Column(Float, nullable=True)
    stoch_d = Column(Float, nullable=True)

    # 8. ADX Değerleri
    adx = Column(Float, nullable=True)
    adx_pos_di = Column(Float, nullable=True)
    adx_neg_di = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('symbol', 'timeframe', 'timestamp', name='uix_indicator_sym_tf_time'),
        Index('idx_indicator_sym_tf_time_desc', 'symbol', 'timeframe', timestamp.desc()),
    )

    def to_dict(self):
        return {
            'timestamp': self.timestamp,
            'close_price': self.close_price,
            'sma_20': self.sma_20,
            'sma_50': self.sma_50,
            'sma_200': self.sma_200,
            'ema_9': self.ema_9,
            'ema_21': self.ema_21,
            'ema_50': self.ema_50,
            'ema_200': self.ema_200,
            'rsi': self.rsi,
            'macd': self.macd,
            'macd_signal': self.macd_signal,
            'macd_hist': self.macd_hist,
            'bb_high': self.bb_high,
            'bb_mid': self.bb_mid,
            'bb_low': self.bb_low,
            'bb_width': self.bb_width,
            'bb_pctb': self.bb_pctb,
            'atr': self.atr,
            'stoch_k': self.stoch_k,
            'stoch_d': self.stoch_d,
            'adx': self.adx,
            'adx_pos_di': self.adx_pos_di,
            'adx_neg_di': self.adx_neg_di
        }

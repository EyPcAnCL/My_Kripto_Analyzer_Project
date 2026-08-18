import logging
import pandas as pd
from typing import Optional, Dict

from services.exchange_service import ExchangeService
from core.microstructure import MarketMicrostructureAnalyzer, MicrostructureResult

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MicrostructureService:
    """
    Piyasa Mikro Yapısı ve Emir Defteri Veri & Analiz Servisi.
    """

    def __init__(self, exchange_id: str = 'binance'):
        self.exchange = ExchangeService(exchange_id=exchange_id)

    def analyze_microstructure(
        self,
        symbol: str,
        depth_limit: int = 100,
        trades_limit: int = 100
    ) -> MicrostructureResult:
        """
        1. Anlık Order Book (Bids & Asks) verilerini çeker.
        2. Son gerçekleşen piyasa işlemlerini (Trade Flow) çeker.
        3. 24 saatlik Ticker (VWAP vb.) verisini çeker.
        4. Tüm mikro yapı göstergelerini (OBI, Spread, Likidite, CVD, Slippage) hesaplar.
        """
        symbol = self.exchange.normalize_symbol(symbol)

        logger.info(f"🌊 {symbol} için emir defteri ve mikro yapı verileri çekiliyor...")
        
        # 1. Order Book
        order_book = self.exchange.fetch_order_book(symbol=symbol, limit=depth_limit)
        
        # 2. Trades
        trades = self.exchange.fetch_trades(symbol=symbol, limit=trades_limit)
        
        # 3. Ticker
        ticker = self.exchange.fetch_ticker(symbol=symbol)

        # 4. Mikro Yapı Analizi
        result = MarketMicrostructureAnalyzer.analyze(
            symbol=symbol,
            order_book=order_book,
            trades=trades,
            ticker_24h=ticker
        )

        logger.info(f"✅ {symbol} Mikro Yapı Analizi Tamamlandı: {result.pressure_verdict} (OBI: {result.obi_pct:+.2f}%)")
        return result

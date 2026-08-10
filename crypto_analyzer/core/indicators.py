import pandas as pd
import ta

class TechnicalIndicators:
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        """
        DataFrame üzerine teknik analiz indikatörlerini ekler.
        """
        if df is None or df.empty or len(df) < 50:
            return df

        # RSI (14)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)

        # Üstel Hareketli Ortalamalar (EMA)
        df['EMA_50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['EMA_200'] = ta.trend.ema_indicator(df['close'], window=200)

        # MACD
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()

        # Bollinger Bantları
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['BB_High'] = bollinger.bollinger_hband()
        df['BB_Low'] = bollinger.bollinger_lband()
        df['BB_Mid'] = bollinger.bollinger_mavg()

        return df
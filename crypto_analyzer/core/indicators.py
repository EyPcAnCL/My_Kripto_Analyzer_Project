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

        df = df.copy()

        # 1. RSI (14)
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)

        # 2. Üstel Hareketli Ortalamalar (EMA)
        df['EMA_50'] = ta.trend.ema_indicator(df['close'], window=50)
        df['EMA_200'] = ta.trend.ema_indicator(df['close'], window=200)

        # 3. Basit Hareketli Ortalamalar (SMA 20)
        df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)

        # 4. MACD
        macd = ta.trend.MACD(df['close'])
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Diff'] = macd.macd_diff()

        # 5. Bollinger Bantları
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['BB_High'] = bollinger.bollinger_hband()
        df['BB_Low'] = bollinger.bollinger_lband()
        df['BB_Mid'] = bollinger.bollinger_mavg()

        # 6. Stochastic RSI
        try:
            stoch = ta.momentum.StochRSIIndicator(df['close'], window=14, smooth1=3, smooth2=3)
            df['Stoch_K'] = stoch.stochrsi_k() * 100
            df['Stoch_D'] = stoch.stochrsi_d() * 100
        except Exception:
            df['Stoch_K'] = 50.0
            df['Stoch_D'] = 50.0

        # 7. ATR (Volatilite)
        try:
            df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)
        except Exception:
            df['ATR'] = 0.0

        # 8. Hacim Ortalaması
        if 'volume' in df.columns:
            df['Vol_SMA_20'] = df['volume'].rolling(window=20).mean()

        return df

    @staticmethod
    def calculate_support_resistance(df: pd.DataFrame, window: int = 30) -> dict:
        """
        Son belirli mumdaki en yüksek ve en düşük seviyelere göre dinamik destek,
        direnç ve Fibonacci düzeltme seviyelerini hesaplar.
        """
        if df is None or df.empty or len(df) < window:
            return {}

        recent = df.iloc[-window:]
        recent_high = recent['high'].max()
        recent_low = recent['low'].min()
        current_close = df.iloc[-1]['close']
        diff = recent_high - recent_low

        fib_236 = recent_high - (diff * 0.236)
        fib_382 = recent_high - (diff * 0.382)
        fib_500 = recent_high - (diff * 0.500)
        fib_618 = recent_high - (diff * 0.618)
        fib_786 = recent_high - (diff * 0.786)

        return {
            "current_price": round(current_close, 4),
            "resistance_major": round(recent_high, 4),
            "support_major": round(recent_low, 4),
            "fib_236": round(fib_236, 4),
            "fib_382": round(fib_382, 4),
            "fib_500": round(fib_500, 4),
            "fib_618": round(fib_618, 4),
            "fib_786": round(fib_786, 4),
        }
"""
Temel Teknik Göstergeler (Sayısal Veri Hesaplama Motoru)
Hesaplanan Göstergeler:
  1. SMA (20, 50, 200)
  2. EMA (9, 21, 50, 200)
  3. RSI (14)
  4. MACD (12, 26, 9)
  5. Bollinger Bands (20, 2)
  6. ATR (14)
  7. Stochastic RSI (14, 3, 3)
  8. ADX (14)
"""
import pandas as pd
import numpy as np
import ta

class TechnicalIndicators:
    """
    Kripto OHLCV verileri üzerinde 8 temel teknik indikatörün
    sayısal değerlerini hesaplayan çekirdek sınıf.
    """

    @staticmethod
    def calculate_all(df: pd.DataFrame) -> pd.DataFrame:
        """
        OHLCV DataFrame üzerine 8 temel göstergenin tüm sayısal sütunlarını ekler.
        """
        if df is None or df.empty or len(df) < 14:
            return df

        df = df.copy()

        # -------------------------------------------------------------
        # 1. SMA (Basit Hareketli Ortalamalar)
        # -------------------------------------------------------------
        df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)
        df['SMA_50'] = ta.trend.sma_indicator(df['close'], window=50) if len(df) >= 50 else np.nan
        df['SMA_200'] = ta.trend.sma_indicator(df['close'], window=200) if len(df) >= 200 else np.nan

        # -------------------------------------------------------------
        # 2. EMA (Üstel Hareketli Ortalamalar)
        # -------------------------------------------------------------
        df['EMA_9'] = ta.trend.ema_indicator(df['close'], window=9)
        df['EMA_21'] = ta.trend.ema_indicator(df['close'], window=21)
        df['EMA_50'] = ta.trend.ema_indicator(df['close'], window=50) if len(df) >= 50 else np.nan
        df['EMA_200'] = ta.trend.ema_indicator(df['close'], window=200) if len(df) >= 200 else np.nan

        # -------------------------------------------------------------
        # 3. RSI (Bağıl Güç Endeksi - 14)
        # -------------------------------------------------------------
        df['RSI'] = ta.momentum.rsi(df['close'], window=14)

        # -------------------------------------------------------------
        # 4. MACD (Moving Average Convergence Divergence - 12, 26, 9)
        # -------------------------------------------------------------
        macd = ta.trend.MACD(df['close'], window_fast=12, window_slow=26, window_sign=9)
        df['MACD'] = macd.macd()
        df['MACD_Signal'] = macd.macd_signal()
        df['MACD_Hist'] = macd.macd_diff()

        # -------------------------------------------------------------
        # 5. Bollinger Bands (Volatilite Bantları - 20, 2)
        # -------------------------------------------------------------
        bollinger = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
        df['BB_High'] = bollinger.bollinger_hband()
        df['BB_Mid'] = bollinger.bollinger_mavg()
        df['BB_Low'] = bollinger.bollinger_lband()
        df['BB_Width'] = bollinger.bollinger_wband()   # Genişlik Yüzdesi
        df['BB_PctB'] = bollinger.bollinger_pband()    # %B (Fiyatın bant içindeki bağıl konumu)

        # -------------------------------------------------------------
        # 6. ATR (Average True Range - Volatilite - 14)
        # -------------------------------------------------------------
        df['ATR'] = ta.volatility.average_true_range(df['high'], df['low'], df['close'], window=14)

        # -------------------------------------------------------------
        # 7. Stochastic RSI (Stokastik RSI - 14, 3, 3)
        # -------------------------------------------------------------
        try:
            stoch = ta.momentum.StochRSIIndicator(df['close'], window=14, smooth1=3, smooth2=3)
            df['Stoch_K'] = stoch.stochrsi_k() * 100
            df['Stoch_D'] = stoch.stochrsi_d() * 100
        except Exception:
            df['Stoch_K'] = np.nan
            df['Stoch_D'] = np.nan

        # -------------------------------------------------------------
        # 8. ADX (Average Directional Index - Trend Gücü - 14)
        # -------------------------------------------------------------
        try:
            adx = ta.trend.ADXIndicator(df['high'], df['low'], df['close'], window=14)
            df['ADX'] = adx.adx()
            df['ADX_Pos_DI'] = adx.adx_pos()
            df['ADX_Neg_DI'] = adx.adx_neg()
        except Exception:
            df['ADX'] = np.nan
            df['ADX_Pos_DI'] = np.nan
            df['ADX_Neg_DI'] = np.nan

        return df

    @staticmethod
    def extract_latest_metrics(df: pd.DataFrame) -> dict:
        """
        En son mumun hesaplanmış sayısal değerlerini temiz bir sözlük olarak döndürür.
        """
        if df is None or df.empty:
            return {}

        last = df.iloc[-1]

        def safe_val(val, decimals=4):
            if pd.isna(val) or val is None:
                return None
            return round(float(val), decimals)

        return {
            'timestamp': last.get('timestamp'),
            'close': safe_val(last.get('close')),
            
            # SMA
            'sma_20': safe_val(last.get('SMA_20')),
            'sma_50': safe_val(last.get('SMA_50')),
            'sma_200': safe_val(last.get('SMA_200')),

            # EMA
            'ema_9': safe_val(last.get('EMA_9')),
            'ema_21': safe_val(last.get('EMA_21')),
            'ema_50': safe_val(last.get('EMA_50')),
            'ema_200': safe_val(last.get('EMA_200')),

            # RSI
            'rsi': safe_val(last.get('RSI'), 2),

            # MACD
            'macd': safe_val(last.get('MACD')),
            'macd_signal': safe_val(last.get('MACD_Signal')),
            'macd_hist': safe_val(last.get('MACD_Hist')),

            # Bollinger
            'bb_high': safe_val(last.get('BB_High')),
            'bb_mid': safe_val(last.get('BB_Mid')),
            'bb_low': safe_val(last.get('BB_Low')),
            'bb_width': safe_val(last.get('BB_Width'), 2),
            'bb_pctb': safe_val(last.get('BB_PctB'), 4),

            # ATR
            'atr': safe_val(last.get('ATR')),

            # Stoch RSI
            'stoch_k': safe_val(last.get('Stoch_K'), 2),
            'stoch_d': safe_val(last.get('Stoch_D'), 2),

            # ADX
            'adx': safe_val(last.get('ADX'), 2),
            'adx_pos_di': safe_val(last.get('ADX_Pos_DI'), 2),
            'adx_neg_di': safe_val(last.get('ADX_Neg_DI'), 2),
        }
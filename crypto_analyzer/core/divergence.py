import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class DivergenceSignal:
    type: str              # 'REGULAR_BULLISH', 'REGULAR_BEARISH', 'HIDDEN_BULLISH', 'HIDDEN_BEARISH'
    indicator: str         # 'RSI', 'MACD'
    name_tr: str           # Türkçe açıklayıcı başlık
    description: str       # Detaylı açıklama
    p1_time: pd.Timestamp  # İlk dip/tepe zamanı
    p1_price: float        # İlk dip/tepe fiyatı
    p1_val: float          # İlk indikatör değeri
    p2_time: pd.Timestamp  # İkinci dip/tepe zamanı
    p2_price: float        # İkinci dip/tepe fiyatı
    p2_val: float          # İkinci indikatör değeri
    candles_ago: int       # Kaç mum önce tamamlandı
    score_impact: int      # Skora etkisi (+30, -30 vb.)
    is_bullish: bool       # Alım lehine mi?

@dataclass
class DivergenceResult:
    signals: List[DivergenceSignal] = field(default_factory=list)
    has_bullish: bool = False
    has_bearish: bool = False
    total_score_impact: int = 0
    summary_notes: List[str] = field(default_factory=list)

class DivergenceDetector:
    """
    Fiyat ile RSI / MACD arasındaki klasik ve gizli tepe-dip uyumsuzluklarını
    otomatik tespit eden gelişmiş algoritmik analiz sınıfı.
    """

    @staticmethod
    def _find_pivots(series: pd.Series, window: int = 3) -> tuple:
        """
        Yerel tepe (Swing High) ve dip (Swing Low) noktalarını tespit eder.
        """
        n = len(series)
        pivot_highs = []
        pivot_lows = []

        for i in range(window, n - window):
            val = series.iloc[i]
            # Tepe kontrolü
            if all(val >= series.iloc[i - k] for k in range(1, window + 1)) and \
               all(val >= series.iloc[i + k] for k in range(1, window + 1)):
                pivot_highs.append(i)
            # Dip kontrolü
            if all(val <= series.iloc[i - k] for k in range(1, window + 1)) and \
               all(val <= series.iloc[i + k] for k in range(1, window + 1)):
                pivot_lows.append(i)

        return pivot_lows, pivot_highs

    @classmethod
    def detect_all(cls, df: pd.DataFrame, lookback: int = 50, window: int = 3) -> DivergenceResult:
        """
        Verilen veri çerçevesi üzerinde tüm RSI ve MACD uyumsuzluklarını tarar.
        """
        result = DivergenceResult()
        if df is None or df.empty or len(df) < 30:
            return result

        df_slice = df.iloc[-lookback:].copy().reset_index(drop=True)
        n = len(df_slice)

        # 1. RSI Uyumsuzluklarını Tara
        if 'RSI' in df_slice.columns:
            cls._detect_indicator_divergences(
                df_slice=df_slice,
                indicator_col='RSI',
                indicator_name='RSI',
                window=window,
                result=result
            )

        # 2. MACD Histogram Uyumsuzluklarını Tara
        if 'MACD' in df_slice.columns and 'MACD_Signal' in df_slice.columns:
            cls._detect_indicator_divergences(
                df_slice=df_slice,
                indicator_col='MACD',
                indicator_name='MACD',
                window=window,
                result=result
            )

        # Özet değerleri güncelle
        result.has_bullish = any(s.is_bullish for s in result.signals)
        result.has_bearish = any(not s.is_bullish for s in result.signals)
        
        # En güçlü etkiyi al
        bullish_impact = max([s.score_impact for s in result.signals if s.is_bullish], default=0)
        bearish_impact = min([s.score_impact for s in result.signals if not s.is_bullish], default=0)
        result.total_score_impact = bullish_impact + bearish_impact

        for s in result.signals:
            result.summary_notes.append(s.description)

        return result

    @classmethod
    def _detect_indicator_divergences(cls, df_slice: pd.DataFrame, indicator_col: str, indicator_name: str, window: int, result: DivergenceResult):
        n = len(df_slice)
        price_lows, price_highs = cls._find_pivots(df_slice['low'], window=window)
        ind_lows, ind_highs = cls._find_pivots(df_slice[indicator_col], window=window)

        # --- A) DIP UYUMSUZLUKLARI (BULLISH DIVERGENCES) ---
        # Fiyatın son 2-3 dip noktasını karşılaştır
        if len(price_lows) >= 2:
            for i in range(len(price_lows) - 1, max(-1, len(price_lows) - 4), -1):
                p2_idx = price_lows[i]
                for j in range(i - 1, max(-1, i - 4), -1):
                    p1_idx = price_lows[j]
                    dist = p2_idx - p1_idx
                    if dist < 4 or dist > 35:
                        continue

                    # Sadece son 15 mum içinde tamamlanmış olanları önceliklendir
                    if (n - 1 - p2_idx) > 12:
                        continue

                    p1_price = df_slice['low'].iloc[p1_idx]
                    p2_price = df_slice['low'].iloc[p2_idx]
                    p1_ind = df_slice[indicator_col].iloc[p1_idx]
                    p2_ind = df_slice[indicator_col].iloc[p2_idx]

                    if pd.isna(p1_ind) or pd.isna(p2_ind):
                        continue

                    # 1. Klasik Pozitif Uyumsuzluk: Fiyat Daha Düşük Dip, İndikatör Daha Yüksek Dip
                    if p2_price < p1_price and p2_ind > p1_ind:
                        sig = DivergenceSignal(
                            type='REGULAR_BULLISH',
                            indicator=indicator_name,
                            name_tr=f"🟢 {indicator_name} Klasik Pozitif Uyumsuzluk (Boğa)",
                            description=f"🔥 **{indicator_name} Pozitif Uyumsuzluk (Dip Dönüşü):** Fiyat daha düşük dip ({p1_price:.2f} ➔ {p2_price:.2f}) yaparken {indicator_name} yükselen dip ({p1_ind:.1f} ➔ {p2_ind:.1f}) yaptı. Güçlü alış ve toparlanma sinyali.",
                            p1_time=df_slice['timestamp'].iloc[p1_idx],
                            p1_price=p1_price,
                            p1_val=p1_ind,
                            p2_time=df_slice['timestamp'].iloc[p2_idx],
                            p2_price=p2_price,
                            p2_val=p2_ind,
                            candles_ago=n - 1 - p2_idx,
                            score_impact=30,
                            is_bullish=True
                        )
                        # Çift eklemeyi önle
                        if not any(s.type == sig.type and s.indicator == sig.indicator for s in result.signals):
                            result.signals.append(sig)
                            break

                    # 2. Gizli Pozitif Uyumsuzluk: Fiyat Daha Yüksek Dip, İndikatör Daha Düşük Dip
                    elif p2_price > p1_price and p2_ind < p1_ind and p1_ind < 40:
                        sig = DivergenceSignal(
                            type='HIDDEN_BULLISH',
                            indicator=indicator_name,
                            name_tr=f"⚡ {indicator_name} Gizli Pozitif Uyumsuzluk (Trend Devamı)",
                            description=f"⚡ **{indicator_name} Gizli Pozitif Uyumsuzluk:** Fiyat yükselen dip korurken {indicator_name} aşırı soğudu ({p1_ind:.1f} ➔ {p2_ind:.1f}). Yükseliş trendinin devamını teyit eder.",
                            p1_time=df_slice['timestamp'].iloc[p1_idx],
                            p1_price=p1_price,
                            p1_val=p1_ind,
                            p2_time=df_slice['timestamp'].iloc[p2_idx],
                            p2_price=p2_price,
                            p2_val=p2_ind,
                            candles_ago=n - 1 - p2_idx,
                            score_impact=15,
                            is_bullish=True
                        )
                        if not any(s.type == sig.type and s.indicator == sig.indicator for s in result.signals):
                            result.signals.append(sig)
                            break

        # --- B) TEPE UYUMSUZLUKLARI (BEARISH DIVERGENCES) ---
        # Fiyatın son 2-3 tepe noktasını karşılaştır
        if len(price_highs) >= 2:
            for i in range(len(price_highs) - 1, max(-1, len(price_highs) - 4), -1):
                p2_idx = price_highs[i]
                for j in range(i - 1, max(-1, i - 4), -1):
                    p1_idx = price_highs[j]
                    dist = p2_idx - p1_idx
                    if dist < 4 or dist > 35:
                        continue

                    if (n - 1 - p2_idx) > 12:
                        continue

                    p1_price = df_slice['high'].iloc[p1_idx]
                    p2_price = df_slice['high'].iloc[p2_idx]
                    p1_ind = df_slice[indicator_col].iloc[p1_idx]
                    p2_ind = df_slice[indicator_col].iloc[p2_idx]

                    if pd.isna(p1_ind) or pd.isna(p2_ind):
                        continue

                    # 1. Klasik Negatif Uyumsuzluk: Fiyat Daha Yüksek Tepe, İndikatör Daha Düşük Tepe
                    if p2_price > p1_price and p2_ind < p1_ind:
                        sig = DivergenceSignal(
                            type='REGULAR_BEARISH',
                            indicator=indicator_name,
                            name_tr=f"🔴 {indicator_name} Klasik Negatif Uyumsuzluk (Ayı)",
                            description=f"⚠️ **{indicator_name} Negatif Uyumsuzluk (Tepe Yorulması):** Fiyat daha yüksek tepe ({p1_price:.2f} ➔ {p2_price:.2f}) yaparken {indicator_name} momentum kaybetti ({p1_ind:.1f} ➔ {p2_ind:.1f}). Düzeltme ve satış riski yüksek.",
                            p1_time=df_slice['timestamp'].iloc[p1_idx],
                            p1_price=p1_price,
                            p1_val=p1_ind,
                            p2_time=df_slice['timestamp'].iloc[p2_idx],
                            p2_price=p2_price,
                            p2_val=p2_ind,
                            candles_ago=n - 1 - p2_idx,
                            score_impact=-30,
                            is_bullish=False
                        )
                        if not any(s.type == sig.type and s.indicator == sig.indicator for s in result.signals):
                            result.signals.append(sig)
                            break

                    # 2. Gizli Negatif Uyumsuzluk: Fiyat Daha Düşük Tepe, İndikatör Daha Yüksek Tepe
                    elif p2_price < p1_price and p2_ind > p1_ind and p1_ind > 60:
                        sig = DivergenceSignal(
                            type='HIDDEN_BEARISH',
                            indicator=indicator_name,
                            name_tr=f"⚡ {indicator_name} Gizli Negatif Uyumsuzluk (Düşüş Devamı)",
                            description=f"⚡ **{indicator_name} Gizli Negatif Uyumsuzluk:** Fiyat tepeleri düşerken {indicator_name} aşırı şişti ({p1_ind:.1f} ➔ {p2_ind:.1f}). Düşüş trendinin devam baskısını teyit eder.",
                            p1_time=df_slice['timestamp'].iloc[p1_idx],
                            p1_price=p1_price,
                            p1_val=p1_ind,
                            p2_time=df_slice['timestamp'].iloc[p2_idx],
                            p2_price=p2_price,
                            p2_val=p2_ind,
                            candles_ago=n - 1 - p2_idx,
                            score_impact=-15,
                            is_bullish=False
                        )
                        if not any(s.type == sig.type and s.indicator == sig.indicator for s in result.signals):
                            result.signals.append(sig)
                            break

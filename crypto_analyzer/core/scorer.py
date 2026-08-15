import pandas as pd
from core.divergence import DivergenceDetector, DivergenceResult

class AnalysisScorer:
    def __init__(self, high_threshold=75, low_threshold=40):
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

    def evaluate(self, symbol: str, current_price: float, df_row, df: pd.DataFrame = None) -> dict:
        """
        Teknik indikatör değerlerine ve otomatik tepe/dip uyumsuzluklarına (Divergence)
        göre kapsamlı puanlama yapar ve analiz notu üretir.
        """
        rsi = df_row.get('RSI', 50)
        ema_50 = df_row.get('EMA_50', current_price)
        ema_200 = df_row.get('EMA_200', current_price)
        bb_low = df_row.get('BB_Low', current_price)
        bb_high = df_row.get('BB_High', current_price)
        macd = df_row.get('MACD', 0)
        macd_signal = df_row.get('MACD_Signal', 0)
        stoch_k = df_row.get('Stoch_K', 50)

        score = 50  # Nötr başlangıç puanı
        notes = []

        # 1. RSI Değerlendirmesi
        if pd.isna(rsi):
            notes.append("RSI verisi hesaplanamadı.")
        elif rsi < 30:
            score += 20
            notes.append(f"RSI aşırı satım bölgesinde ({rsi:.1f}) - Dip fırsatı olabilir.")
        elif rsi > 70:
            score -= 20
            notes.append(f"RSI aşırı alım bölgesinde ({rsi:.1f}) - Tepe riski / Düzeltme gelebilir.")
        else:
            notes.append(f"RSI dengeli seviyede ({rsi:.1f}).")

        # 2. Trend (EMA) Değerlendirmesi
        if current_price > ema_50 and ema_50 > ema_200:
            score += 25
            notes.append("Fiyat 50 ve 200 EMA'nın üzerinde (Güçlü Yükseliş Trendi - Boğa).")
        elif current_price < ema_50 and ema_50 < ema_200:
            score -= 25
            notes.append("Fiyat 50 ve 200 EMA'nın altında (Güçlü Düşüş Trendi - Ayı).")
        elif current_price < ema_50:
            score -= 15
            notes.append("Fiyat 50 EMA'nın altında (Kısa vadeli baskı mevcut).")
        else:
            notes.append("Trend yatay / karar aşamasında.")

        # 3. Bollinger Bandı Durumu
        if current_price <= bb_low:
            score += 15
            notes.append("Fiyat alt Bollinger bandına temas ediyor (Destek bölgesinde).")
        elif current_price >= bb_high:
            score -= 15
            notes.append("Fiyat üst Bollinger bandına ulaştı (Direnç / Esneme bölgesi).")

        # 4. MACD Kesişimi
        if macd > macd_signal and macd > 0:
            score += 10
            notes.append("MACD pozitif bölgede ve sinyal çizgisinin üzerinde.")
        elif macd < macd_signal and macd < 0:
            score -= 10
            notes.append("MACD negatif bölgede ve satış baskısı devam ediyor.")

        # 5. Otomatik RSI / MACD Uyumsuzluk (Divergence) Tespiti
        div_result = DivergenceResult()
        if df is not None and not df.empty and len(df) >= 30:
            div_result = DivergenceDetector.detect_all(df)
            if div_result.signals:
                score += div_result.total_score_impact
                for sig in div_result.signals:
                    notes.insert(0, sig.description)

        # Puanı 0-100 arasında sınırla
        score = max(0, min(100, score))

        # Karar / Tahmin Notu Belirleme
        if score >= self.high_threshold:
            verdict = "GÜÇLÜ AL / TOPLAMA BÖLGESİ"
        elif score >= 60:
            verdict = "KADEMELİ ALIM YAPILABİLİR"
        elif score <= self.low_threshold:
            verdict = "RİSKLİ / SAT VEYA UZAK DUR"
        else:
            verdict = "NÖTR / İZLEMEDE KAL"

        return {
            "symbol": symbol,
            "price": current_price,
            "rsi": round(rsi, 2) if not pd.isna(rsi) else 0,
            "stoch_k": round(stoch_k, 2) if not pd.isna(stoch_k) else 50,
            "score": score,
            "verdict": verdict,
            "notes": notes,
            "divergence": div_result
        }
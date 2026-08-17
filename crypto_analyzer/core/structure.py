"""
Fiyat Yapısı (Market Structure & Price Action) Modülü
Hesaplanan Bileşenler:
  1. Support / Resistance (Destek ve Direnç Seviyeleri)
  2. Higher High (HH), Higher Low (HL), Lower High (LH), Lower Low (LL)
  3. Trend Detection (Yükselen Trend, Düşüş Trendi, Yatay Piyasa)
  4. Breakout (Yukarı Kırılım) & Breakdown (Aşağı Kırılım)
  5. Doğal Dil Durum Raporu ("BTC şu anda 4H'de yükselen trendde.")
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple

@dataclass
class StructurePoint:
    index: int
    timestamp: pd.Timestamp
    price: float
    point_type: str      # 'HH', 'LH', 'HL', 'LL'
    name_tr: str         # 'Yüksek Tepe (HH)', 'Düşük Dip (LL)' vb.
    is_high: bool        # True: Tepe, False: Dip
    candles_ago: int     # Kaç mum önce oluştu

@dataclass
class MarketStructureResult:
    symbol: str
    timeframe: str
    current_price: float
    trend: str                        # 'UPTREND', 'DOWNTREND', 'RANGING'
    trend_name_tr: str                # 'YÜKSELEN TREND (Boğa Yapısı)' vb.
    trend_badge: str                  # '🟢 YÜKSELEN TREND'
    statement: str                    # "BTC/USDT şu anda 4H zaman diliminde YÜKSELEN TRENDDE."
    points: List[StructurePoint] = field(default_factory=list)
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
    nearest_support: Optional[float] = None
    nearest_resistance: Optional[float] = None
    dist_to_support_pct: Optional[float] = None
    dist_to_resistance_pct: Optional[float] = None
    is_breakout: bool = False
    is_breakdown: bool = False
    breakout_details: Optional[str] = None
    summary_notes: List[str] = field(default_factory=list)

class PriceStructureAnalyzer:
    """
    Mum grafiklerindeki tepe ve dip hareketlerini analiz ederek
    piyasa yapısını ve trend yönünü belirleyen analiz motoru.
    """

    @staticmethod
    def _find_swing_pivots(df: pd.DataFrame, window: int = 3) -> Tuple[List[int], List[int]]:
        """
        Grafikteki yerel tepe (Swing High) ve dip (Swing Low) indekslerini döner.
        """
        n = len(df)
        highs = []
        lows = []

        for i in range(window, n - window):
            high_val = df['high'].iloc[i]
            low_val = df['low'].iloc[i]

            # Tepe kontrolü
            if all(high_val >= df['high'].iloc[i - k] for k in range(1, window + 1)) and \
               all(high_val >= df['high'].iloc[i + k] for k in range(1, window + 1)):
                highs.append(i)

            # Dip kontrolü
            if all(low_val <= df['low'].iloc[i - k] for k in range(1, window + 1)) and \
               all(low_val <= df['low'].iloc[i + k] for k in range(1, window + 1)):
                lows.append(i)

        return lows, highs

    @classmethod
    def analyze(cls, df: pd.DataFrame, symbol: str = "BTC/USDT", timeframe: str = "4h", window: int = 3) -> MarketStructureResult:
        """
        Verilen OHLCV verisi üzerinde fiyat yapısı analizini çalıştırır.
        """
        if df is None or df.empty or len(df) < 20:
            return MarketStructureResult(
                symbol=symbol,
                timeframe=timeframe,
                current_price=0.0,
                trend="UNKNOWN",
                trend_name_tr="Yetersiz Veri",
                trend_badge="⚪ BELİRSİZ",
                statement=f"{symbol} için piyasa yapısını belirlemek amacıyla yeterli veri bulunamadı."
            )

        n = len(df)
        current_price = float(df['close'].iloc[-1])
        low_indices, high_indices = cls._find_swing_pivots(df, window=window)

        # -------------------------------------------------------------
        # 1. TEPE VE DİPLERİ SINIFLANDIR (HH, LH, HL, LL)
        # -------------------------------------------------------------
        structure_points: List[StructurePoint] = []

        # A) Tepelerin Sınıflandırılması (Highs -> HH veya LH)
        prev_high_price = None
        for idx in high_indices:
            p_price = float(df['high'].iloc[idx])
            p_time = df['timestamp'].iloc[idx]
            candles_ago = n - 1 - idx

            if prev_high_price is None:
                pt_type = "HIGH"
                pt_name = "Tepe"
            elif p_price > prev_high_price:
                pt_type = "HH"
                pt_name = "Yüksek Tepe (Higher High)"
            else:
                pt_type = "LH"
                pt_name = "Düşük Tepe (Lower High)"

            structure_points.append(StructurePoint(
                index=idx,
                timestamp=p_time,
                price=p_price,
                point_type=pt_type,
                name_tr=pt_name,
                is_high=True,
                candles_ago=candles_ago
            ))
            prev_high_price = p_price

        # B) Dipllerin Sınıflandırılması (Lows -> HL veya LL)
        prev_low_price = None
        for idx in low_indices:
            p_price = float(df['low'].iloc[idx])
            p_time = df['timestamp'].iloc[idx]
            candles_ago = n - 1 - idx

            if prev_low_price is None:
                pt_type = "LOW"
                pt_name = "Dip"
            elif p_price >= prev_low_price:
                pt_type = "HL"
                pt_name = "Yüksek Dip (Higher Low)"
            else:
                pt_type = "LL"
                pt_name = "Düşük Dip (Lower Low)"

            structure_points.append(StructurePoint(
                index=idx,
                timestamp=p_time,
                price=p_price,
                point_type=pt_type,
                name_tr=pt_name,
                is_high=False,
                candles_ago=candles_ago
            ))
            prev_low_price = p_price

        # Kronolojik sıraya diz
        structure_points.sort(key=lambda p: p.index)

        # -------------------------------------------------------------
        # 2. TREND TESPİTİ (TREND DETECTION)
        # -------------------------------------------------------------
        recent_highs = [p for p in structure_points if p.is_high][-3:]
        recent_lows = [p for p in structure_points if not p.is_high][-3:]

        is_uptrend = False
        is_downtrend = False

        if len(recent_highs) >= 2 and len(recent_lows) >= 2:
            last_h = recent_highs[-1]
            last_l = recent_lows[-1]

            # Son tepe HH ve son dip HL ise -> Yükselen Trend
            if last_h.point_type == "HH" and last_l.point_type == "HL":
                is_uptrend = True
            # Son tepe LH ve son dip LL ise -> Düşüş Trendi
            elif last_h.point_type == "LH" and last_l.point_type == "LL":
                is_downtrend = True
            elif last_h.point_type == "HH" and last_l.point_type == "LL":
                # Genişleyen yapı / volatilite artışı
                is_uptrend = (current_price > (last_h.price + last_l.price) / 2)
                is_downtrend = not is_uptrend
            elif last_h.point_type == "LH" and last_l.point_type == "HL":
                # Sıkışan yapı (Simetrik üçgen / testere)
                is_uptrend = False
                is_downtrend = False
        elif len(recent_highs) >= 1 and len(recent_lows) >= 1:
            # Yedek: Fiyatın son pivotlara göre konumu
            if current_price > recent_highs[-1].price:
                is_uptrend = True
            elif current_price < recent_lows[-1].price:
                is_downtrend = True

        if is_uptrend:
            trend = "UPTREND"
            trend_name_tr = "YÜKSELEN TREND (Boğa Yapısı)"
            trend_badge = "🟢 YÜKSELEN TREND"
            trend_verb = "yükselen trendde"
        elif is_downtrend:
            trend = "DOWNTREND"
            trend_name_tr = "DÜŞÜŞ TRENDİ (Ayı Yapısı)"
            trend_badge = "🔴 DÜŞÜŞ TRENDİ"
            trend_verb = "düşüş trendinde"
        else:
            trend = "RANGING"
            trend_name_tr = "YATAY / KONSOLİDASYON (Testere Piyasası)"
            trend_badge = "🟡 YATAY PİYASA"
            trend_verb = "yatay / kararsız konsolidasyon aşamasında"

        # -------------------------------------------------------------
        # 3. DESTEK VE DİRENÇ KÜMELEMESİ (SUPPORT & RESISTANCE)
        # -------------------------------------------------------------
        all_low_prices = [p.price for p in structure_points if not p.is_high]
        all_high_prices = [p.price for p in structure_points if p.is_high]

        # En yakın destekler (fiyatın altındakiler)
        supports_below = sorted([p for p in all_low_prices if p < current_price], reverse=True)
        # En yakın dirençler (fiyatın üstündekiler)
        resistances_above = sorted([p for p in all_high_prices if p > current_price])

        nearest_support = supports_below[0] if supports_below else (min(all_low_prices) if all_low_prices else None)
        nearest_resistance = resistances_above[0] if resistances_above else (max(all_high_prices) if all_high_prices else None)

        dist_to_sup_pct = round(((current_price - nearest_support) / current_price) * 100.0, 2) if nearest_support else None
        dist_to_res_pct = round(((nearest_resistance - current_price) / current_price) * 100.0, 2) if nearest_resistance else None

        # -------------------------------------------------------------
        # 4. KIRILIM TESPİTİ (BREAKOUT / BREAKDOWN)
        # -------------------------------------------------------------
        is_breakout = False
        is_breakdown = False
        breakout_details = None

        if len(recent_highs) >= 2:
            prev_swing_high = recent_highs[-2].price if len(recent_highs) >= 2 else recent_highs[-1].price
            # Son mum veya bir önceki mum direnci yukarı kırdı mı?
            if current_price > prev_swing_high and df['close'].iloc[-2] <= prev_swing_high:
                is_breakout = True
                breakout_details = f"⚡ YUKARI KIRILIM (Breakout): Fiyat {prev_swing_high:,.2f} USDT direncini yukarı kırdı!"

        if len(recent_lows) >= 2:
            prev_swing_low = recent_lows[-2].price if len(recent_lows) >= 2 else recent_lows[-1].price
            # Son mum desteği aşağı kırdı mı?
            if current_price < prev_swing_low and df['close'].iloc[-2] >= prev_swing_low:
                is_breakdown = True
                breakout_details = f"⚡ AŞAĞI KIRILIM (Breakdown): Fiyat {prev_swing_low:,.2f} USDT desteğini aşağı kırdı!"

        # -------------------------------------------------------------
        # 5. NET DURUM CÜMLESİ VE NOTLAR
        # -------------------------------------------------------------
        last_pts_str = " - ".join([f"{p.point_type} ({p.price:,.2f})" for p in structure_points[-3:]]) if structure_points else ""
        
        statement_parts = [f"**{symbol}** şu anda **{timeframe.upper()}** zaman diliminde **{trend_verb}**."]
        if nearest_support and nearest_resistance:
            statement_parts.append(f"En yakın destek: `{nearest_support:,.2f} USDT` (Uzaklık: %{dist_to_sup_pct}), en yakın direnç: `{nearest_resistance:,.2f} USDT` (Uzaklık: %{dist_to_res_pct}).")
        
        statement = " ".join(statement_parts)

        notes = []
        if is_breakout and breakout_details:
            notes.append(breakout_details)
        if is_breakdown and breakout_details:
            notes.append(breakout_details)
        if last_pts_str:
            notes.append(f"Son Fiyat Yapısı Dizilimi: {last_pts_str}")
        if is_uptrend:
            notes.append("Fiyat yapısı yükselen tepeler (HH) ve yükselen dipler (HL) oluşturarak boğa piyasasını koruyor.")
        elif is_downtrend:
            notes.append("Fiyat yapısı alçalan tepeler (LH) ve alçalan dipler (LL) ile düşüş trendi baskısını sürdürüyor.")
        else:
            notes.append("Fiyat net bir kırılım yapmadan belirli bir bant aralığında konsolide oluyor.")

        return MarketStructureResult(
            symbol=symbol,
            timeframe=timeframe,
            current_price=current_price,
            trend=trend,
            trend_name_tr=trend_name_tr,
            trend_badge=trend_badge,
            statement=statement,
            points=structure_points,
            support_levels=supports_below,
            resistance_levels=resistances_above,
            nearest_support=nearest_support,
            nearest_resistance=nearest_resistance,
            dist_to_support_pct=dist_to_sup_pct,
            dist_to_resistance_pct=dist_to_res_pct,
            is_breakout=is_breakout,
            is_breakdown=is_breakdown,
            breakout_details=breakout_details,
            summary_notes=notes
        )

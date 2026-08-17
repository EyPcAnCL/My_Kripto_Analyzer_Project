import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.settings import SUPPORTED_TIMEFRAMES, DEFAULT_TIMEFRAME
from services.exchange_service import ExchangeService
from services.market_data_service import MarketDataService
from services.indicator_service import IndicatorService
from core.structure import PriceStructureAnalyzer
from database.connection import init_db

init_db()

st.set_page_config(
    page_title="Kripto Fiyat Yapısı & Teknik Analiz Platformu",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS
st.markdown("""
<style>
    .metric-container {
        background-color: #1e222d;
        border: 1px solid #2a2e39;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 8px;
    }
    .metric-title {
        color: #90a4ae;
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-val {
        color: #ffffff;
        font-size: 18px;
        font-weight: bold;
    }
    .statement-box-up {
        background-color: rgba(0, 200, 83, 0.12);
        border: 1px solid #00c853;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .statement-box-down {
        background-color: rgba(255, 82, 82, 0.12);
        border: 1px solid #ff5252;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
    .statement-box-range {
        background-color: rgba(255, 235, 59, 0.12);
        border: 1px solid #fbc02d;
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 16px;
    }
</style>
""", unsafe_allow_html=True)

st.title("⚡ Kripto Fiyat Yapısı & Teknik Analiz Platformu")
st.caption("Fiyat Yapısı (Market Structure), Destek/Direnç Seviyeleri, HH/HL/LH/LL Tespiti, Trend Yönü ve Sayısal İndikatör Katmanı.")

# Kenar Çubuğu
st.sidebar.header("⚙️ Genel Ayarlar")
selected_exchange = st.sidebar.selectbox("Borsa Seçimi", ["binance", "kucoin", "gate", "bybit", "okx"], index=0)

market_service = MarketDataService(exchange_id=selected_exchange)
indicator_service = IndicatorService(exchange_id=selected_exchange)

# Sekmeler
tab_structure, tab_indicators, tab_ohlcv, tab_storage = st.tabs([
    "🏛️ Fiyat Yapısı & Trend Durumu",
    "📊 8 Temel İndikatör (Sayısal)",
    "📦 OHLCV Veri Toplama",
    "💾 Veritabanı Arşivi"
])


# ==========================================================
# SEKME 1: FİYAT YAPISI & TREND TESPİTİ (MARKET STRUCTURE)
# ==========================================================
with tab_structure:
    st.markdown("### 🏛️ Fiyat Yapısı (Market Structure) & Trend Tespiti")
    st.caption("Piyasa tepe ve dipleri (HH, HL, LH, LL), dinamik destek/direnç seviyeleri, trend yönü ve kırılımlar.")

    col_s1, col_s2, col_s3, col_s4 = st.columns([3, 2, 2, 2])
    with col_s1:
        struct_coin_raw = st.text_input("🪙 Coin Ara / Gir", value="BTC", placeholder="Örn: BTC, ETH, SOL, PEPE, SUI...", key="struct_coin_input")
    with col_s2:
        struct_tf = st.selectbox("Zaman Dilimi", SUPPORTED_TIMEFRAMES, index=4, key="struct_tf_select") # 4h
    with col_s3:
        struct_limit = st.slider("İncelenecek Mum Sayısı", min_value=50, max_value=500, value=150, step=25, key="struct_limit_slider")
    with col_s4:
        st.write("")
        st.write("")
        struct_btn = st.button("🔍 Fiyat Yapısını Analiz Et", type="primary", key="btn_calc_struct")

    struct_symbol = ExchangeService.normalize_symbol(struct_coin_raw)

    df_struct = pd.DataFrame()
    if struct_btn or "last_struct_symbol" in st.session_state:
        if struct_btn:
            with st.spinner(f"⏳ {struct_symbol} [{struct_tf}] için fiyat yapısı analiz ediliyor..."):
                df_struct = market_service.get_candles(struct_symbol, timeframe=struct_tf, limit=struct_limit, auto_fetch=True)
                st.session_state["last_struct_symbol"] = struct_symbol
                st.session_state["last_struct_tf"] = struct_tf
                st.session_state["df_struct"] = df_struct
        else:
            df_struct = st.session_state.get("df_struct", pd.DataFrame())

    if not df_struct.empty and len(df_struct) >= 20:
        struct_res = PriceStructureAnalyzer.analyze(df_struct, symbol=struct_symbol, timeframe=struct_tf)

        st.markdown("---")

        # 1. BÜYÜK DURUM BİLDİRİM KUTUSU (STATEMENT BANNER)
        box_class = "statement-box-up" if struct_res.trend == "UPTREND" else ("statement-box-down" if struct_res.trend == "DOWNTREND" else "statement-box-range")
        st.markdown(f"""
        <div class="{box_class}">
            <div style="font-size:22px; font-weight:bold; margin-bottom:6px;">
                {struct_res.trend_badge} — {struct_res.trend_name_tr}
            </div>
            <div style="font-size:16px; color:#eceff1;">
                📢 {struct_res.statement}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # 2. ÜST METRİKLER & DESTEK/DİRENÇ KARTLARI
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Son Fiyat", f"{struct_res.current_price:,.2f} USDT")
        with m2:
            st.metric(
                "En Yakın Destek",
                f"{struct_res.nearest_support:,.2f} USDT" if struct_res.nearest_support else "-",
                delta=f"-%{struct_res.dist_to_support_pct}" if struct_res.dist_to_support_pct else None,
                delta_color="normal"
            )
        with m3:
            st.metric(
                "En Yakın Direnç",
                f"{struct_res.nearest_resistance:,.2f} USDT" if struct_res.nearest_resistance else "-",
                delta=f"+%{struct_res.dist_to_resistance_pct}" if struct_res.dist_to_resistance_pct else None,
                delta_color="inverse"
            )
        with m4:
            last_pt = struct_res.points[-1] if struct_res.points else None
            st.metric("Son Yapı Noktası", f"{last_pt.point_type} ({last_pt.price:,.2f})" if last_pt else "-")

        # Kırılım Uyarısı (Breakout / Breakdown)
        if struct_res.is_breakout:
            st.success(f"### {struct_res.breakout_details}")
        if struct_res.is_breakdown:
            st.error(f"### {struct_res.breakout_details}")

        # 3. PLOTLY FİYAT YAPISI GRAFİĞİ (MUMLAR + HH/HL/LH/LL ETİKETLERİ + DESTEK/DİRENÇ)
        fig_struct = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f"{struct_symbol} Fiyat Yapısı (HH, HL, LH, LL ve Destek/Direnç Çizgileri)", "İşlem Hacmi (Volume)"),
            row_heights=[0.75, 0.25]
        )

        # Mumlar
        fig_struct.add_trace(go.Candlestick(
            x=df_struct['timestamp'],
            open=df_struct['open'], high=df_struct['high'], low=df_struct['low'], close=df_struct['close'],
            name='Mumlar', increasing_line_color='#00e676', decreasing_line_color='#ff5252'
        ), row=1, col=1)

        # Fiyat Yapısı Noktalarını (HH, HL, LH, LL) Grafiğe Ekle
        for pt in struct_res.points:
            color = '#00e676' if pt.point_type in ['HH', 'HL'] else ('#ff5252' if pt.point_type in ['LH', 'LL'] else '#ffeb3b')
            pos = "top center" if pt.is_high else "bottom center"

            fig_struct.add_trace(go.Scatter(
                x=[pt.timestamp],
                y=[pt.price],
                mode='markers+text',
                name=f"{pt.point_type} ({pt.price:,.2f})",
                text=[f"<b>{pt.point_type}</b>"],
                textposition=pos,
                textfont=dict(size=11, color=color),
                marker=dict(size=8, color=color, symbol='circle'),
                showlegend=False
            ), row=1, col=1)

        # Destek ve Direnç Yatay Çizgileri
        if struct_res.nearest_support:
            fig_struct.add_hline(
                y=struct_res.nearest_support,
                line_dash="dash", line_color="#00e676", line_width=1.5,
                annotation_text=f"Destek: {struct_res.nearest_support:,.2f}",
                annotation_position="bottom right",
                row=1, col=1
            )

        if struct_res.nearest_resistance:
            fig_struct.add_hline(
                y=struct_res.nearest_resistance,
                line_dash="dash", line_color="#ff5252", line_width=1.5,
                annotation_text=f"Direnç: {struct_res.nearest_resistance:,.2f}",
                annotation_position="top right",
                row=1, col=1
            )

        # Hacim
        vol_colors = ['#00e676' if row['close'] >= row['open'] else '#ff5252' for _, row in df_struct.iterrows()]
        fig_struct.add_trace(go.Bar(
            x=df_struct['timestamp'], y=df_struct['volume'],
            name='Volume', marker_color=vol_colors, showlegend=False
        ), row=2, col=1)

        fig_struct.update_layout(
            template="plotly_dark",
            height=650,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="x unified"
        )

        st.plotly_chart(fig_struct, use_container_width=True)

        # 4. YAPI NOTLARI VE PİVOT LİSTESİ
        col_nt1, col_nt2 = st.columns([1, 1])
        with col_nt1:
            st.markdown("##### 📝 Fiyat Yapısı Analiz Özeti")
            for note in struct_res.summary_notes:
                st.markdown(f"- {note}")

        with col_nt2:
            st.markdown("##### 📍 Son Tepe ve Dip Noktaları (Pivots)")
            pts_data = [{
                'Tür': pt.point_type,
                'Açıklama': pt.name_tr,
                'Fiyat (USDT)': f"{pt.price:,.2f}",
                'Tarih': pt.timestamp.strftime('%Y-%m-%d %H:%M'),
                'Mum Önce': f"{pt.candles_ago} mum"
            } for pt in reversed(struct_res.points[-8:])]
            st.dataframe(pd.DataFrame(pts_data), use_container_width=True, hide_index=True)

    else:
        st.info("👈 Coini ve zaman dilimini seçip **'Fiyat Yapısını Analiz Et'** butonuna tıklayarak piyasa yapısını görüntüleyebilirsiniz.")


# ==========================================================
# SEKME 2: 8 TEMEL İNDİKATÖR SAYISAL PANELİ
# ==========================================================
with tab_indicators:
    st.markdown("### 🔢 8 Temel Teknik Göstergenin Sayısal Değerleri")
    st.caption("Al/Sat kararlarına dönüştürülmeden, indikatörlerin ham matematiksel ve sayısal çıktıları.")

    col_i1, col_i2, col_i3, col_i4 = st.columns([3, 2, 2, 2])
    with col_i1:
        ind_coin_raw = st.text_input("🪙 Coin Ara / Gir", value="BTC", placeholder="Örn: BTC, ETH, SOL, PEPE, SUI...", key="ind_coin_input")
    with col_i2:
        ind_tf = st.selectbox("Zaman Dilimi", SUPPORTED_TIMEFRAMES, index=4, key="ind_tf_select")
    with col_i3:
        ind_limit = st.slider("İncelenecek Mum Sayısı", min_value=50, max_value=1000, value=250, step=50, key="ind_limit_slider")
    with col_i4:
        st.write("")
        st.write("")
        calc_btn = st.button("🚀 İndikatörleri Hesapla & Kaydet", type="primary", key="btn_calc_ind")

    ind_symbol = ExchangeService.normalize_symbol(ind_coin_raw)

    df_ind = pd.DataFrame()
    if calc_btn or "last_ind_symbol" in st.session_state:
        if calc_btn:
            with st.spinner(f"⏳ {ind_symbol} [{ind_tf}] için indikatörler hesaplanıyor ve veritabanına kaydediliyor..."):
                df_ind = indicator_service.compute_and_save(ind_symbol, timeframe=ind_tf, limit=ind_limit)
                st.session_state["last_ind_symbol"] = ind_symbol
                st.session_state["last_ind_tf"] = ind_tf
                st.session_state["df_ind"] = df_ind
        else:
            df_ind = st.session_state.get("df_ind", pd.DataFrame())

    if not df_ind.empty and len(df_ind) >= 14:
        latest = df_ind.iloc[-1]

        st.markdown("---")
        st.subheader(f"📌 {ind_symbol} [{ind_tf.upper()}] — En Güncel Sayısal Değerler")
        st.caption(f"Son Mum Zamanı: `{latest['timestamp']}` | Kapanış: `{latest['close']} USDT`")

        r1_c1, r1_c2, r1_c3, r1_c4 = st.columns(4)
        with r1_c1:
            st.markdown("#### 1. SMA Değerleri")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">SMA 20</div>
                <div class="metric-val">{latest.get('SMA_20', 0):,.2f}</div>
                <div class="metric-title" style="margin-top:6px;">SMA 50</div>
                <div class="metric-val">{latest.get('SMA_50', 0):,.2f}</div>
                <div class="metric-title" style="margin-top:6px;">SMA 200</div>
                <div class="metric-val">{latest.get('SMA_200', 0):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with r1_c2:
            st.markdown("#### 2. EMA Değerleri")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">EMA 9 / EMA 21</div>
                <div class="metric-val">{latest.get('EMA_9', 0):,.2f} / {latest.get('EMA_21', 0):,.2f}</div>
                <div class="metric-title" style="margin-top:6px;">EMA 50</div>
                <div class="metric-val">{latest.get('EMA_50', 0):,.2f}</div>
                <div class="metric-title" style="margin-top:6px;">EMA 200</div>
                <div class="metric-val">{latest.get('EMA_200', 0):,.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with r1_c3:
            st.markdown("#### 3. RSI (14)")
            rsi_val = latest.get('RSI', 50)
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">RSI Değeri</div>
                <div class="metric-val">{rsi_val:.2f}</div>
                <div class="metric-title" style="margin-top:6px;">Referans Aralıkları</div>
                <div style="font-size:13px; color:#b0bec5;">Aşırı Satım &lt; 30 | Aşırı Alım &gt; 70</div>
            </div>
            """, unsafe_allow_html=True)

        with r1_c4:
            st.markdown("#### 4. MACD (12, 26, 9)")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">MACD Çizgisi</div>
                <div class="metric-val">{latest.get('MACD', 0):.4f}</div>
                <div class="metric-title" style="margin-top:6px;">Sinyal Çizgisi</div>
                <div class="metric-val">{latest.get('MACD_Signal', 0):.4f}</div>
                <div class="metric-title" style="margin-top:6px;">Histogram (Diff)</div>
                <div class="metric-val">{latest.get('MACD_Hist', 0):.4f}</div>
            </div>
            """, unsafe_allow_html=True)

        r2_c1, r2_c2, r2_c3, r2_c4 = st.columns(4)
        with r2_c1:
            st.markdown("#### 5. Bollinger Bands")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">Üst Bant (BB High)</div>
                <div class="metric-val">{latest.get('BB_High', 0):,.2f}</div>
                <div class="metric-title" style="margin-top:6px;">Orta Bant (BB Mid)</div>
                <div class="metric-val">{latest.get('BB_Mid', 0):,.2f}</div>
                <div class="metric-title" style="margin-top:6px;">Alt Bant (BB Low)</div>
                <div class="metric-val">{latest.get('BB_Low', 0):,.2f}</div>
                <div class="metric-title" style="margin-top:6px;">Bant Genişliği (Width)</div>
                <div class="metric-val">%{latest.get('BB_Width', 0):.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with r2_c2:
            st.markdown("#### 6. ATR (Volatilite)")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">ATR (14) Değeri</div>
                <div class="metric-val">{latest.get('ATR', 0):,.2f} USDT</div>
                <div class="metric-title" style="margin-top:6px;">Volatilite Yüzdesi</div>
                <div class="metric-val">%{((latest.get('ATR', 0) / latest['close']) * 100):.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with r2_c3:
            st.markdown("#### 7. Stochastic RSI")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">Stoch %K (Hızlı)</div>
                <div class="metric-val">{latest.get('Stoch_K', 0):.2f}</div>
                <div class="metric-title" style="margin-top:6px;">Stoch %D (Yavaş)</div>
                <div class="metric-val">{latest.get('Stoch_D', 0):.2f}</div>
            </div>
            """, unsafe_allow_html=True)

        with r2_c4:
            st.markdown("#### 8. ADX (Trend Gücü)")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">ADX Değeri</div>
                <div class="metric-val">{latest.get('ADX', 0):.2f}</div>
                <div class="metric-title" style="margin-top:6px;">+DI / -DI Yön Değerleri</div>
                <div class="metric-val">{latest.get('ADX_Pos_DI', 0):.1f} / {latest.get('ADX_Neg_DI', 0):.1f}</div>
            </div>
            """, unsafe_allow_html=True)


# ==========================================================
# SEKME 3: OHLCV VERİ TOPLAMA
# ==========================================================
with tab_ohlcv:
    st.markdown("### 📦 Çoklu Zaman Dilimli OHLCV Veri Toplama")

    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        coin_input = st.text_input("🪙 Coin Sembolü", value="BTC", placeholder="Örn: BTC, ETH, SOL, PEPE, SUI...", key="view_coin_input")
    with c2:
        tf_select = st.selectbox("Zaman Dilimi", SUPPORTED_TIMEFRAMES, index=4, key="view_tf_select")
    with c3:
        candle_limit = st.slider("Mum Sayısı", min_value=50, max_value=1500, value=200, step=50, key="view_limit")
    with c4:
        st.write("")
        st.write("")
        fetch_btn = st.button("📥 Veriyi Çek & Kaydet", type="primary", key="btn_fetch_single")

    symbol = ExchangeService.normalize_symbol(coin_input)

    st.markdown("---")
    multi_c1, multi_c2 = st.columns([4, 2])
    with multi_c1:
        st.write("💡 **Tek Tıkla Tüm Zaman Dilimlerini (1m, 5m, 15m, 1h, 4h, 1D) İndir ve Veritabanına Arşivle:**")
    with multi_c2:
        if st.button("🚀 Tüm Zaman Dilimlerini Arşivle (500 Mum)", key="btn_fetch_all_tf"):
            with st.spinner(f"⏳ {symbol} için tüm zaman dilimleri toplanıyor ve veritabanına kaydediliyor..."):
                res = market_service.collect_all_timeframes(symbol, candles_per_tf=500)
                st.success(f"✅ {symbol} için tüm zaman dilimleri arşivlendi: {res}")


# ==========================================================
# SEKME 4: VERİTABANI ARŞİVİ & DURUM
# ==========================================================
with tab_storage:
    st.markdown("### 💾 SQLite Veritabanı Saklama Özeti")
    st.caption("Veritabanında kalıcı olarak saklanan tüm pariteler, zaman dilimleri ve mum istatistikleri.")

    df_summary = market_service.get_summary()

    if not df_summary.empty:
        st.dataframe(df_summary, use_container_width=True, hide_index=True)

        st.markdown("---")
        st.markdown("#### 🗑️ Veritabanı Temizleme")
        del_c1, del_c2, del_c3 = st.columns([3, 2, 2])
        with del_c1:
            del_sym = st.selectbox("Silinecek Sembol", df_summary['Sembol'].unique(), key="sel_del_sym")
        with del_c2:
            del_tf = st.selectbox("Zaman Dilimi (İsteğe Bağlı)", ["Tümü"] + SUPPORTED_TIMEFRAMES, key="sel_del_tf")
        with del_c3:
            st.write("")
            st.write("")
            if st.button("🗑️ Seçili Veriyi Sil", key="btn_del_db_data"):
                tf_arg = None if del_tf == "Tümü" else del_tf
                deleted_rows = market_service.remove_coin_data(del_sym, timeframe=tf_arg)
                st.success(f"{del_sym} ({del_tf}) için {deleted_rows} mum silindi.")
                st.rerun()
    else:
        st.info("ℹ️ Veritabanında henüz kayıtlı OHLCV verisi bulunmuyor.")
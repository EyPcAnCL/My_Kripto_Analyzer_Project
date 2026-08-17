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
from database.connection import init_db

init_db()

st.set_page_config(
    page_title="Kripto Fiyat & Sayısal İndikatör Platformu",
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
</style>
""", unsafe_allow_html=True)

st.title("⚡ Kripto Fiyat & Sayısal İndikatör Platformu")
st.caption("8 Temel Teknik Göstergenin (SMA, EMA, RSI, MACD, Bollinger, ATR, StochRSI, ADX) net sayısal verileri ve çoklu zaman dilimli OHLCV arşivi.")

# Kenar Çubuğu
st.sidebar.header("⚙️ Genel Ayarlar")
selected_exchange = st.sidebar.selectbox("Borsa Seçimi", ["binance", "kucoin", "gate", "bybit", "okx"], index=0)

market_service = MarketDataService(exchange_id=selected_exchange)
indicator_service = IndicatorService(exchange_id=selected_exchange)

# Sekmeler
tab_indicators, tab_ohlcv, tab_storage = st.tabs([
    "📊 8 Temel İndikatör (Sayısal Veriler)",
    "📦 OHLCV Veri Toplama",
    "💾 Veritabanı Arşivi & Durum"
])

# ==========================================================
# SEKME 1: 8 TEMEL İNDİKATÖR SAYISAL PANELİ
# ==========================================================
with tab_indicators:
    st.markdown("### 🔢 8 Temel Teknik Göstergenin Sayısal Değerleri")
    st.caption("Al/Sat kararlarına dönüştürülmeden, indikatörlerin ham matematiksel ve sayısal çıktıları.")

    col_i1, col_i2, col_i3, col_i4 = st.columns([3, 2, 2, 2])
    with col_i1:
        ind_coin_raw = st.text_input("🪙 Coin Ara / Gir", value="BTC", placeholder="Örn: BTC, ETH, SOL, PEPE, SUI...", key="ind_coin_input")
    with col_i2:
        ind_tf = st.selectbox("Zaman Dilimi", SUPPORTED_TIMEFRAMES, index=4, key="ind_tf_select") # 4h
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
        prev = df_ind.iloc[-2] if len(df_ind) > 1 else latest

        st.markdown("---")
        st.subheader(f"📌 {ind_symbol} [{ind_tf.upper()}] — En Güncel Sayısal Değerler")
        st.caption(f"Son Mum Zamanı: `{latest['timestamp']}` | Kapanış: `{latest['close']} USDT`")

        # -------------------------------------------------------------
        # 8 İNDİKATÖRÜN SAYISAL KARTLARI
        # -------------------------------------------------------------
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
                <div class="metric-title" style="margin-top:6px;">+DI (Alıcı Gücü) / -DI (Satıcı Gücü)</div>
                <div class="metric-val">{latest.get('ADX_Pos_DI', 0):.1f} / {latest.get('ADX_Neg_DI', 0):.1f}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # -------------------------------------------------------------
        # ÇOKLU KATMANLI PLOTLY İNDİKATÖR GRAFİKLERİ
        # -------------------------------------------------------------
        fig_multi = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(
                f"{ind_symbol} Fiyat, SMA, EMA & Bollinger Bantları",
                "RSI (14) & Stochastic RSI (K, D)",
                "MACD (12, 26, 9)",
                "ADX Trend Gücü & ATR Volatilite"
            ),
            row_heights=[0.45, 0.20, 0.20, 0.15]
        )

        # 1. Panel: Fiyat + SMA + EMA + Bollinger
        fig_multi.add_trace(go.Candlestick(
            x=df_ind['timestamp'],
            open=df_ind['open'], high=df_ind['high'], low=df_ind['low'], close=df_ind['close'],
            name='Fiyat', increasing_line_color='#00e676', decreasing_line_color='#ff5252'
        ), row=1, col=1)

        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['SMA_20'], mode='lines', name='SMA 20', line=dict(color='#ffeb3b', width=1.2)), row=1, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['EMA_50'], mode='lines', name='EMA 50', line=dict(color='#ff9800', width=1.5)), row=1, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['EMA_200'], mode='lines', name='EMA 200', line=dict(color='#29b6f6', width=2)), row=1, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['BB_High'], mode='lines', name='BB Üst', line=dict(color='rgba(255, 255, 255, 0.25)', width=1, dash='dot')), row=1, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['BB_Low'], mode='lines', name='BB Alt', line=dict(color='rgba(255, 255, 255, 0.25)', width=1, dash='dot'), fill='tonexty', fillcolor='rgba(255, 255, 255, 0.02)'), row=1, col=1)

        # 2. Panel: RSI + StochRSI
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['RSI'], mode='lines', name='RSI (14)', line=dict(color='#ab47bc', width=2)), row=2, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['Stoch_K'], mode='lines', name='Stoch %K', line=dict(color='#00e5ff', width=1.2, dash='dash')), row=2, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['Stoch_D'], mode='lines', name='Stoch %D', line=dict(color='#ff4081', width=1.2, dash='dash')), row=2, col=1)
        fig_multi.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig_multi.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

        # 3. Panel: MACD
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['MACD'], mode='lines', name='MACD', line=dict(color='#00e676', width=1.5)), row=3, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['MACD_Signal'], mode='lines', name='Sinyal', line=dict(color='#ff5252', width=1.5)), row=3, col=1)
        hist_colors = ['#00e676' if val >= 0 else '#ff5252' for val in df_ind['MACD_Hist']]
        fig_multi.add_trace(go.Bar(x=df_ind['timestamp'], y=df_ind['MACD_Hist'], name='Histogram', marker_color=hist_colors), row=3, col=1)

        # 4. Panel: ADX
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['ADX'], mode='lines', name='ADX (14)', line=dict(color='#ffffff', width=2)), row=4, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['ADX_Pos_DI'], mode='lines', name='+DI (Alıcı)', line=dict(color='#00e676', width=1.2)), row=4, col=1)
        fig_multi.add_trace(go.Scatter(x=df_ind['timestamp'], y=df_ind['ADX_Neg_DI'], mode='lines', name='-DI (Satıcı)', line=dict(color='#ff5252', width=1.2)), row=4, col=1)
        fig_multi.add_hline(y=25, line_dash="dash", line_color="yellow", row=4, col=1)

        fig_multi.update_layout(
            template="plotly_dark",
            height=900,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="x unified"
        )
        st.plotly_chart(fig_multi, use_container_width=True)

        # Sayısal Veri Tablosu
        with st.expander("📄 Tüm Hesaplanmış Sayısal İndikatör Tablosu (Son 50 Mum)", expanded=False):
            st.dataframe(df_ind.tail(50), use_container_width=True, hide_index=True)
            csv_ind = df_ind.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 İndikatör Verilerini CSV Olarak İndir",
                data=csv_ind,
                file_name=f"{ind_symbol.replace('/', '_')}_{ind_tf}_indicators.csv",
                mime="text/csv"
            )
    else:
        st.info("👈 Coini ve zaman dilimini seçip **'İndikatörleri Hesapla & Kaydet'** butonuna tıklayarak sayısal analiz sonuçlarını görüntüleyebilirsiniz.")


# ==========================================================
# SEKME 2: OHLCV VERİ TOPLAMA
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
# SEKME 3: VERİTABANI ARŞİVİ & DURUM
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
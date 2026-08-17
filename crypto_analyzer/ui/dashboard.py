import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from config.settings import SUPPORTED_TIMEFRAMES, DEFAULT_TIMEFRAME, DEFAULT_CANDLE_LIMIT
from services.exchange_service import ExchangeService
from services.market_data_service import MarketDataService
from database.connection import init_db

init_db()

st.set_page_config(
    page_title="Kripto Fiyat Verisi (OHLCV) Yönetim Merkezi",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📦 Kripto Fiyat Verisi (OHLCV) — Temel Katman")
st.caption("Farklı zaman dilimlerinde (1m, 5m, 15m, 1h, 4h, 1D) fiyat mumlarını toplayın, veritabanında saklayın ve görselleştirin.")

# Kenar Çubuğu
st.sidebar.header("⚙️ Genel Ayarlar")
selected_exchange = st.sidebar.selectbox("Borsa", ["binance", "kucoin", "gate", "bybit", "okx"], index=0)
market_service = MarketDataService(exchange_id=selected_exchange)

# Sekmeler
tab_view, tab_storage = st.tabs(["📈 Canlı & Yerel OHLCV İnceleme", "💾 Veritabanı Arşivi & Durum"])

# ==========================================
# SEKME 1: OHLCV İNCELEME & TOPLAMA
# ==========================================
with tab_view:
    st.markdown("### 🔍 Çoklu Zaman Dilimli OHLCV Veri Toplama")

    c1, c2, c3, c4 = st.columns([3, 2, 2, 2])
    with c1:
        coin_input = st.text_input("🪙 Coin Sembolü", value="BTC", placeholder="Örn: BTC, ETH, SOL, PEPE, SUI...", key="view_coin_input")
    with c2:
        tf_select = st.selectbox("Zaman Dilimi", SUPPORTED_TIMEFRAMES, index=4, key="view_tf_select") # varsayılan 4h
    with c3:
        candle_limit = st.slider("Mum Sayısı", min_value=50, max_value=1500, value=200, step=50, key="view_limit")
    with c4:
        st.write("")
        st.write("")
        fetch_btn = st.button("📥 Veriyi Çek & Kaydet", type="primary", key="btn_fetch_single")

    symbol = ExchangeService.normalize_symbol(coin_input)

    # Çoklu Zaman Dilimi İndirme Butonu
    st.markdown("---")
    multi_c1, multi_c2 = st.columns([4, 2])
    with multi_c1:
        st.write("💡 **Tek Tıkla Tüm Zaman Dilimlerini (1m, 5m, 15m, 1h, 4h, 1D) İndir ve Veritabanına Arşivle:**")
    with multi_c2:
        if st.button("🚀 Tüm Zaman Dilimlerini Arşivle (500 Mum)", key="btn_fetch_all_tf"):
            with st.spinner(f"⏳ {symbol} için tüm zaman dilimleri toplanıyor ve veritabanına kaydediliyor..."):
                res = market_service.collect_all_timeframes(symbol, candles_per_tf=500)
                st.success(f"✅ {symbol} için tüm zaman dilimleri arşivlendi: {res}")

    # Veriyi Çek ve Görüntüle
    df_data = pd.DataFrame()
    if fetch_btn or "last_symbol" in st.session_state:
        if fetch_btn:
            with st.spinner(f"⏳ {symbol} [{tf_select}] verileri çekiliyor ve SQLite veritabanına yazılıyor..."):
                df_data = market_service.fetch_and_store(symbol, timeframe=tf_select, limit=candle_limit)
                st.session_state["last_symbol"] = symbol
                st.session_state["last_tf"] = tf_select
                st.session_state["df_data"] = df_data
        else:
            df_data = st.session_state.get("df_data", pd.DataFrame())

    # Eğer oturumda veri varsa grafiği ve tabloyu çiz
    if not df_data.empty:
        st.markdown(f"#### 📊 **{symbol}** [{tf_select.upper()}] OHLCV Fiyat & Hacim Grafiği")

        # Üst Metrikler
        last_row = df_data.iloc[-1]
        prev_row = df_data.iloc[-2] if len(df_data) > 1 else last_row
        pct_change = ((last_row['close'] - prev_row['close']) / prev_row['close']) * 100.0

        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.metric("Kapanış (Close)", f"{last_row['close']} USDT", delta=f"%{pct_change:+.2f}")
        with m2:
            st.metric("Açılış (Open)", f"{last_row['open']} USDT")
        with m3:
            st.metric("En Yüksek (High)", f"{last_row['high']} USDT")
        with m4:
            st.metric("En Düşük (Low)", f"{last_row['low']} USDT")
        with m5:
            st.metric("Hacim (Volume)", f"{last_row['volume']:,.2f}")

        # Plotly Candlestick + Hacim Alt Grafiği
        fig = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f"{symbol} Mum Grafiği", "İşlem Hacmi (Volume)"),
            row_heights=[0.75, 0.25]
        )

        fig.add_trace(go.Candlestick(
            x=df_data['timestamp'],
            open=df_data['open'],
            high=df_data['high'],
            low=df_data['low'],
            close=df_data['close'],
            name='OHLC',
            increasing_line_color='#00e676',
            decreasing_line_color='#ff5252'
        ), row=1, col=1)

        vol_colors = ['#00e676' if row['close'] >= row['open'] else '#ff5252' for _, row in df_data.iterrows()]
        fig.add_trace(go.Bar(
            x=df_data['timestamp'],
            y=df_data['volume'],
            name='Volume',
            marker_color=vol_colors,
            showlegend=False
        ), row=2, col=1)

        fig.update_layout(
            template="plotly_dark",
            height=600,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="x unified"
        )

        st.plotly_chart(fig, use_container_width=True)

        # Veri Tablosu
        with st.expander("📄 Ham OHLCV Veri Tablosu (Son 50 Mum)", expanded=False):
            st.dataframe(df_data.tail(50), use_container_width=True, hide_index=True)
            csv_bytes = df_data.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Bu Veriyi CSV Olarak İndir",
                data=csv_bytes,
                file_name=f"{symbol.replace('/', '_')}_{tf_select}_ohlcv.csv",
                mime="text/csv"
            )
    else:
        st.info("👈 Coini ve zaman dilimini seçip **'Veriyi Çek & Kaydet'** butonuna tıklayarak veriyi toplayabilirsiniz.")


# ==========================================
# SEKME 2: VERİTABANI ARŞİVİ & DURUM
# ==========================================
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
        st.info("ℹ️ Veritabanında henüz kayıtlı OHLCV verisi bulunmuyor. Birinci sekmeden veya komut satırından veri toplayabilirsiniz.")
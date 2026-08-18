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
from services.microstructure_service import MicrostructureService
from core.structure import PriceStructureAnalyzer
from database.connection import init_db

init_db()

st.set_page_config(
    page_title="Kripto Analiz & Mikro Yapı Platformu",
    page_icon="🌊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel Stil
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

st.title("⚡ Kripto Analiz & Piyasa Mikro Yapı Platformu")
st.caption("Piyasa Mikro Yapısı (Order Book, OBI, CVD, Slippage), Fiyat Yapısı (HH/HL/LH/LL, Trend) ve 8 Temel Sayısal İndikatör Katmanı.")

# Kenar Çubuğu
st.sidebar.header("⚙️ Genel Ayarlar")
selected_exchange = st.sidebar.selectbox("Borsa Seçimi", ["binance", "kucoin", "gate", "bybit", "okx"], index=0)

market_service = MarketDataService(exchange_id=selected_exchange)
indicator_service = IndicatorService(exchange_id=selected_exchange)
micro_service = MicrostructureService(exchange_id=selected_exchange)

# Sekmeler
tab_micro, tab_structure, tab_indicators, tab_ohlcv, tab_storage = st.tabs([
    "🌊 Order Book & Piyasa Mikro Yapısı",
    "🏛️ Fiyat Yapısı & Trend Durumu",
    "📊 8 Temel İndikatör (Sayısal)",
    "📦 OHLCV Veri Toplama",
    "💾 Veritabanı Arşivi"
])


# ==========================================================
# SEKME 1: ORDER BOOK & MİKRO YAPI (4. AŞAMA)
# ==========================================================
with tab_micro:
    st.markdown("### 🌊 Order Book Imbalance (OBI) & Piyasa Mikro Yapısı")
    st.caption("Anlık tahta dengesizliği (OBI), Taker alış/satış baskısı, Kümülatif Hacim Deltası (CVD) ve Slippage simülasyonu.")

    mc1, mc2, mc3 = st.columns([4, 2, 2])
    with mc1:
        micro_coin_raw = st.text_input("🪙 Coin Ara / Gir", value="BTC", placeholder="Örn: BTC, ETH, SOL, PEPE, SUI...", key="micro_coin_input")
    with mc2:
        depth_levels = st.selectbox("Tahta Derinliği", [50, 100, 200, 500], index=1, key="micro_depth_levels")
    with mc3:
        st.write("")
        st.write("")
        micro_btn = st.button("🌊 Mikro Yapıyı Analiz Et", type="primary", key="btn_calc_micro")

    micro_symbol = ExchangeService.normalize_symbol(micro_coin_raw)

    if micro_btn or "last_micro_res" in st.session_state:
        if micro_btn:
            with st.spinner(f"⏳ {micro_symbol} için anlık Order Book ve Trade akışı analiz ediliyor..."):
                res_micro = micro_service.analyze_microstructure(symbol=micro_symbol, depth_limit=depth_levels, trades_limit=100)
                st.session_state["last_micro_res"] = res_micro
        else:
            res_micro = st.session_state.get("last_micro_res")

        if res_micro and res_micro.mid_price > 0:
            st.markdown("---")

            # 1. BÜYÜK BASKI BANNERI
            box_cls = "statement-box-up" if "ALIŞ" in res_micro.pressure_verdict else ("statement-box-down" if "SATIŞ" in res_micro.pressure_verdict else "statement-box-range")
            st.markdown(f"""
            <div class="{box_cls}">
                <div style="font-size:22px; font-weight:bold; margin-bottom:6px;">
                    {res_micro.pressure_badge}
                </div>
                <div style="font-size:16px; color:#eceff1;">
                    📢 {res_micro.statement}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 2. ÜST METRİKLER (Mid Price, Spread, OBI, CVD)
            u1, u2, u3, u4, u5 = st.columns(5)
            with u1:
                st.metric("Mid Price", f"{res_micro.mid_price:,.2f} USDT")
            with u2:
                st.metric("Bid / Ask Spread", f"{res_micro.spread:,.4f} USDT", delta=f"{res_micro.spread_bps:.1f} bps", delta_color="inverse")
            with u3:
                st.metric("Order Book Imbalance (OBI)", f"%{res_micro.obi_pct:+.2f}", delta="Alıcı Baskın" if res_micro.obi > 0 else "Satıcı Baskın")
            with u4:
                st.metric("Trade Imbalance", f"%{res_micro.trade_imbalance * 100:+.2f}")
            with u5:
                st.metric("CVD (Kümülatif Delta)", f"{res_micro.cvd_current:+.4f}", delta="Net Alım" if res_micro.cvd_current > 0 else "Net Satım")

            # 3. LİKİDİTE DERİNLİĞİ KARTLARI (0.5%, 1.0%, 2.0%)
            st.markdown("#### 🧱 Likidite Derinliği Tamponları (Depth Buffers)")
            d1, d2, d3 = st.columns(3)
            with d1:
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-title">±%0.5 Likidite Tamponu</div>
                    <div style="color:#00e676; font-size:16px; font-weight:bold;">Alış: {res_micro.depth_buffers.depth_05_pct_bid:,.0f} $</div>
                    <div style="color:#ff5252; font-size:16px; font-weight:bold;">Satış: {res_micro.depth_buffers.depth_05_pct_ask:,.0f} $</div>
                    <div class="metric-title" style="margin-top:6px;">Bid / Ask Oranı: {res_micro.depth_buffers.ratio_05_pct:.2f}x</div>
                </div>
                """, unsafe_allow_html=True)
            with d2:
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-title">±%1.0 Likidite Tamponu</div>
                    <div style="color:#00e676; font-size:16px; font-weight:bold;">Alış: {res_micro.depth_buffers.depth_10_pct_bid:,.0f} $</div>
                    <div style="color:#ff5252; font-size:16px; font-weight:bold;">Satış: {res_micro.depth_buffers.depth_10_pct_ask:,.0f} $</div>
                    <div class="metric-title" style="margin-top:6px;">Bid / Ask Oranı: {res_micro.depth_buffers.ratio_10_pct:.2f}x</div>
                </div>
                """, unsafe_allow_html=True)
            with d3:
                st.markdown(f"""
                <div class="metric-container">
                    <div class="metric-title">Toplam Tahta Hacmi (100 Kademe)</div>
                    <div style="color:#00e676; font-size:16px; font-weight:bold;">Alış: {res_micro.bid_usd_total:,.0f} $ ({res_micro.bid_vol_total:,.2f})</div>
                    <div style="color:#ff5252; font-size:16px; font-weight:bold;">Satış: {res_micro.ask_usd_total:,.0f} $ ({res_micro.ask_vol_total:,.2f})</div>
                    <div class="metric-title" style="margin-top:6px;">VWAP: {res_micro.vwap:,.2f} USDT</div>
                </div>
                """, unsafe_allow_html=True)

            # 4. ORDER BOOK DERİNLİK GRAFİĞİ & CVD GRAFİĞİ
            g1, g2 = st.columns([1, 1])
            with g1:
                st.markdown("##### 📊 Görsel Emir Defteri Derinlik Eğrisi (Depth Chart)")
                if not res_micro.bids_df.empty and not res_micro.asks_df.empty:
                    fig_depth = go.Figure()
                    fig_depth.add_trace(go.Scatter(
                        x=res_micro.bids_df['price'],
                        y=res_micro.bids_df['cum_usd'],
                        fill='tozeroy',
                        name='Alış Derinliği (Bids)',
                        line=dict(color='#00e676', width=2),
                        fillcolor='rgba(0, 230, 118, 0.15)'
                    ))
                    fig_depth.add_trace(go.Scatter(
                        x=res_micro.asks_df['price'],
                        y=res_micro.asks_df['cum_usd'],
                        fill='tozeroy',
                        name='Satış Derinliği (Asks)',
                        line=dict(color='#ff5252', width=2),
                        fillcolor='rgba(255, 82, 82, 0.15)'
                    ))
                    fig_depth.update_layout(
                        template="plotly_dark",
                        height=360,
                        margin=dict(l=10, r=10, t=20, b=10),
                        xaxis_title="Fiyat (USDT)",
                        yaxis_title="Kümülatif Derinlik ($)",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_depth, use_container_width=True)

            with g2:
                st.markdown("##### ⚡ Cumulative Volume Delta (CVD) Akışı")
                if not res_micro.cvd_series.empty:
                    fig_cvd = go.Figure()
                    cvd_color = '#00e676' if res_micro.cvd_current >= 0 else '#ff5252'
                    fig_cvd.add_trace(go.Scatter(
                        x=res_micro.cvd_series['timestamp'],
                        y=res_micro.cvd_series['cvd'],
                        mode='lines',
                        name='CVD',
                        line=dict(color=cvd_color, width=2)
                    ))
                    fig_cvd.update_layout(
                        template="plotly_dark",
                        height=360,
                        margin=dict(l=10, r=10, t=20, b=10),
                        xaxis_title="Zaman",
                        yaxis_title="Kümülatif Delta Hacmi",
                        hovermode="x unified"
                    )
                    st.plotly_chart(fig_cvd, use_container_width=True)

            # 5. SLIPPAGE & MARKET IMPACT SİMÜLASYONU
            st.markdown("#### 🎯 Slippage (Fiyat Kayması) & Piyasa Etkisi Simülasyonu")
            st.caption("Farklı dolar boyutundaki anlık piyasa emirlerinin (Market Orders) emir defterini ne kadar kaydıracağının simülasyonu.")
            
            slip_data = [{
                'Emir Büyüklüğü': f"${q.order_size_usd:,.0f}",
                'İşlem Yönü': q.side,
                'Ort. Gerçekleşme Fiyatı': f"{q.avg_exec_price:,.2f} USDT",
                'Fiyat Kayması (%)': f"%{q.slippage_pct:.3f}",
                'Fiyat Farkı ($)': f"${q.slippage_usd:,.2f}",
                'Piyasa Etkisi': q.impact_level
            } for q in res_micro.slippage_matrix]
            
            st.dataframe(pd.DataFrame(slip_data), use_container_width=True, hide_index=True)

    else:
        st.info("👈 Coini seçip **'Mikro Yapıyı Analiz Et'** butonuna tıklayarak anlık Order Book, OBI, CVD ve Slippage verilerini inceleyebilirsiniz.")


# ==========================================================
# SEKME 2: FİYAT YAPISI & TREND TESPİTİ (3. AŞAMA)
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

        if struct_res.is_breakout:
            st.success(f"### {struct_res.breakout_details}")
        if struct_res.is_breakdown:
            st.error(f"### {struct_res.breakout_details}")

        fig_struct = make_subplots(
            rows=2, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            subplot_titles=(f"{struct_symbol} Fiyat Yapısı (HH, HL, LH, LL ve Destek/Direnç Çizgileri)", "İşlem Hacmi (Volume)"),
            row_heights=[0.75, 0.25]
        )

        fig_struct.add_trace(go.Candlestick(
            x=df_struct['timestamp'],
            open=df_struct['open'], high=df_struct['high'], low=df_struct['low'], close=df_struct['close'],
            name='Mumlar', increasing_line_color='#00e676', decreasing_line_color='#ff5252'
        ), row=1, col=1)

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


# ==========================================================
# SEKME 3: 8 TEMEL İNDİKATÖR SAYISAL PANELİ (2. AŞAMA)
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
            </div>
            """, unsafe_allow_html=True)

        with r1_c4:
            st.markdown("#### 4. MACD (12, 26, 9)")
            st.markdown(f"""
            <div class="metric-container">
                <div class="metric-title">MACD / Sinyal</div>
                <div class="metric-val">{latest.get('MACD', 0):.4f} / {latest.get('MACD_Signal', 0):.4f}</div>
                <div class="metric-title" style="margin-top:6px;">Histogram</div>
                <div class="metric-val">{latest.get('MACD_Hist', 0):.4f}</div>
            </div>
            """, unsafe_allow_html=True)


# ==========================================================
# SEKME 4: OHLCV VERİ TOPLAMA
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
# SEKME 5: VERİTABANI ARŞİVİ & DURUM
# ==========================================================
with tab_storage:
    st.markdown("### 💾 SQLite Veritabanı Saklama Özeti")
    df_summary = market_service.get_summary()

    if not df_summary.empty:
        st.dataframe(df_summary, use_container_width=True, hide_index=True)
    else:
        st.info("ℹ️ Veritabanında henüz kayıtlı OHLCV verisi bulunmuyor.")
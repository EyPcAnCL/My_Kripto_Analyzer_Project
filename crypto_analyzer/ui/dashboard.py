import sys
from pathlib import Path

# Proje ana dizinini Python yoluna ekle
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from services.exchange_service import ExchangeService
from core.indicators import TechnicalIndicators
from core.scorer import AnalysisScorer
from core.backtester import Backtester, BacktestConfig, BacktestResult
from database.connection import (
    init_db, get_watchlist, get_watchlist_details,
    add_to_watchlist, remove_from_watchlist, clear_watchlist, is_in_watchlist
)

# Veritabanını Başlat
init_db()

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Kripto Analiz, Takip & Backtesting Platformu",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Özel CSS Stilleri
st.markdown("""
<style>
    .metric-card {
        background-color: #1e222d;
        border: 1px solid #2a2e39;
        border-radius: 8px;
        padding: 14px;
        text-align: center;
    }
    .metric-value-green {
        color: #00c853;
        font-size: 22px;
        font-weight: bold;
    }
    .metric-value-red {
        color: #ff5252;
        font-size: 22px;
        font-weight: bold;
    }
    .metric-label {
        color: #90a4ae;
        font-size: 13px;
        margin-bottom: 4px;
    }
    .stButton>button {
        border-radius: 6px;
    }
</style>
""", unsafe_allow_html=True)

# Başlık ve Açıklama
st.title("⚡ Kripto Teknik Analiz, Takip & Backtesting Platformu")
st.caption("İstediğiniz tüm coinleri anlık arayın, kişisel takip listenize kaydedin, profesyonel grafiklerle inceleyin ve stratejilerinizi test edin.")

# Kenar Çubuğu (Global Ayarlar)
st.sidebar.header("⚙️ Borsa Seçimi")
selected_exchange = st.sidebar.selectbox("Aktif Borsa", ["binance", "kucoin", "gate", "bybit", "okx"], index=0)

# Sekmeler (Tabs)
tab_watchlist, tab_scanner, tab_backtest = st.tabs([
    "⭐ Takip Listem & Canlı Coin İnceleme",
    "🔍 Çoklu Piyasa Taraması",
    "🧪 Backtesting & Strateji Simülatörü"
])


# ==========================================================
# SEKME 1: TAKİP LİSTEM & CANLI COİN İNCELEME (ARAMA MOTORLU)
# ==========================================================
with tab_watchlist:
    st.markdown("### 🔎 İstediğiniz Coini Arayın & Takip Listenizi Yönetin")
    st.caption("Arama çubuğuna istediğiniz herhangi bir coini yazın (Örn: PEPE, SUI, DOGE, SOL, AVAX, NEAR). Anlık verisini çekip inceleyebilir ve tek tıkla takip listenize kaydedebilirsiniz.")

    # 1. Canlı Arama ve İnceleme Çubuğu
    search_col1, search_col2, search_col3, search_col4 = st.columns([3, 2, 2, 2])
    with search_col1:
        search_query = st.text_input("🪙 Coin Ara / Gir", value="BTC", placeholder="Örn: PEPE, SUI, AVAX, DOGE, SOL...", key="main_coin_search")
    with search_col2:
        inspect_tf = st.selectbox("Zaman Dilimi", ["15m", "1h", "4h", "1d"], index=2, key="wl_inspect_tf")
    with search_col3:
        inspect_limit = st.slider("Grafik Mum Sayısı", min_value=50, max_value=500, value=200, step=50, key="wl_inspect_limit")
    with search_col4:
        st.write("")
        st.write("")
        search_btn = st.button("🔍 Coini Çek ve İncele", type="primary", key="btn_search_coin")

    # Sembolü normalize et (Örn: pepe -> PEPE/USDT)
    current_symbol = ExchangeService.normalize_symbol(search_query) if search_query else "BTC/USDT"

    # Kayıtlı Takip Listesi Kontrolü
    in_wl = is_in_watchlist(current_symbol)

    st.markdown("---")

    # Coinin Canlı Verisini Çek
    exchange = None
    df_coin = pd.DataFrame()
    try:
        exchange = ExchangeService(exchange_id=selected_exchange)
        df_coin = exchange.fetch_ohlcv(current_symbol, timeframe=inspect_tf, limit=inspect_limit)
    except Exception as e:
        st.error(f"Borsa bağlantı hatası: {e}")

    if df_coin.empty or len(df_coin) < 50:
        st.warning(f"⚠️ **{current_symbol}** için borsadan veri çekilemedi. Lütfen parite adını kontrol edin (Örn: PEPE, SUI, BTC, DOGE).")
    else:
        # İndikatörleri ve Destek/Direnç Seviyelerini Hesapla
        df_coin = TechnicalIndicators.add_all_indicators(df_coin)
        sr_levels = TechnicalIndicators.calculate_support_resistance(df_coin)
        scorer = AnalysisScorer()
        last_row = df_coin.iloc[-1]
        prev_row = df_coin.iloc[-2]
        eval_res = scorer.evaluate(current_symbol, last_row['close'], last_row)

        price_change = ((last_row['close'] - prev_row['close']) / prev_row['close']) * 100.0

        # Başlık & Takip Listesi Butonları
        head_col1, head_col2 = st.columns([3, 2])
        with head_col1:
            st.subheader(f"📊 **{current_symbol}** - Canlı Teknik Rapor ({inspect_tf.upper()})")
        with head_col2:
            wl_action_c1, wl_action_c2 = st.columns([1, 1])
            with wl_action_c1:
                if in_wl:
                    if st.button("🗑️ Listemden Çıkar", key="btn_remove_from_wl"):
                        remove_from_watchlist(current_symbol)
                        st.success(f"{current_symbol} takip listenizden çıkarıldı.")
                        st.rerun()
                else:
                    if st.button("⭐ Takip Listeme Kaydet", type="primary", key="btn_add_to_wl"):
                        add_to_watchlist(current_symbol, notes="Kullanıcı takibi")
                        st.success(f"✅ {current_symbol} takip listenize başarıyla kaydedildi!")
                        st.rerun()
            with wl_action_c2:
                if in_wl:
                    st.info("✅ Listenizde Kayıtlı")

        # Üst Metrik Kartları
        top_m1, top_m2, top_m3, top_m4, top_m5 = st.columns(5)
        with top_m1:
            st.metric("Son Fiyat", f"{last_row['close']} USDT", delta=f"%{price_change:+.2f}")
        with top_m2:
            st.metric("Teknik Sağlık Skoru", f"{eval_res['score']}/100")
        with top_m3:
            st.metric("RSI (14)", f"{eval_res['rsi']}")
        with top_m4:
            st.metric("Stochastic RSI (K)", f"{last_row.get('Stoch_K', 0):.1f}")
        with top_m5:
            st.metric("Sinyal Kararı", eval_res['verdict'])

        # Gelişmiş Plotly Grafiği (Fiyat + Hacim + RSI Subplotları)
        fig_coin = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.04,
            subplot_titles=(f"{current_symbol} Fiyat & Hareketli Ortalamalar (EMA 50/200, Bollinger)", "İşlem Hacmi (Volume)", "RSI Momentum (14)"),
            row_heights=[0.60, 0.20, 0.20]
        )

        # 1. Mum Grafiği
        fig_coin.add_trace(go.Candlestick(
            x=df_coin['timestamp'],
            open=df_coin['open'],
            high=df_coin['high'],
            low=df_coin['low'],
            close=df_coin['close'],
            name='Mumlar',
            increasing_line_color='#00e676',
            decreasing_line_color='#ff5252'
        ), row=1, col=1)

        # EMA 50 & 200
        fig_coin.add_trace(go.Scatter(
            x=df_coin['timestamp'], y=df_coin['EMA_50'],
            mode='lines', name='EMA 50', line=dict(color='#ff9800', width=1.5)
        ), row=1, col=1)

        fig_coin.add_trace(go.Scatter(
            x=df_coin['timestamp'], y=df_coin['EMA_200'],
            mode='lines', name='EMA 200', line=dict(color='#29b6f6', width=2)
        ), row=1, col=1)

        # Bollinger Bantları
        fig_coin.add_trace(go.Scatter(
            x=df_coin['timestamp'], y=df_coin['BB_High'],
            mode='lines', name='BB Üst', line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dot')
        ), row=1, col=1)

        fig_coin.add_trace(go.Scatter(
            x=df_coin['timestamp'], y=df_coin['BB_Low'],
            mode='lines', name='BB Alt', line=dict(color='rgba(255, 255, 255, 0.3)', width=1, dash='dot'),
            fill='tonexty', fillcolor='rgba(255, 255, 255, 0.03)'
        ), row=1, col=1)

        # 2. Hacim Çubukları
        colors = ['#00e676' if row['close'] >= row['open'] else '#ff5252' for _, row in df_coin.iterrows()]
        fig_coin.add_trace(go.Bar(
            x=df_coin['timestamp'], y=df_coin['volume'],
            name='Hacim', marker_color=colors, showlegend=False
        ), row=2, col=1)

        if 'Vol_SMA_20' in df_coin.columns:
            fig_coin.add_trace(go.Scatter(
                x=df_coin['timestamp'], y=df_coin['Vol_SMA_20'],
                mode='lines', name='Hacim Ort. (20)', line=dict(color='#ffeb3b', width=1.2)
            ), row=2, col=1)

        # 3. RSI Grafiği
        fig_coin.add_trace(go.Scatter(
            x=df_coin['timestamp'], y=df_coin['RSI'],
            mode='lines', name='RSI (14)', line=dict(color='#ab47bc', width=2)
        ), row=3, col=1)

        fig_coin.add_hline(y=70, line_dash="dash", line_color="red", row=3, col=1)
        fig_coin.add_hline(y=30, line_dash="dash", line_color="green", row=3, col=1)

        fig_coin.update_layout(
            template="plotly_dark",
            height=750,
            xaxis_rangeslider_visible=False,
            margin=dict(l=20, r=20, t=40, b=20),
            hovermode="x unified"
        )

        st.plotly_chart(fig_coin, use_container_width=True)

        # Destek, Direnç & Analiz Notları
        col_inf1, col_inf2 = st.columns([1, 1])
        with col_inf1:
            st.markdown("##### 🧱 Dinamik Destek & Direnç Seviyeleri")
            if sr_levels:
                sr_df = pd.DataFrame([
                    {"Seviye": "🔴 Ana Direnç (Swing High)", "Fiyat": f"{sr_levels['resistance_major']} USDT"},
                    {"Seviye": "Fibonacci 0.236", "Fiyat": f"{sr_levels['fib_236']} USDT"},
                    {"Seviye": "Fibonacci 0.382", "Fiyat": f"{sr_levels['fib_382']} USDT"},
                    {"Seviye": "Fibonacci 0.500 (Denge)", "Fiyat": f"{sr_levels['fib_500']} USDT"},
                    {"Seviye": "Fibonacci 0.618 (Altın Oran)", "Fiyat": f"{sr_levels['fib_618']} USDT"},
                    {"Seviye": "🟢 Ana Destek (Swing Low)", "Fiyat": f"{sr_levels['support_major']} USDT"}
                ])
                st.dataframe(sr_df, use_container_width=True, hide_index=True)

        with col_inf2:
            st.markdown("##### 📝 Teknik Sinyal Notları & Durum")
            for note in eval_res['notes']:
                st.markdown(f"- {note}")
            
            st.markdown("---")
            if last_row['close'] > last_row['EMA_50'] > last_row['EMA_200']:
                st.success("🟢 **Genel Trend:** Güçlü Yükseliş Trendi (Boğa)")
            elif last_row['close'] < last_row['EMA_50'] < last_row['EMA_200']:
                st.error("🔴 **Genel Trend:** Düşüş Trendi (Ayı)")
            else:
                st.warning("🟡 **Genel Trend:** Yatay / Konsolidasyon")

    # ==========================================
    # KAYITLI TAKİP LİSTEM (VERİTABANI KARTLARI)
    # ==========================================
    st.markdown("---")
    st.markdown("### 📋 Kayıtlı Takip Listeniz")
    
    saved_watchlist_details = get_watchlist_details()

    if not saved_watchlist_details:
        st.info("ℹ️ Henüz takip listenize kayıtlı coin bulunmuyor. Yukarıdaki arama kutusuna istediğiniz coini (Örn: PEPE, SUI, DOGE) yazıp **'⭐ Takip Listeme Kaydet'** butonuna basarak listenizi oluşturabilirsiniz.")
    else:
        # Hızlı seçim butonları
        st.markdown("**Hızlı İncelemek İçin Coine Tıklayın:**")
        pill_cols = st.columns(min(len(saved_watchlist_details), 8))
        for idx, coin_item in enumerate(saved_watchlist_details):
            col_idx = idx % min(len(saved_watchlist_details), 8)
            with pill_cols[col_idx]:
                if st.button(f"📌 {coin_item['symbol']}", key=f"quick_pill_{coin_item['symbol']}"):
                    st.session_state["main_coin_search"] = coin_item['symbol']
                    st.rerun()

        # Kayıtlı Coinler Tablosu ve Silme
        wl_table_df = pd.DataFrame(saved_watchlist_details)
        st.dataframe(wl_table_df[['symbol', 'added_at', 'notes']], use_container_width=True, hide_index=True)

        col_wl_del1, col_wl_del2 = st.columns([3, 1])
        with col_wl_del1:
            coin_to_remove = st.selectbox("Listeden Silinecek Coini Seçin", [c['symbol'] for c in saved_watchlist_details], key="sel_coin_to_remove")
        with col_wl_del2:
            st.write("")
            st.write("")
            if st.button("🗑️ Seçili Coini Sil", key="btn_del_single_coin"):
                remove_from_watchlist(coin_to_remove)
                st.success(f"{coin_to_remove} silindi.")
                st.rerun()


# ==========================================
# SEKME 2: ÇOKLU PİYASA TARAMASI
# ==========================================
with tab_scanner:
    st.markdown("### 📊 Özel Liste ile Çoklu Piyasa Taraması")
    st.caption("Takip listenizdeki tüm coinleri veya virgülle ayırarak girdiğiniz özel coin listesini tek tıkla tarayın.")

    # Kayıtlı coinleri al
    saved_symbols = get_watchlist()
    default_scan_text = ", ".join(saved_symbols) if saved_symbols else "BTC, ETH, SOL, PEPE, SUI"

    col_s1, col_s2, col_s3 = st.columns([2, 2, 2])
    with col_s1:
        scan_timeframe = st.selectbox("Zaman Dilimi", ["15m", "1h", "4h", "1d"], index=2, key="scan_tf")
    with col_s2:
        scan_candle_limit = st.slider("İncelenecek Mum Sayısı", min_value=50, max_value=500, value=150, step=50, key="scan_limit")
    with col_s3:
        min_score_filter = st.slider("Minimum Skor Filtresi", min_value=0, max_value=90, value=0, step=5, key="scan_min_score")

    scan_coin_input = st.text_area(
        "Taranacak Coinler (Virgülle ayırarak istediğiniz kadar yazabilirsiniz)",
        value=default_scan_text,
        placeholder="Örn: BTC, ETH, SOL, AVAX, PEPE, SUI, DOGE, NEAR, RENDER",
        key="scan_input_coins"
    )

    scan_list = [ExchangeService.normalize_symbol(c) for c in scan_coin_input.split(",") if c.strip()]

    start_scan = st.button("🚀 Listeyi Şimdi Tara", type="primary", key="start_scan_btn")

    if start_scan or "scan_results" in st.session_state:
        if start_scan:
            try:
                exchange = ExchangeService(exchange_id=selected_exchange)
                scorer = AnalysisScorer()
            except Exception as e:
                st.error(f"Borsa bağlantısı kurulamadı: {e}")
                st.stop()

            scan_results = []
            progress_bar = st.progress(0)
            status_text = st.empty()

            for i, symbol in enumerate(scan_list):
                status_text.text(f"⏳ {symbol} verileri çekiliyor ve analiz ediliyor...")
                df = exchange.fetch_ohlcv(symbol, timeframe=scan_timeframe, limit=scan_candle_limit)
                
                if not df.empty and len(df) >= 50:
                    df = TechnicalIndicators.add_all_indicators(df)
                    last_row = df.iloc[-1]
                    current_price = last_row['close']
                    result = scorer.evaluate(symbol, current_price, last_row)
                    
                    result['ema_50'] = round(last_row.get('EMA_50', 0), 2)
                    result['ema_200'] = round(last_row.get('EMA_200', 0), 2)
                    result['bb_high'] = round(last_row.get('BB_High', 0), 2)
                    result['bb_low'] = round(last_row.get('BB_Low', 0), 2)
                    result['macd'] = round(last_row.get('MACD', 0), 4)
                    result['macd_signal'] = round(last_row.get('MACD_Signal', 0), 4)
                    
                    scan_results.append(result)

                progress_bar.progress((i + 1) / len(scan_list))

            progress_bar.empty()
            status_text.empty()
            st.session_state["scan_results"] = scan_results
        else:
            scan_results = st.session_state["scan_results"]

        filtered_results = [r for r in scan_results if r['score'] >= min_score_filter]
        filtered_results.sort(key=lambda x: x['score'], reverse=True)

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        with kpi1:
            st.metric("Taranan Coin Sayısı", len(scan_results))
        with kpi2:
            strong_buys = len([r for r in scan_results if "GÜÇLÜ" in r['verdict']])
            st.metric("Güçlü Al Sinyalleri", strong_buys, delta=f"{strong_buys} Fırsat" if strong_buys > 0 else None)
        with kpi3:
            buys = len([r for r in scan_results if "KADEMELİ" in r['verdict']])
            st.metric("Kademeli Al Sinyalleri", buys)
        with kpi4:
            avg_score = round(np.mean([r['score'] for r in scan_results]), 1) if scan_results else 0
            st.metric("Ortalama Piyasa Skoru", f"{avg_score}/100")

        st.markdown("---")

        for res in filtered_results:
            with st.container():
                c1, c2, c3, c4 = st.columns([2.5, 2, 2.5, 5])

                with c1:
                    st.subheader(f"{res['symbol']}")
                    st.markdown(f"**Fiyat:** `{res['price']} USDT`")

                with c2:
                    st.metric(label="Teknik Skor", value=f"{res['score']}/100")

                with c3:
                    st.markdown(f"**RSI (14):** `{res['rsi']}`")
                    if "GÜÇLÜ" in res['verdict']:
                        st.success(f"**{res['verdict']}**")
                    elif "KADEMELİ" in res['verdict']:
                        st.info(f"**{res['verdict']}**")
                    elif "RİSKLİ" in res['verdict']:
                        st.error(f"**{res['verdict']}**")
                    else:
                        st.warning(f"**{res['verdict']}**")

                with c4:
                    st.markdown("**Analiz & Sinyal Notları:**")
                    for note in res['notes']:
                        st.markdown(f"- {note}")

                st.divider()
    else:
        st.info("👈 Taranacak coinleri belirleyip **'Listeyi Şimdi Tara'** butonuna basarak taramayı başlatın.")


# ==========================================
# SEKME 3: BACKTESTING & STRATEJİ SİMÜLATÖRÜ
# ==========================================
with tab_backtest:
    st.markdown("### 🧪 Geçmiş Veri Strateji Simülatörü & Backtesting")
    st.caption("İstediğiniz herhangi bir coinin geçmiş verilerini çekerek teknik alım-satım stratejinizin kârlılığını test edin.")

    # Parametre Giriş Formu
    with st.expander("🛠️ Backtest Parametreleri ve Strateji Ayarları", expanded=True):
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)

        with col_b1:
            bt_symbol_raw = st.text_input("Test Edilecek Parite", value="BTC", placeholder="Örn: PEPE, SUI, DOGE, SOL, BTC...", key="bt_sym_input")
            bt_symbol = ExchangeService.normalize_symbol(bt_symbol_raw)
            bt_timeframe = st.selectbox("Zaman Dilimi (Timeframe)", ["15m", "1h", "4h", "1d"], index=2, key="bt_tf")
            bt_candle_count = st.select_slider("Geçmiş Mum Sayısı", options=[200, 500, 1000, 1500, 2000], value=1000)

        with col_b2:
            bt_capital = st.number_input("Başlangıç Sermayesi ($)", min_value=100.0, max_value=1000000.0, value=1000.0, step=100.0)
            bt_pos_size = st.slider("Pozisyon Büyüklüğü (% Sermaye)", min_value=10.0, max_value=100.0, value=100.0, step=5.0)
            bt_commission = st.number_input("İşlem Komisyonu (% Başına)", min_value=0.0, max_value=1.0, value=0.1, step=0.02)

        with col_b3:
            bt_entry_score = st.slider("Alım (Giriş) Skor Eşiği", min_value=50, max_value=85, value=65, step=5, help="Skor bu değer veya üzerine çıktığında alım yapılır.")
            bt_exit_score = st.slider("Satım (Çıkış) Skor Eşiği", min_value=20, max_value=55, value=40, step=5, help="Skor bu değer veya altına indiğinde pozisyon kapatılır.")

        with col_b4:
            enable_tp_sl = st.checkbox("TP / SL (Kâr Al & Zarar Kes) Kullan", value=True)
            if enable_tp_sl:
                bt_tp = st.slider("Kâr Al - Take Profit (%)", min_value=1.0, max_value=30.0, value=6.0, step=0.5)
                bt_sl = st.slider("Zarar Kes - Stop Loss (%)", min_value=1.0, max_value=20.0, value=3.5, step=0.5)
                bt_trail = st.slider("İz Süren Stop - Trailing (%) [0 = Pasif]", min_value=0.0, max_value=15.0, value=0.0, step=0.5)
            else:
                bt_tp, bt_sl, bt_trail = None, None, None

    bt_run_btn = st.button("🚀 Backtest'i Çalıştır", type="primary", key="run_bt_btn")

    if bt_run_btn or "backtest_result" in st.session_state:
        if bt_run_btn:
            with st.spinner(f"⏳ {bt_symbol} için {bt_candle_count} mumluk veri çekiliyor ve simülasyon koşturuluyor..."):
                try:
                    exchange = ExchangeService(exchange_id=selected_exchange)
                    df_historical = exchange.fetch_historical_ohlcv(bt_symbol, timeframe=bt_timeframe, total_candles=bt_candle_count)

                    if df_historical.empty or len(df_historical) < 50:
                        st.error(f"❌ {bt_symbol} için yeterli geçmiş veri alınamadı. Lütfen pariteyi kontrol edin.")
                        st.stop()

                    cfg = BacktestConfig(
                        initial_capital=bt_capital,
                        position_size_pct=bt_pos_size,
                        commission_pct=bt_commission,
                        entry_score_threshold=bt_entry_score,
                        exit_score_threshold=bt_exit_score,
                        take_profit_pct=bt_tp if enable_tp_sl else None,
                        stop_loss_pct=bt_sl if enable_tp_sl else None,
                        trailing_stop_pct=bt_trail if enable_tp_sl and bt_trail > 0 else None
                    )

                    backtester = Backtester(config=cfg)
                    bt_result = backtester.run(df_historical, symbol=bt_symbol, timeframe=bt_timeframe)
                    st.session_state["backtest_result"] = bt_result
                    st.session_state["df_historical"] = df_historical
                except Exception as e:
                    st.error(f"Backtest sırasında hata meydana geldi: {e}")
                    st.stop()
        else:
            bt_result = st.session_state["backtest_result"]
            df_historical = st.session_state["df_historical"]

        # ==========================================
        # PERFORMANS GÖSTERGE PANELİ (KPIs)
        # ==========================================
        st.markdown(f"#### 📈 **{bt_result.symbol}** Strateji Performans Özeti ({bt_result.timeframe.upper()})")

        kpi_r1_1, kpi_r1_2, kpi_r1_3, kpi_r1_4 = st.columns(4)
        with kpi_r1_1:
            profit_color = "normal" if bt_result.net_profit >= 0 else "inverse"
            st.metric(
                label="Net Kâr / Zarar",
                value=f"{bt_result.net_profit:+.2f} USDT",
                delta=f"%{bt_result.net_profit_pct:+.2f}",
                delta_color=profit_color
            )
        with kpi_r1_2:
            st.metric(
                label="Son Bakiye",
                value=f"{bt_result.final_capital:,.2f} USDT",
                delta=f"Başlangıç: {bt_result.initial_capital:,.0f} $"
            )
        with kpi_r1_3:
            st.metric(
                label="Kazanma Oranı (Win Rate)",
                value=f"%{bt_result.win_rate:.1f}",
                delta=f"{bt_result.winning_trades} Kazanç / {bt_result.total_trades} İşlem"
            )
        with kpi_r1_4:
            st.metric(
                label="Buy & Hold Getirisi (Al-Tut)",
                value=f"%{bt_result.buy_and_hold_pct:+.2f}",
                delta="Kıyaslama"
            )

        kpi_r2_1, kpi_r2_2, kpi_r2_3, kpi_r2_4 = st.columns(4)
        with kpi_r2_1:
            st.metric(label="Profit Factor", value=f"{bt_result.profit_factor:.2f}")
        with kpi_r2_2:
            st.metric(label="Maksimum Düşüş (Max DD)", value=f"%{bt_result.max_drawdown_pct:.2f}", delta=f"-{bt_result.max_drawdown_usd:.2f} $", delta_color="inverse")
        with kpi_r2_3:
            st.metric(label="Sharpe Oranı", value=f"{bt_result.sharpe_ratio:.2f}")
        with kpi_r2_4:
            st.metric(label="Ort. İşlem Getirisi", value=f"%{bt_result.avg_trade_pct:+.2f}", delta=f"R/R: {bt_result.risk_reward_ratio:.2f}")

        st.markdown("---")

        # ==========================================
        # GÖRSEL GRAFİKLER (PLOTLY EQUITY & DRAWDOWN)
        # ==========================================
        eq_df = bt_result.equity_curve
        if not eq_df.empty:
            fig_equity = go.Figure()

            fig_equity.add_trace(go.Scatter(
                x=eq_df['timestamp'],
                y=eq_df['equity'],
                mode='lines',
                name='Strateji Portföyü ($)',
                line=dict(color='#00e676', width=2.5),
                fill='tozeroy',
                fillcolor='rgba(0, 230, 118, 0.08)'
            ))

            fig_equity.add_trace(go.Scatter(
                x=eq_df['timestamp'],
                y=eq_df['buy_and_hold'],
                mode='lines',
                name='Buy & Hold (Al-Tut) ($)',
                line=dict(color='#90a4ae', width=1.5, dash='dash')
            ))

            fig_equity.update_layout(
                title=f"💼 Sermaye Büyüme Eğrisi (Equity Curve) vs Al-Tut Karşılaştırması",
                xaxis_title="Tarih / Zaman",
                yaxis_title="Portföy Değeri (USDT)",
                template="plotly_dark",
                hovermode="x unified",
                legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
                margin=dict(l=20, r=20, t=50, b=20),
                height=450
            )
            st.plotly_chart(fig_equity, use_container_width=True)

            fig_dd = go.Figure()
            fig_dd.add_trace(go.Scatter(
                x=eq_df['timestamp'],
                y=eq_df['drawdown'],
                mode='lines',
                name='Drawdown (%)',
                line=dict(color='#ff5252', width=1.5),
                fill='tozeroy',
                fillcolor='rgba(255, 82, 82, 0.2)'
            ))
            fig_dd.update_layout(
                title="📉 Sualtı Düşüş Eğrisi (Underwater Drawdown %)",
                xaxis_title="Tarih",
                yaxis_title="Düşüş (%)",
                template="plotly_dark",
                margin=dict(l=20, r=20, t=40, b=20),
                height=250
            )
            st.plotly_chart(fig_dd, use_container_width=True)

        # ==========================================
        # İŞLEM GEÇMİŞİ TABLOSU & DÖKÜMÜ
        # ==========================================
        st.markdown("#### 📜 Gerçekleşen İşlem Dökümü (Trade Logs)")
        
        if not bt_result.trades_df.empty:
            st.dataframe(
                bt_result.trades_df,
                use_container_width=True,
                hide_index=True
            )

            csv_data = bt_result.trades_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 İşlem Geçmişini CSV Olarak İndir",
                data=csv_data,
                file_name=f"backtest_{bt_result.symbol.replace('/', '_')}_{bt_result.timeframe}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Seçilen zaman dilimi ve skor eşiklerinde hiçbir alım-satım işlemi gerçekleşmedi.")
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

from config.settings import DEFAULT_WATCHLIST, TIMEFRAME, CANDLE_LIMIT
from services.exchange_service import ExchangeService
from core.indicators import TechnicalIndicators
from core.scorer import AnalysisScorer
from core.backtester import Backtester, BacktestConfig, BacktestResult

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Kripto Analiz & Backtesting Platformu",
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
    .trade-badge-win {
        background-color: rgba(0, 200, 83, 0.15);
        color: #00e676;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
    .trade-badge-loss {
        background-color: rgba(255, 82, 82, 0.15);
        color: #ff5252;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Başlık ve Açıklama
st.title("⚡ Kripto Teknik Analiz & Strateji Simülatörü")
st.caption("Gerçek zamanlı piyasa tarayıcısı, indikatör skorlayıcı ve geçmiş veri backtesting motoru.")

# Kenar Çubuğu (Global Ayarlar)
st.sidebar.header("⚙️ Genel Ayarlar")
selected_exchange = st.sidebar.selectbox("Borsa Seçimi", ["binance", "kucoin", "gate", "bybit", "okx"], index=0)

# Sekmeler (Tabs)
tab_scanner, tab_backtest = st.tabs(["🔍 Canlı Piyasa Taraması", "🧪 Backtesting & Strateji Simülatörü"])

# ==========================================
# SEKME 1: CANLI PİYASA TARAMASI
# ==========================================
with tab_scanner:
    st.markdown("### 📊 Çoklu Coin Teknik Analiz Taraması")
    
    col_s1, col_s2, col_s3 = st.columns([2, 2, 2])
    with col_s1:
        scan_timeframe = st.selectbox("Zaman Dilimi", ["15m", "1h", "4h", "1d"], index=2, key="scan_tf")
    with col_s2:
        scan_candle_limit = st.slider("İncelenecek Mum Sayısı", min_value=50, max_value=500, value=150, step=50, key="scan_limit")
    with col_s3:
        min_score_filter = st.slider("Minimum Skor Filtresi", min_value=0, max_value=90, value=0, step=5, key="scan_min_score")
        
    user_coin_input = st.text_input("Listeye Ek Coin Ekle (Örn: XRP/USDT, AVAX/USDT)", "", key="scan_custom_coin")
    
    watchlist = DEFAULT_WATCHLIST.copy()
    if user_coin_input:
        extra_coins = [c.strip().upper() for c in user_coin_input.split(",") if c.strip()]
        for coin in extra_coins:
            if coin not in watchlist:
                watchlist.append(coin)

    start_scan = st.button("🚀 Piyasayı Şimdi Tara", type="primary", key="start_scan_btn")

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

            for i, symbol in enumerate(watchlist):
                status_text.text(f"⏳ {symbol} verileri çekiliyor ve analiz ediliyor...")
                df = exchange.fetch_ohlcv(symbol, timeframe=scan_timeframe, limit=scan_candle_limit)
                
                if not df.empty and len(df) >= 50:
                    df = TechnicalIndicators.add_all_indicators(df)
                    last_row = df.iloc[-1]
                    current_price = last_row['close']
                    result = scorer.evaluate(symbol, current_price, last_row)
                    
                    # Ek teknik detaylar
                    result['ema_50'] = round(last_row.get('EMA_50', 0), 2)
                    result['ema_200'] = round(last_row.get('EMA_200', 0), 2)
                    result['bb_high'] = round(last_row.get('BB_High', 0), 2)
                    result['bb_low'] = round(last_row.get('BB_Low', 0), 2)
                    result['macd'] = round(last_row.get('MACD', 0), 4)
                    result['macd_signal'] = round(last_row.get('MACD_Signal', 0), 4)
                    
                    scan_results.append(result)

                progress_bar.progress((i + 1) / len(watchlist))

            progress_bar.empty()
            status_text.empty()
            st.session_state["scan_results"] = scan_results
        else:
            scan_results = st.session_state["scan_results"]

        # Filtreleme
        filtered_results = [r for r in scan_results if r['score'] >= min_score_filter]
        filtered_results.sort(key=lambda x: x['score'], reverse=True)

        # Özet KPI'lar
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

        # Sonuç Kartları
        for res in filtered_results:
            with st.container():
                c1, c2, c3, c4 = st.columns([2.5, 2, 2.5, 5])

                with c1:
                    st.subheader(f"{res['symbol']}")
                    st.markdown(f"**Fiyat:** `{res['price']} USDT`")

                with c2:
                    score_color = "green" if res['score'] >= 65 else ("orange" if res['score'] >= 45 else "red")
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
        st.info("👈 Tarama parametrelerini seçip **'Piyasayı Şimdi Tara'** butonuna basarak analizi başlatın.")


# ==========================================
# SEKME 2: BACKTESTING & STRATEJİ SİMÜLATÖRÜ
# ==========================================
with tab_backtest:
    st.markdown("### 🧪 Geçmiş Veri Strateji Simülatörü & Backtesting")
    st.caption("Teknik analiz puanlama motorunun geçmiş dönem performansını, kârlılığını, risk/getiri oranını ve sermaye eğrisini test edin.")

    # Parametre Giriş Formu
    with st.expander("🛠️ Backtest Parametreleri ve Strateji Ayarları", expanded=True):
        col_b1, col_b2, col_b3, col_b4 = st.columns(4)

        with col_b1:
            bt_symbol = st.selectbox("Test Edilecek Parite", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "AVAX/USDT", "BNB/USDT", "DOGE/USDT", "XRP/USDT"], index=0)
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
                        st.error("Yeterli geçmiş veri alınamadı. Lütfen mum sayısını veya pariteyi kontrol edin.")
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
            # 1. Sermaye Büyüme Eğrisi Grafiği
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

            # 2. Düşüş Grafiği (Underwater Drawdown)
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

            # CSV İndirme Butonu
            csv_data = bt_result.trades_df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 İşlem Geçmişini CSV Olarak İndir",
                data=csv_data,
                file_name=f"backtest_{bt_result.symbol.replace('/', '_')}_{bt_result.timeframe}.csv",
                mime="text/csv"
            )
        else:
            st.warning("⚠️ Seçilen zaman dilimi ve skor eşiklerinde hiçbir alım-satım işlemi gerçekleşmedi. Skor eşiklerini esnetmeyi deneyin.")
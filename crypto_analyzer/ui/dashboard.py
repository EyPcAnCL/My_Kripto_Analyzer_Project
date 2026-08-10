import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import streamlit as st
import pandas as pd
from config.settings import DEFAULT_WATCHLIST, TIMEFRAME, CANDLE_LIMIT
from services.exchange_service import ExchangeService
from core.indicators import TechnicalIndicators
from core.scorer import AnalysisScorer

# ... (geri kalan kodlar aynı kalacak)

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Kripto Teknik Analizör",
    page_icon="📈",
    layout="wide"
)

st.title("🚀 Kripto Teknik Analiz Paneli")
st.markdown("Seçtiğiniz coinleri anlık tarar, teknik indikatörleri hesaplar ve detaylı analiz notları sunar.")

# Kenar Çubuğu (Sidebar) Ayarları
st.sidebar.header("⚙️ Kontrol Paneli")
selected_exchange = st.sidebar.selectbox("Borsa Seçimi", ["binance", "kucoin", "gate"], index=0)
selected_timeframe = st.sidebar.selectbox("Zaman Dilimi (Timeframe)", ["1h", "4h", "1d"], index=1)

# Kullanıcının özel coin ekleyebilmesi için alan
user_coin_input = st.sidebar.text_input("Ek Coin Ekle (Örn: XRP/USDT)", "")
watchlist = DEFAULT_WATCHLIST.copy()

if user_coin_input:
    formatted_coin = user_coin_input.upper().strip()
    if formatted_coin not in watchlist:
        watchlist.append(formatted_coin)

st.sidebar.markdown("---")
analyze_button = st.sidebar.button("🔍 Piyasayı Tara ve Analiz Et", type="primary")

# Ana Ekran
if analyze_button or "analyzed" in st.session_state:
    st.session_state["analyzed"] = True
    
    # Servisleri Başlat
    try:
        exchange = ExchangeService(exchange_id=selected_exchange)
        scorer = AnalysisScorer()
    except Exception as e:
        st.error(f"Borsa başlatılamadı: {e}")
        st.stop()

    st.subheader(f"📊 Aktif Tarama Sonuçları ({selected_timeframe.upper()})")
    
    progress_bar = st.progress(0)
    total_coins = len(watchlist)
    
    results = []
    for i, symbol in enumerate(watchlist):
        df = exchange.fetch_ohlcv(symbol, timeframe=selected_timeframe, limit=CANDLE_LIMIT)
        
        if not df.empty:
            df = TechnicalIndicators.add_all_indicators(df)
            last_row = df.iloc[-1]
            current_price = last_row['close']
            
            result = scorer.evaluate(symbol, current_price, last_row)
            results.append(result)
            
        progress_bar.progress((i + 1) / total_coins)
        
    progress_bar.empty()

    # Sonuçları Kartlar Halinde Gösterme
    for res in results:
        with st.container():
            col1, col2, col3, col4 = st.columns([2, 2, 2, 4])
            
            with col1:
                st.markdown(f"### **{res['symbol']}**")
                st.text(f"Fiyat: {res['price']} USDT")
                
            with col2:
                st.metric(label="Sağlık / Alım Skoru", value=f"{res['score']}/100")
                
            with col3:
                st.text(f"RSI: {res['rsi']}")
                if "GÜÇLÜ" in res['verdict']:
                    st.success(res['verdict'])
                elif "KADEMELİ" in res['verdict']:
                    st.info(res['verdict'])
                elif "RİSKLİ" in res['verdict']:
                    st.error(res['verdict'])
                else:
                    st.warning(res['verdict'])
                    
            with col4:
                st.markdown("**Analiz Notları:**")
                for note in res['notes']:
                    st.markdown(f"- {note}")
                    
            st.divider()
else:
    st.info("👈 Sol menüden **Piyasayı Tara ve Analiz Et** butonuna tıklayarak analizi başlatın.")
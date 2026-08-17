import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

import streamlit as st
from services.exchange_service import ExchangeService

st.set_page_config(
    page_title="Kripto Analiz Platformu",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Kripto Analiz Platformu (Yeniden Başlangıç)")
st.info("💡 Tüm teknik analiz modülleri sıfırlandı. Yeni analiz ve strateji mantığını sıfırdan inşa etmeye hazırız.")
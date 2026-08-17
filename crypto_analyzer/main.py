import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def main():
    print("⚡ Kripto Analiz Projesi - Sıfırdan Başlangıç Modu")
    print("Modüller yeni analiz stratejisine göre inşa edilmeye hazırdır.")

if __name__ == "__main__":
    main()
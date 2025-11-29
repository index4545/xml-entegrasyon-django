@echo off
SETLOCAL EnableDelayedExpansion

echo ==========================================
echo XML Entegrasyon Projesi Baslatiliyor...
echo ==========================================

:: 1. Python Kontrolu
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [HATA] Python bulunamadi!
    echo Lutfen Python'u https://www.python.org/downloads/ adresinden indirip kurun.
    echo Kurulum sirasinda "Add Python to PATH" secenegini isaretlemeyi unutmayin.
    pause
    exit /b 1
)

:: 2. Sanal Ortam (venv) Kontrolu ve Kurulumu
if not exist venv (
    echo [BILGI] Sanal ortam (venv) olusturuluyor...
    python -m venv venv
) else (
    echo [BILGI] Sanal ortam mevcut.
)

:: 3. Sanal Ortami Aktiflestir
call .\venv\Scripts\activate

:: 4. Pip Guncelleme (Python 3.14 uyumlulugu icin onemli)
echo [BILGI] Pip ve kurulum araclari guncelleniyor...
python -m pip install --upgrade pip setuptools wheel

:: 5. Gereksinimleri Yukle
echo [BILGI] Kutuphaneler yukleniyor...
:: Pillow ve grpcio icin ozel islem gerekebilir, once onlari deneyelim
python -m pip install --upgrade Pillow grpcio google-generativeai
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [HATA] Kutuphaneler yuklenirken hata olustu.
    pause
    exit /b 1
)

:: 6. Veritabani Migrations
echo [BILGI] Veritabani guncelleniyor...
python manage.py migrate

:: 7. Superuser Olustur
echo [BILGI] Yonetici kullanicisi kontrol ediliyor...
python create_superuser_script.py

:: 8. Uygulamayi Baslat
echo ==========================================
echo Uygulama baslatiliyor...
echo Yonetim Paneli: http://127.0.0.1:8000/admin
echo Kullanici Adi: admin
echo Sifre: admin
echo ==========================================
echo.

:: GUI Baslatici (run_app.py) varsa onu kullan, yoksa manage.py runserver
if exist run_app.py (
    echo [BILGI] GUI Baslatici kullaniliyor...
    python run_app.py
) else (
    echo [BILGI] Standart sunucu baslatiliyor...
    python manage.py runserver
)

pause

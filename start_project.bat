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
if exist venv (
    echo [BILGI] Mevcut sanal ortam kontrol ediliyor...
    .\venv\Scripts\python.exe --version >nul 2>&1
    IF !ERRORLEVEL! NEQ 0 (
        echo [UYARI] Mevcut venv bozuk veya calismiyor. Yeniden olusturuluyor...
        rmdir /s /q venv
        python -m venv venv
    ) else (
        echo [BILGI] Sanal ortam hazir.
    )
) else (
    echo [BILGI] Sanal ortam (venv) olusturuluyor...
    python -m venv venv
)

:: 3. Sanal Ortami Aktiflestir
call .\venv\Scripts\activate

:: 4. Gereksinimleri Yukle
echo [BILGI] Kutuphaneler yukleniyor...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo [HATA] Kutuphaneler yuklenirken hata olustu.
    pause
    exit /b 1
)

:: 5. Veritabani Migrations
echo [BILGI] Veritabani guncelleniyor...
python manage.py migrate

:: 6. Superuser Olustur
echo [BILGI] Yonetici kullanicisi kontrol ediliyor...
python create_superuser_script.py

:: 7. Sunucuyu Baslat
echo ==========================================
echo Uygulama baslatiliyor...
echo Yonetim Paneli: http://127.0.0.1:8000/admin
echo Kullanici Adi: admin
echo Sifre: admin
echo ==========================================
echo Durdurmak icin CTRL+C yapabilirsiniz.
echo.

python manage.py runserver

pause

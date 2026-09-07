@echo off
setlocal
cd /d "%~dp0"

echo ============================================
echo ERK Arac Database - GitHub Guncelleme
echo ============================================
echo.

git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo HATA: Bu klasor bir git deposu degil ya da git bulunamadi.
    pause
    exit /b 1
)

echo --- Durum ozeti ---
git status
echo.

echo --- Degisen dosyalar (kisa) ---
git status --short
echo.

set /p "devam=Bu degisiklikleri GitHub'a gondermek istiyor musunuz? (E/H): "
if /i not "%devam%"=="E" (
    echo Iptal edildi, hicbir sey gonderilmedi.
    pause
    exit /b 0
)

set "mesaj="
set /p "mesaj=Commit mesaji yazin (bos birakirsan tarih/saat yazilir): "
if "%mesaj%"=="" set "mesaj=Guncelleme - %date% %time%"

git add .
git commit -m "%mesaj%"
if errorlevel 1 (
    echo.
    echo NOT: Commit yapilamadi - muhtemelen gonderilecek yeni bir degisiklik yok.
    pause
    exit /b 0
)

echo.
echo --- GitHub'a gonderiliyor ---
git push
if errorlevel 1 (
    echo.
    echo HATA: Push basarisiz oldu. Yukaridaki hata mesajini kontrol edin.
    echo Internet baglantisi veya GitHub kimlik dogrulamasi ile ilgili olabilir.
    pause
    exit /b 1
)

echo.
echo ============================================
echo Tamamlandi. Degisiklikler GitHub'a gonderildi.
echo https://github.com/EnginBagci/erk-database
echo ============================================
pause

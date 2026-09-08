@echo off
setlocal
cd /d "%~dp0"

echo ERK Arac Database - Goruntuleyici baslatiliyor...
echo.

if not exist ".venv\Scripts\python.exe" (
    echo HATA: .venv bulunamadi. Once "python -m venv .venv" ve
    echo "pip install -r requirements.txt" calistirdiginizdan emin olun.
    pause
    exit /b 1
)

rem ONEMLI (birkac denemeden sonra buraya karar verildi): sunucuyu bu
rem pencerede, ON PLANDA calistiriyoruz -- "start" ile AYRI bir pencerede
rem ACMIYORUZ artik. Sebep: "python -m src.viewer" komutu dogrudan
rem calistirildiginda hep sorunsuz acildi (test edildi), ama onceki
rem denemelerde "start" ile ayri pencerede + port kontrolu (once sabit
rem bekleme, sonra powershell dongusu) bu bilgisayarda guvenilmez cikti --
rem bazen hic acilmiyor, bazen uzun sure donup kaliyordu (muhtemelen
rem guvenlik yazilimi/firewall yerel baglanti denemelerini yavaslatiyor).
rem O yuzden en basit ve zaten calistigi kanitlanmis yontemi kullaniyoruz:
rem sunucuyu normal, dogrudan calistirma.
rem
rem Tarayiciyi ise BEKLEMEDEN, ayri kucuk bir arka plan komutuyla 3 saniye
rem sonra aciyoruz (asagidaki satir). Bu, herhangi bir "hazir mi degil mi"
rem kontrolu yapmadigi icin TAKILIP KALAMAZ -- sadece 3 saniye sayar ve
rem tarayici sekmesini acar. Sunucu 3 saniyede tam hazir olmadiysa
rem tarayicida "baglanti reddedildi" gorebilirsin, o durumda F5 (yenile)
rem tusuna basman yeterlidir.
start "" cmd /c "timeout /t 3 /nobreak >nul & start http://localhost:5050"

echo Sunucu bu pencerede calisacak, tarayici birkac saniye icinde
echo otomatik acilacak. Acilmazsa ya da "baglanti reddedildi" gorursen,
echo tarayicida F5'e (yenile) bas.
echo Sunucuyu durdurmak icin bu pencereyi kapat ya da CTRL+C'ye bas.
echo.

.venv\Scripts\python.exe -m src.viewer

echo.
echo Sunucu durdu.
pause

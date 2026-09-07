"""
Ortam değişkenlerinden (.env) ayarları okur.
.env dosyasını .env.example'dan kopyalayıp doldur.

ÖĞRENME NOTU: Şifre/API anahtarı gibi bilgileri KODUN İÇİNE yazmak yerine
.env dosyasında tutuyoruz. Sebebi: bu dosya (config.py) GitHub'a gidiyor,
.env ise .gitignore'da olduğu için gitmiyor. Yani şifreler hiçbir zaman
GitHub'a yüklenmiyor -- sadece senin bilgisayarında, .env dosyasında duruyor.
"""
import os
from dotenv import load_dotenv

# Bu satır, aynı klasördeki .env dosyasını okuyup ortam değişkenlerine
# (os.environ) yükler. Programın en başında, başka hiçbir ayar okunmadan
# önce çalışması gerekiyor -- o yüzden dosyanın en üstünde.
load_dotenv()


def _get(name: str, default=None, required: bool = False):
    """.env'den (veya işletim sistemi ortam değişkenlerinden) bir değer okur.

    required=True verilirse ve değer boşsa program burada durur (RuntimeError
    fırlatır) -- yanlış/eksik ayarla sessizce devam edip ilerideki bir
    noktada anlaşılmaz bir hatayla karşılaşmaktansa, en başta net bir hata
    vermek daha iyi.
    """
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Eksik ortam değişkeni: {name} (.env dosyasını kontrol et)")
    return val


# --- Veritabanı ---
# UYARI: Buradaki isimler (DB_HOST, DB_NAME, ...) .env.example dosyasındaki
# isimlerle BİREBİR aynı olmak zorunda. Birini değiştirirsen diğerini de
# değiştir, yoksa _get() değeri bulamaz ve varsayılana (ya da hataya) düşer.
DB_HOST = _get("DB_HOST", "localhost")
DB_PORT = int(_get("DB_PORT", "5432"))
DB_NAME = _get("DB_NAME", "erk_arac_db")
DB_USER = _get("DB_USER", "postgres", required=True)
DB_PASSWORD = _get("DB_PASSWORD", required=True)

# --- DMS API ---
# HOST: dealer içi ağdaki DMS sunucusu. Bu script'in bu ağa erişimi olan
# bir makinede (bu bilgisayar) çalışması gerekiyor.
# UYARI: Bu IP dışarıdan (örn. bulut ortamından) erişilemez -- sadece bayi
# içi yerel ağdan (LAN) görülebilir. Script'i başka bir bilgisayarda
# çalıştırmak istersen, o bilgisayarın da bu ağa (VPN vb. ile) erişimi
# olması gerekir.
DMS_API_HOST = _get("DMS_API_HOST", "192.168.20.95:8081")
DMS_APP_KEY = _get("DMS_APP_KEY", "4B9D26B7-89D3-422D-AE11-CCAEAD45803A")

# DMS_API_MODE:
#   "direct" -> Python'dan doğrudan DMS API'sine auth alıp istek atar.
#               DOĞRULANDI (2026-09-08): auth ve GetPurchaseInvoicesByDates
#               gerçek veriyle test edildi, çalışıyor. Yeni bir endpoint
#               eklerken de bu mod kullanılacak.
#   "proxy"  -> Zaten çalışan dms-app (http://localhost:4000) üzerinden gider.
#               dms-app'te bu veriyi döndüren bir route yoksa önce onu
#               eklemek gerekir. Şu an kullanılmıyor, ileride bir ihtiyaç
#               çıkarsa diye duruyor.
DMS_API_MODE = _get("DMS_API_MODE", "direct")
DMS_PROXY_BASE_URL = _get("DMS_PROXY_BASE_URL", "http://localhost:4000")

"""
Ortam değişkenlerinden (.env) ayarları okur.
.env dosyasını .env.example'dan kopyalayıp doldur.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get(name: str, default=None, required: bool = False):
    val = os.environ.get(name, default)
    if required and not val:
        raise RuntimeError(f"Eksik ortam değişkeni: {name} (.env dosyasını kontrol et)")
    return val


# --- Veritabanı ---
DB_HOST = _get("DB_HOST", "localhost")
DB_PORT = int(_get("DB_PORT", "5432"))
DB_NAME = _get("DB_NAME", "erk_arac_db")
DB_USER = _get("DB_USER", "postgres", required=True)
DB_PASSWORD = _get("DB_PASSWORD", required=True)

# --- DMS API ---
# HOST: dealer içi ağdaki DMS sunucusu. Bu script'in bu ağa erişimi olan
# bir makinede (bu bilgisayar) çalışması gerekiyor.
DMS_API_HOST = _get("DMS_API_HOST", "192.168.20.95:8081")
DMS_APP_KEY = _get("DMS_APP_KEY", "4B9D26B7-89D3-422D-AE11-CCAEAD45803A")

# DMS_API_MODE:
#   "direct" -> Python'dan doğrudan DMS API'sine auth alıp istek atar.
#               Auth isteğinin gövdesi/başlıkları TAHMİNİ yazıldı, dms-app'in
#               server.js dosyasındaki GERÇEK auth isteğine bakıp
#               api_client.py -> get_auth_token() içini ona göre düzeltmen gerekiyor.
#   "proxy"  -> Zaten çalışan dms-app (http://localhost:4000) üzerinden gider.
#               dms-app'te bu veriyi döndüren bir route yoksa önce onu eklemek gerekir.
DMS_API_MODE = _get("DMS_API_MODE", "direct")
DMS_PROXY_BASE_URL = _get("DMS_PROXY_BASE_URL", "http://localhost:4000")

"""
DMS API istemcisi.

ETKİ HARİTASI: Bu dosyadaki DmsApiClient sınıfı (özellikle get_auth_token
ve _headers) TÜM gelecek endpoint'ler tarafından paylaşılıyor. Yani auth
mantığında yapılan bir değişiklik, ileride eklenecek her etl_*.py dosyasını
da etkiler. Yeni bir endpoint eklerken bu sınıfa sadece YENİ BİR METOD
ekle (get_service_orders gibi), get_auth_token'a dokunma.

DOĞRULANMIŞ DURUM (2026-09-08): Auth ve GetPurchaseInvoicesByDates canlı
veriyle test edildi, çalışıyor. Aşağıdaki notlar artık tahmin değil.
"""
import datetime as dt
import time

import requests

from . import config


class DmsApiError(RuntimeError):
    """DMS API'sinden gelen her türlü hata bu tip üzerinden fırlatılıyor.
    Böylece çağıran kod (etl.py) "except DmsApiError" ile sadece API
    hatalarını yakalayabiliyor, programlama hatalarını (örn. yanlış
    kullanım) farklı ele alabiliyor."""
    pass


class DmsApiClient:
    def __init__(self):
        # Token'ı bellekte tutuyoruz (cache) ki her istek için yeniden auth
        # almayalım -- her auth isteği DMS sunucusuna ekstra yük demek.
        self._token = None
        self._token_expires_at = 0  # epoch seconds (time.time() ile karşılaştırılır)

    # ------------------------------------------------------------------
    # AUTH
    # ------------------------------------------------------------------
    def _base_url(self) -> str:
        """DMS_API_HOST'un başına http:// eklenmemişse ekler.
        (.env'de sadece "192.168.20.95:8081" yazılmışsa burada tamamlanır.)"""
        host = config.DMS_API_HOST
        if not host.startswith("http"):
            host = f"http://{host}"
        return host

    def get_auth_token(self) -> str:
        """DMS API'sinden auth token alır. Token'ı süresi dolana kadar cache'ler.

        DOĞRULANDI (2026-09-08): Gerçek yanıt şekli
        {"isSuccess": true, "statusCode": 200, "errorMessage": null, "data": "<JWT>"}
        Token, JWT olarak "data" alanında geliyor ve ~15 gün geçerli.

        UYARI: Bu yanıt zarfı ({"isSuccess", "data", ...}) muhtemelen bu
        API'nin GENEL deseni -- GetPurchaseInvoicesByDates'te de aynısını
        gördük. Yeni bir endpoint eklerken önce bunu doğrula, ama aynı
        olacağını varsayıp kör kod yazma (bkz. get_purchase_invoices_by_dates
        içindeki kontrol).
        """
        now = time.time()
        # Cache'lenmiş, süresi dolmamış bir token varsa onu kullan --
        # gereksiz auth isteği atmayalım.
        if self._token and now < self._token_expires_at:
            return self._token

        url = f"{self._base_url()}/api/RequestAuthorization/GetRequestAuthorization"
        payload = {"AppKey": config.DMS_APP_KEY}

        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()  # HTTP 4xx/5xx ise burada exception fırlar
        data = resp.json()

        if data.get("isSuccess") is False:
            raise DmsApiError(f"Auth başarısız: {data.get('errorMessage')} (ham yanıt: {data})")

        token = data.get("data")
        if not token:
            # Buraya düşersek API'nin yanıt şekli değişmiş demektir --
            # sessizce devam etmek yerine ham yanıtı gösterip duruyoruz.
            raise DmsApiError(
                f"Auth yanıtında token alanı bulunamadı. Ham yanıt: {data}"
            )

        self._token = token
        # Token JWT, ~15 gün geçerli. Temkinli davranıp 12 saat cache'liyoruz
        # (uzun süren toplu çekimlerde gereksiz yere sık auth isteği atmamak
        # için). 12 saati aşan tek bir run_range çağrısı olursa otomatik
        # olarak yeni token alınır, elle bir şey yapmana gerek yok.
        self._token_expires_at = now + 12 * 60 * 60
        return token

    def _headers(self) -> dict:
        """Her API isteğinde kullanılacak standart header'lar. Yeni bir
        endpoint metodu eklerken requests.get/post çağrısına
        headers=self._headers() geçmen yeterli, token yönetimiyle
        uğraşmana gerek yok."""
        token = self.get_auth_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # ENDPOINTLER
    # Yeni bir endpoint eklerken buraya benzer bir metod ekle. Şablon:
    #   1. URL'i kur
    #   2. Parametreleri hazırla (API'nin gerçek beklediği isim/format neyse)
    #   3. self._headers() ile GET/POST at
    #   4. Yanıt zarfını (isSuccess/data) kontrol et, asıl veriyi döndür
    # ------------------------------------------------------------------
    def get_purchase_invoices_by_dates(
        self, start_date: dt.date, end_date: dt.date
    ) -> list[dict]:
        """GET /api/Sales/GetPurchaseInvoicesByDates

        DÜZELTİLDİ (2026-09-08): Özette "API doğrudan array döndürüyor"
        deniyordu ama gerçekte auth ile aynı zarf (envelope) kullanılıyor:
        {"isSuccess": true, "statusCode": 200, "errorMessage": null, "data": [...]}
        Asıl liste "data" alanının içinde.

        UYARI: DMS API'sinin bir istekte en fazla 28 GÜNLÜK tarih aralığı
        kabul ettiği doğrulandı (kullanıcı bildirdi, daha genişi 400 Bad
        Request döndürüyor). Bu fonksiyonu tek başına çağırırken start_date
        ile end_date arasının 28 günü geçmediğinden emin ol -- parçalama
        işini normalde etl.py'deki run_range() yapıyor.
        """
        url = f"{self._base_url()}/api/Sales/GetPurchaseInvoicesByDates"
        params = {
            "StartDate": start_date.strftime("%Y-%m-%dT00:00:00.000"),
            "EndDate": end_date.strftime("%Y-%m-%dT00:00:00.000"),
        }

        resp = requests.get(url, headers=self._headers(), params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if isinstance(data, dict):
            if data.get("isSuccess") is False:
                raise DmsApiError(
                    f"API hata döndürdü: {data.get('errorMessage')} (ham yanıt: {data})"
                )
            inner = data.get("data")
            if isinstance(inner, list):
                return inner
            raise DmsApiError(
                f"Beklenmeyen yanıt şekli ('data' alanı liste değil). Ham yanıt: {data}"
            )

        # Zarfsız (ham array) yanıt ihtimaline karşı da bir yol bırakıyoruz --
        # API dokümantasyonuyla gerçek davranış arasında fark çıkabildiğini
        # zaten bir kere gördük.
        if not isinstance(data, list):
            raise DmsApiError(
                f"Beklenmeyen yanıt şekli (array/dict bekleniyordu): {type(data)} - ham yanıt: {data}"
            )
        return data


class DmsProxyClient:
    """dms-app (Node.js, http://localhost:4000) üzerinden erişim.

    Şu an KULLANILMIYOR (config.DMS_API_MODE varsayılan olarak "direct").
    Doğrudan bağlantı bir sorun çıkarırsa (örn. bu bilgisayardan DMS ağına
    erişim kesilirse ama dms-app çalışan başka bir makinede duruyorsa) diye
    hazır bekletiliyor.

    UYARI: dms-app'te bu veriyi dönen bir route yoksa (örn.
    /api/purchase-invoices) önce onu dms-app tarafında eklemek gerekir.
    Route adını kendi projene göre değiştir -- şu anki değer bir tahmin/
    yer tutucu.
    """

    def __init__(self):
        self.base_url = config.DMS_PROXY_BASE_URL

    def get_purchase_invoices_by_dates(
        self, start_date: dt.date, end_date: dt.date
    ) -> list[dict]:
        url = f"{self.base_url}/api/purchase-invoices"  # TODO: gerçek route ile değiştir
        params = {
            "StartDate": start_date.strftime("%Y-%m-%dT00:00:00.000"),
            "EndDate": end_date.strftime("%Y-%m-%dT00:00:00.000"),
        }
        resp = requests.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            raise DmsApiError(
                f"Beklenmeyen yanıt şekli (array bekleniyordu): {type(data)}"
            )
        return data


def get_client():
    """etl.py bu fonksiyonu çağırır -- .env'deki DMS_API_MODE ayarına göre
    doğru istemciyi (DmsApiClient ya da DmsProxyClient) döner. etl.py'nin
    hangi sınıfı kullandığını bilmesine gerek yok, sadece get_client()
    çağırır."""
    if config.DMS_API_MODE == "proxy":
        return DmsProxyClient()
    return DmsApiClient()

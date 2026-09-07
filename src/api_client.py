"""
DMS API istemcisi.

ÖNEMLİ / DOĞRULA:
Auth isteğinin tam gövdesi ve header'ları elimde net değildi (özette sadece
endpoint + AppKey vardı). Aşağıdaki get_auth_token() içindeki gövde/header
şekli en yaygın DMS entegrasyon kalıbına göre TAHMİN edildi. dms-app
(Node.js) projesi bu API'ye zaten bağlanıyor -- oradaki server.js (veya auth
ile ilgili dosya) içindeki gerçek isteği bulup burayı ona göre düzelt.
Yanlış varsayımla ilerleyip yanlış sonuç almaktansa, bunu netleştirmek daha
sağlıklı.
"""
import datetime as dt
import time

import requests

from . import config


class DmsApiError(RuntimeError):
    pass


class DmsApiClient:
    def __init__(self):
        self._token = None
        self._token_expires_at = 0  # epoch seconds

    # ------------------------------------------------------------------
    # AUTH
    # ------------------------------------------------------------------
    def _base_url(self) -> str:
        host = config.DMS_API_HOST
        if not host.startswith("http"):
            host = f"http://{host}"
        return host

    def get_auth_token(self) -> str:
        """DMS API'sinden auth token alır. Token'ı süresi dolana kadar cache'ler.

        TODO (doğrula): Gerçek istek gövdesi/başlığı dms-app'teki çalışan
        koda göre düzeltilmeli. Aşağıdaki sadece makul bir varsayım.
        """
        now = time.time()
        if self._token and now < self._token_expires_at:
            return self._token

        url = f"{self._base_url()}/api/RequestAuthorization/GetRequestAuthorization"
        payload = {"AppKey": config.DMS_APP_KEY}

        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        # API'nin token alanının adı farklı olabilir (Token, AccessToken,
        # token, vs.) -- gerçek yanıtı bir kere print/log edip burayı
        # ona göre düzelt.
        token = (
            data.get("token")
            or data.get("Token")
            or data.get("accessToken")
            or data.get("AccessToken")
        )
        if not token:
            raise DmsApiError(
                f"Auth yanıtında token alanı bulunamadı. Ham yanıt: {data}"
            )

        self._token = token
        # Süre bilgisi yoksa temkinli davranıp 10 dakika say.
        self._token_expires_at = now + 10 * 60
        return token

    def _headers(self) -> dict:
        token = self.get_auth_token()
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # ENDPOINTLER
    # ------------------------------------------------------------------
    def get_purchase_invoices_by_dates(
        self, start_date: dt.date, end_date: dt.date
    ) -> list[dict]:
        """GET /api/Sales/GetPurchaseInvoicesByDates

        API doğrudan array döndürüyor (r[0] gibi, r.data[0] değil).
        """
        url = f"{self._base_url()}/api/Sales/GetPurchaseInvoicesByDates"
        params = {
            "StartDate": start_date.strftime("%Y-%m-%dT00:00:00.000"),
            "EndDate": end_date.strftime("%Y-%m-%dT00:00:00.000"),
        }

        resp = requests.get(url, headers=self._headers(), params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list):
            raise DmsApiError(
                f"Beklenmeyen yanıt şekli (array bekleniyordu): {type(data)}"
            )
        return data


class DmsProxyClient:
    """dms-app (Node.js, http://localhost:4000) üzerinden erişim.

    dms-app'te bu veriyi dönen bir route yoksa (örn. /api/purchase-invoices)
    önce onu dms-app tarafında eklemek gerekir. Route adını kendi projene
    göre değiştir.
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
    if config.DMS_API_MODE == "proxy":
        return DmsProxyClient()
    return DmsApiClient()

# ERK Araç Database

Hyundai DMS API'sinden araç/fatura verisini çekip PostgreSQL'e yazan ETL.
Şasi numarası (VIN) merkezli, normalize şema.

## Şu an ne yapıyor / ne yapmıyor

Yapıyor: `GetPurchaseInvoicesByDates` sonucundan carline, spec, renk,
spec_ocn_renk, araç, plaka, alış faturası kayıtlarını upsert ediyor.

Henüz yapmıyor (özetteki "SONRADAN" bölümleri, ayrı endpoint/iş gerektiriyor):
- `motor_tipleri` (hacim/güç/tork) ve `ocn.motor_id` / `vites_id` — bu
  endpoint bu bilgileri döndürmüyor, teknik detay endpoint'i eklenince
  UPDATE ile doldurulmalı.
- `gumruk_bilgileri` — bu endpoint'te yok.
- Müşteri, araç sahipliği, satış faturası, servis iş emri — plandaki
  sonraki adımlar.
- API yanıtındaki `modelNumber` alanı şu an hiçbir kolona yazılmıyor çünkü
  şemada karşılığı yoktu. Ne olduğunu netleştirip (motor kodu mu, model
  numarası mı) uygun bir kolona bağlamak gerekebilir.

## Doğrulanması gereken tek kritik nokta: DMS auth

`src/api_client.py` içindeki `get_auth_token()` fonksiyonu, auth isteğinin
gövdesini/header'ını **tahmin ederek** yazıldı (`{"AppKey": ...}` POST,
yanıtta `token`/`Token` alanı bekleniyor). Elimde bu isteğin gerçek şekli
yoktu. **dms-app** (Node.js) projesi bu API'ye zaten bağlanıyor — oradaki
gerçek isteği bulup (server.js ya da auth ile ilgili dosya) bu fonksiyonu
ona göre düzelt, ya da `.env`'de `DMS_API_MODE=proxy` yapıp dms-app
üzerinden gitmeyi tercih et (bu durumda dms-app'e bu veriyi dönen bir route
eklemen gerekir — `src/api_client.py` içindeki `DmsProxyClient` sınıfında
route adını güncelle).

Bunu doğrulamadan gerçek veri ile test etmenin bir anlamı yok — auth
başarısız olur ya da (daha kötüsü) yanlış varsayımla sessizce yanlış
davranır.

## Kurulum

```bash
cd erk-database
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

copy .env.example .env        # Windows (cp .env.example .env / Linux-Mac)
# .env dosyasını aç, DB_PASSWORD gir, DMS_API_MODE'u seç
```

## Veritabanını oluştur

```bash
createdb erk_arac_db
psql -d erk_arac_db -f sql/schema.sql
```

## Test (1 haftalık küçük aralık)

```bash
python -m src.etl 2026-08-25 2026-08-31
```

Log satırlarında kaç araç/fatura eklendiğini göreceksin. Şüpheli bir şey
görürsen (0 kayıt, auth hatası, beklenmeyen alan adı) devam etmeden önce
API yanıtının ham halini bir kere yazdırıp (`print(records[0])` gibi)
alan adlarını gerçek veriyle karşılaştır — özetteki alan adları API
dokümantasyonundan çıkarım, gerçek yanıt farklı casing/isim kullanabilir.

## Tüm geçmişi çekme (2020 - bugün)

Test başarılı olduktan sonra:

```bash
python -m src.etl 2020-01-01 2026-09-07
```

`run_range` zaten 7 günlük parçalara bölerek gidiyor (`chunk_days`
parametresiyle değiştirilebilir). Script tekrar tekrar çalıştırılabilir —
şasi ve fatura ID'leri unique olduğu için zaten var olan kayıtlar atlanır,
kaldığı yerden devam edilebilir.

## Git / GitHub

Bu depoyu ben oluşturamadım (bu ortamda GitHub CLI / senin hesabın yok).
Kendi bilgisayarında:

```bash
cd erk-database
git init
git add .
git commit -m "İlk sürüm: şema + purchase invoice ETL"
gh repo create erk-database --private --source=. --push
```

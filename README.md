# ERK Araç Database

Hyundai DMS API'sinden araç/fatura verisini çekip PostgreSQL'e yazan ETL.
Şasi numarası (VIN) merkezli, normalize şema.

Durum (2026-09-08): `GetPurchaseInvoicesByDates` endpoint'i tamamen çalışıyor
ve doğrulandı, 2020-01-01'den bugüne tüm alış faturaları çekildi (~8880
fatura, ~3000+ araç).

## Şu an ne yapıyor / ne yapmıyor

Yapıyor: `GetPurchaseInvoicesByDates` sonucundan carline, spec, renk,
spec_ocn_renk, araç, plaka, gümrük bilgisi, alış faturası kayıtlarını upsert
ediyor.

Henüz yapmıyor (ayrı endpoint/iş gerektiriyor):
- `motor_tipleri` (hacim/güç/tork) ve `ocn.motor_id` / `vites_id` — bu
  endpoint bu bilgileri döndürmüyor, teknik detay endpoint'i eklenince
  UPDATE ile doldurulmalı.
- Müşteri, araç sahipliği, satış faturası, servis iş emri — plandaki
  sonraki adımlar, ayrı endpoint'ler gerekiyor.

## DMS API hakkında doğrulanmış gerçekler

Bunlar tahmin değil, canlı veriyle test edilerek doğrulandı:

- **Auth**: `POST /api/RequestAuthorization/GetRequestAuthorization` gövdesi
  `{"AppKey": ...}`. Yanıt zarfı `{"isSuccess", "statusCode", "errorMessage",
  "data"}` şeklinde; token JWT olarak `data` alanında geliyor, ~15 gün geçerli.
- **Aynı zarf** liste endpoint'lerinde de var: `GetPurchaseInvoicesByDates`
  ham array değil, `{"isSuccess":..., "data": [...]}` dönüyor — asıl liste
  `data` içinde.
- **28 günlük limit**: Bir istekte en fazla 28 günlük tarih aralığı kabul
  ediliyor, daha genişi 400 Bad Request. `etl.py`'deki `run_range` bunu
  28'lik parçalara bölerek yönetiyor.
- **Yanıt yapısı düz değil, iç içe**: `vinNumber`, `engineNumber`,
  `plateNumber`, `carLineType`, `modelNumber` üst seviyede değil,
  `invoiceDetail.item` içinde. Carline/spec/renk bilgileri de
  `invoiceDetail.item.specOcnColorInteriorColor` içinde.
- **Gümrük bilgisi bu endpoint'te var**: `dutyClaimDate/Number`,
  `dutyInvoiceDate/Number`, `dutyOffice` — ayrı bir endpoint beklemeye
  gerek yoktu, `gumruk_bilgileri` tablosu bu adımda dolduruluyor (sadece
  ithal araçlarda dolu geliyor, yerli üretimde boş kalması normal).
- **Üst seviye `totalDiscountAmount` yanıltıcı**: Bu aslında indirimli NET
  fiyat, gerçek indirim tutarı değil. Gerçek indirim tutarı ve KDV oranı
  sadece `invoiceDetail.discountAmount` / `invoiceDetail.taxPercent`
  içinde var — fiyat alanları oradan okunuyor.
- **`modelYear` genelde boş**: gerçek model yılı `item.modelNumber`
  alanında geliyor (örn. 2026), `modelYear` şu ana kadar hep null çıktı.

## Windows + Türkçe yerel ayar: encoding tuzağı

Bu bilgisayarda PostgreSQL bağlantıları (hem `psql` hem varsayılan
`psycopg2` bağlantısı) otomatik olarak `WIN1254` client_encoding
kullanıyor, veritabanı `UTF8`. Bu bir veri bozulmasına yol açmıyor (Türkçe
karakterler WIN1254'te de temsil edilebiliyor) ama **psql çıktısında**
karakterler bozuk görünüyor. `db.py` artık bağlantı açılır açılmaz
`conn.set_client_encoding("UTF8")` çağırıyor. Elle `psql` ile veri
kontrol ederken önce şunu çalıştır:

```sql
SET client_encoding TO 'UTF8';
```

## Kurulum

```cmd
cd erk-database
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
notepad .env
:: DB_PASSWORD gir. DMS_API_MODE=direct kalsın (auth doğrulandı, çalışıyor).
```

PostgreSQL bu bilgisayarda PATH'te değil, gerekirse önce:

```cmd
set PATH=%PATH%;C:\Program Files\PostgreSQL\18\bin
```

## Veritabanını oluştur

```cmd
psql -U postgres -c "CREATE DATABASE erk_arac_db;"
psql -U postgres -d erk_arac_db -f sql\schema.sql
```

## Test (1 haftalık küçük aralık)

```cmd
python -m src.etl 2026-08-25 2026-08-31
```

## Tüm geçmişi çekme (2020 - bugün)

```cmd
python -m src.etl 2020-01-01 2026-09-07
```

`run_range` 28 günlük parçalara bölerek gidiyor (API limiti). Script
tekrar tekrar çalıştırılabilir — şasi ve fatura ID'leri unique olduğu için
zaten var olan kayıtlar atlanır (idempotent), kaldığı yerden devam edilir.
Tamlığı kontrol etmek için aya göre kayıt sayısına bakmak faydalı:

```sql
SELECT date_trunc('month', fatura_tarihi)::date AS ay, COUNT(*)
FROM alis_faturalari GROUP BY 1 ORDER BY 1;
```

Bir ayda beklenmedik şekilde 0 çıkarsa o parça başarısız olmuş demektir,
`run_range`'i o aralık için tekrar çalıştır.

## Git / GitHub

Repo: https://github.com/EnginBagci/erk-database (private). Değişiklik
yaptıktan sonra:

```cmd
git add .
git commit -m "Açıklama"
git push
```

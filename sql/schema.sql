-- ============================================================
-- ERK ARAÇ DATABASE - PostgreSQL Şeması
-- Şasi numarası (VIN) merkezli, tam normalize araç/fatura/müşteri şeması.
-- Hyundai DMS API'sinden (GetPurchaseInvoicesByDates ve sonrası) beslenir.
--
-- ETKİ HARİTASI (öğrenme/takip notu):
-- Bu dosyadaki her tabloya HANGİ Python dosyasının yazdığını yanında
-- belirttik ("-- YAZAN: ..."). Bir tabloya kolon eklersen/kaldırırsan,
-- o kolonu kullanan Python dosyasını da güncellemen gerekir -- yoksa
-- INSERT sorguları kolon sayısı uyuşmazlığından hata verir.
-- ============================================================

BEGIN;

-- Küçük not: her tabloya olusturulma_tarihi/guncellenme_tarihi eklendi.
-- Özette yoktu ama ETL'in ne zaman ne yazdığını görebilmek (debug,
-- "bu kayıt ne zaman değişti" gibi sorular) için pratik bir ekleme.
-- İstemezsen kaldırabiliriz.

-- ============================================================
-- LOOKUP TABLOLARI
-- YAZAN: src/etl.py (adım 1-3) -- upsert_and_get_id ile, tekrar
-- yazılmaz, aynı kod/isim geldiğinde mevcut kaydın id'si kullanılır.
-- ============================================================

-- Araç tipi (Binek, Ticari, vb.). UNIQUE(hyundai_tip_id) ÖNEMLİ: etl.py
-- bu kolon üzerinden "ON CONFLICT" yapıyor, bu kısıtlama kaldırılırsa
-- upsert hata verir.
CREATE TABLE arac_tipleri (
    id                  SERIAL PRIMARY KEY,
    hyundai_tip_id      TEXT UNIQUE,          -- API: carLineTypeID
    adi                 TEXT NOT NULL,
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Model ailesi (örn. "IONIQ6 (CE)"). Her carline bir arac_tipi'ne bağlı.
CREATE TABLE carline (
    id                  SERIAL PRIMARY KEY,
    kod                 TEXT NOT NULL UNIQUE, -- API: carlineCode
    adi                 TEXT,                 -- API: carlineName
    tip_id              INTEGER REFERENCES arac_tipleri(id),
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Model yılı (örn. 2026). Ayrı bir tablo olmasının sebebi: aynı yıl birden
-- fazla spec/carline tarafından paylaşılıyor, tekrar tekrar yazmamak için.
CREATE TABLE model_yillari (
    id                  SERIAL PRIMARY KEY,
    yil                 INTEGER NOT NULL UNIQUE  -- API: modelYear (gerçekte modelNumber'dan geliyor, bkz. etl.py adım 3)
);

-- ============================================================
-- RENK
-- YAZAN: src/etl.py (adım 5-6). Kategori/özellik/malzeme tabloları şu an
-- HİÇBİR YERDEN doldurulmuyor (etl.py sadece kod+isim yazıyor,
-- kategori_id/ozellik_id hep NULL kalıyor) -- ileride renk verisini
-- kategorize etmek istersen ya elle doldurulur ya da API'de bu bilgi
-- bulunursa etl.py'ye eklenir.
-- ============================================================

CREATE TABLE dis_renk_kategorileri (
    id      SERIAL PRIMARY KEY,
    adi     TEXT NOT NULL UNIQUE
);

CREATE TABLE dis_renk_ozellikleri (      -- Sedefli, Metalik, Mat, Solid...
    id      SERIAL PRIMARY KEY,
    adi     TEXT NOT NULL UNIQUE
);

CREATE TABLE dis_renkler (
    id              SERIAL PRIMARY KEY,
    kod             TEXT NOT NULL UNIQUE,   -- API: colorCode
    adi             TEXT,                   -- API: colorName
    kategori_id     INTEGER REFERENCES dis_renk_kategorileri(id),  -- şu an hep NULL
    ozellik_id      INTEGER REFERENCES dis_renk_ozellikleri(id),   -- şu an hep NULL
    aktif_mi        BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE ic_renk_kategorileri (
    id      SERIAL PRIMARY KEY,
    adi     TEXT NOT NULL UNIQUE
);

CREATE TABLE ic_renk_malzemeleri (        -- Deri, Kumaş, Suet...
    id      SERIAL PRIMARY KEY,
    adi     TEXT NOT NULL UNIQUE
);

CREATE TABLE ic_renkler (
    id              SERIAL PRIMARY KEY,
    kod             TEXT NOT NULL UNIQUE,   -- API: interiorColorCode
    adi             TEXT,                   -- API: interiorColorName
    kategori_id     INTEGER REFERENCES ic_renk_kategorileri(id),  -- şu an hep NULL
    malzeme_id      INTEGER REFERENCES ic_renk_malzemeleri(id),   -- şu an hep NULL
    aktif_mi        BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- MOTOR / TEKNİK
-- YAZAN: ŞU AN HİÇBİR PYTHON DOSYASI. GetPurchaseInvoicesByDates bu
-- bilgileri döndürmüyor. Bu tablolar ileride bir "teknik detay"
-- endpoint'i eklenince kullanılacak (bkz. erk-arac-database skill'i).
-- ocn.motor_id / ocn.vites_id o zaman UPDATE ile doldurulacak, etl.py'nin
-- ocn INSERT'ine dokunmaya gerek kalmayacak.
-- ============================================================

CREATE TABLE yakit_tipleri (
    id      SERIAL PRIMARY KEY,
    adi     TEXT NOT NULL UNIQUE   -- Benzin, Dizel, Hibrit, Elektrik...
);

CREATE TABLE vites_tipleri (
    id      SERIAL PRIMARY KEY,
    adi     TEXT NOT NULL UNIQUE   -- Manuel, Otomatik, DCT, IVT...
);

CREATE TABLE motor_tipleri (
    id          SERIAL PRIMARY KEY,
    kod         TEXT UNIQUE,
    hacim_cc    INTEGER,
    guc_hp      INTEGER,
    tork_nm     INTEGER,
    yakit_id    INTEGER REFERENCES yakit_tipleri(id)
);

-- ============================================================
-- SPEC / OCN
-- YAZAN: src/etl.py (adım 4, 7-9)
-- (Bir "spec", bir carline + model yılı kombinasyonudur.
--  Bir "ocn", o spec üzerindeki donanım/motor/vites paketidir.
--  spec_ocn, ikisinin birleşimidir (API: fullSpecCode).
--  spec_ocn_renk, o kombinasyonun belirli bir dış/iç renk versiyonudur.)
--
-- UYARI: Bu dört tablo (spec, ocn, spec_ocn, spec_ocn_renk) birbirine
-- sıkı bağlı. Birine UNIQUE/kolon eklemeden önce etl.py'deki adım 4/7/8/9
-- sırasını ve upsert_and_get_id çağrılarını mutlaka kontrol et.
-- ============================================================

CREATE TABLE spec (
    id              SERIAL PRIMARY KEY,
    kod             TEXT NOT NULL UNIQUE,     -- API: specCode
    carline_id      INTEGER REFERENCES carline(id),
    model_yil_id    INTEGER REFERENCES model_yillari(id)
);

CREATE TABLE ocn (
    id              SERIAL PRIMARY KEY,
    no              TEXT NOT NULL UNIQUE,     -- API: ocnNumber
    adi             TEXT,                     -- API: specOcnName
    spec_id         INTEGER REFERENCES spec(id),
    motor_id        INTEGER REFERENCES motor_tipleri(id),  -- şu an hep NULL, bkz. yukarıdaki not
    vites_id        INTEGER REFERENCES vites_tipleri(id),  -- şu an hep NULL
    donanim         TEXT,                                  -- şu an hep NULL
    ecall_var_mi    BOOLEAN                                -- şu an hep NULL
);

CREATE TABLE spec_ocn (
    id              SERIAL PRIMARY KEY,
    spec_id         INTEGER NOT NULL REFERENCES spec(id),
    ocn_id          INTEGER NOT NULL REFERENCES ocn(id),
    full_spec_kodu  TEXT UNIQUE,              -- API: fullSpecCode
    UNIQUE (spec_id, ocn_id)
);

CREATE TABLE spec_ocn_renk (
    id              SERIAL PRIMARY KEY,
    spec_ocn_id     INTEGER NOT NULL REFERENCES spec_ocn(id),
    dis_renk_id     INTEGER REFERENCES dis_renkler(id),
    ic_renk_id      INTEGER REFERENCES ic_renkler(id),
    tam_adi         TEXT,
    aktif_mi        BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (spec_ocn_id, dis_renk_id, ic_renk_id)
);

-- ============================================================
-- BAYİ
-- YAZAN: src/etl.py (adım 10) -- update_cols=["kodu","adi"] ile her
-- faturada güncelleniyor (bkz. etl.py'deki not). Şu an tek bayi (ERK
-- Otomotiv, kod 01105) olacak ama tablo çoklu bayiyi de destekler.
-- ============================================================

CREATE TABLE bayiler (
    id          SERIAL PRIMARY KEY,
    hyundai_id  TEXT UNIQUE,          -- API: dealerID
    kodu        TEXT,
    adi         TEXT,
    aktif_mi    BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- ARAÇ  (şasi = merkez)
-- YAZAN: src/etl.py (adım 11) -- sadece şasi YOKSA yeni satır ekler.
-- Şasi zaten varsa bu tabloya BİR DAHA YAZILMAZ (bkz. etl.py'deki
-- "KASITLI TASARIM" notu) -- ileride başka bir endpoint bu araca dair
-- ek bilgi getirirse (örn. plaka değişikliği), o script de "şasi var mı"
-- kontrolüyle bu tabloya UPDATE atmalı, INSERT değil.
-- ============================================================

CREATE TABLE araclar (
    id                  SERIAL PRIMARY KEY,
    sasi_no             TEXT NOT NULL UNIQUE,   -- API: vinNumber -- SİSTEMİN ANA ANAHTARI
    motor_no            TEXT,                   -- API: engineNumber
    model_yili          INTEGER,                -- API: modelYear (denormalize edilmiş hızlı erişim için)
    spec_ocn_renk_id    INTEGER REFERENCES spec_ocn_renk(id),
    aktif_mi            BOOLEAN NOT NULL DEFAULT TRUE,
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now(),
    guncellenme_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_araclar_spec_ocn_renk ON araclar(spec_ocn_renk_id);

-- YAZAN: src/etl.py (adım 12) -- aynı (arac_id, plaka) ikilisi için
-- mükerrer satır açılmaması kontrol ediliyor.
CREATE TABLE plakalar (
    id          SERIAL PRIMARY KEY,
    arac_id     INTEGER NOT NULL REFERENCES araclar(id),
    plaka       TEXT NOT NULL,                  -- API: plateNumber
    baslangic   DATE,
    bitis       DATE,
    aktif_mi    BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_plakalar_arac ON plakalar(arac_id);
CREATE INDEX idx_plakalar_plaka ON plakalar(plaka);

-- YAZAN: src/etl.py (adım 13) -- sadece talep_no/fatura_no doluysa
-- yazılır (ithal araçlar). Bu tabloda UNIQUE kısıtlaması YOK (aynı arac_id
-- için birden fazla gümrük kaydı olabilir ihtimaline karşı), o yüzden
-- etl.py kendi elle bir SELECT ile mükerrer kaydı önlüyor.
CREATE TABLE gumruk_bilgileri (
    id                  SERIAL PRIMARY KEY,
    arac_id             INTEGER NOT NULL REFERENCES araclar(id),
    talep_tarihi        DATE,
    talep_no            TEXT,
    fatura_tarihi       DATE,
    fatura_no           TEXT,
    gumruk_mudurlugu    TEXT
);

CREATE INDEX idx_gumruk_arac ON gumruk_bilgileri(arac_id);

-- ============================================================
-- FATURA (alış)
-- YAZAN: src/etl.py (adım 14) -- BU TABLONUN DOLUP DOLMAMASI, ETL
-- SCRIPT'İNİN "İŞİNİ BİTİRDİĞİNİN" GÖSTERGESİ. hyundai_fatura_id UNIQUE
-- olduğu için script tekrar çalıştırıldığında aynı fatura ikinci kez
-- eklenmez (idempotent) -- bu kısıtlamayı kaldırma.
-- ============================================================

CREATE TABLE alis_faturalari (
    id                  SERIAL PRIMARY KEY,
    arac_id             INTEGER NOT NULL REFERENCES araclar(id),
    bayi_id             INTEGER REFERENCES bayiler(id),
    hyundai_fatura_id   TEXT NOT NULL UNIQUE,   -- API: fatura.id -- mükerrer kayıt engelleyen kilit nokta
    fatura_no           TEXT,                   -- API: formalInvoiceNumber
    irsaliye_no         TEXT,                   -- API: waybillNumber
    fatura_tarihi       DATE,                   -- API: invoiceDate
    irsaliye_tarihi     DATE,                   -- API: waybillDate
    liste_fiyat         NUMERIC(14,2),          -- API: invoiceDetail.price
    indirim             NUMERIC(14,2),          -- API: invoiceDetail.discountAmount
    indirimli_fiyat     NUMERIC(14,2),          -- API: invoiceDetail.discountedAmount
    kdv_orani           NUMERIC(5,2),           -- API: invoiceDetail.taxPercent
    kdv_tutari          NUMERIC(14,2),          -- API: invoiceDetail.taxAmount
    toplam              NUMERIC(14,2),          -- API: invoiceDetail.totalAmount
    durum               TEXT,                   -- API: invoiceStatus
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alis_faturalari_arac ON alis_faturalari(arac_id);
CREATE INDEX idx_alis_faturalari_bayi ON alis_faturalari(bayi_id);
CREATE INDEX idx_alis_faturalari_tarih ON alis_faturalari(fatura_tarihi);

-- ============================================================
-- MÜŞTERİ (sonradan eklenecek modül)
-- YAZAN: ŞU AN HİÇBİR PYTHON DOSYASI. Bu tablolar plandaki sonraki adım
-- (müşteri/araç sahipliği endpoint'i) için hazır duruyor, henüz boş.
-- ============================================================

CREATE TABLE musteri_tipleri (
    id      SERIAL PRIMARY KEY,
    adi     TEXT NOT NULL UNIQUE     -- Bireysel, Kurumsal, Kamu
);

CREATE TABLE telefon_tipleri (
    id      SERIAL PRIMARY KEY,
    adi     TEXT NOT NULL UNIQUE     -- Cep, Sabit, İş, Ev
);

CREATE TABLE iller (
    id      SERIAL PRIMARY KEY,
    kod     TEXT UNIQUE,
    adi     TEXT NOT NULL UNIQUE
);

CREATE TABLE ilceler (
    id      SERIAL PRIMARY KEY,
    il_id   INTEGER NOT NULL REFERENCES iller(id),
    adi     TEXT NOT NULL,
    UNIQUE (il_id, adi)
);

CREATE TABLE musteriler (
    id          SERIAL PRIMARY KEY,
    tip_id      INTEGER REFERENCES musteri_tipleri(id),
    tc_no       TEXT UNIQUE,
    vergi_no    TEXT UNIQUE,
    adi         TEXT,
    soyadi      TEXT,
    firma_adi   TEXT,
    ilce_id     INTEGER REFERENCES ilceler(id),
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE musteri_telefonlar (
    id          SERIAL PRIMARY KEY,
    musteri_id  INTEGER NOT NULL REFERENCES musteriler(id),
    tip_id      INTEGER REFERENCES telefon_tipleri(id),
    numara      TEXT NOT NULL,
    aktif_mi    BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_musteri_telefonlar_musteri ON musteri_telefonlar(musteri_id);
CREATE INDEX idx_musteri_telefonlar_numara ON musteri_telefonlar(numara);

CREATE TABLE musteri_emailler (
    id          SERIAL PRIMARY KEY,
    musteri_id  INTEGER NOT NULL REFERENCES musteriler(id),
    email       TEXT NOT NULL,
    aktif_mi    BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX idx_musteri_emailler_musteri ON musteri_emailler(musteri_id);

-- ============================================================
-- ARAÇ SAHİPLİĞİ (köprü tablo)
-- YAZAN: ŞU AN HİÇBİR PYTHON DOSYASI. Bir aracın zaman içinde birden
-- fazla sahibi olabileceği için (2. el satışlar dahil) araclar ve
-- musteriler arasında doğrudan bir kolon yerine bu köprü tablo kullanıldı.
-- ============================================================

CREATE TABLE arac_sahipligi (
    id              SERIAL PRIMARY KEY,
    arac_id         INTEGER NOT NULL REFERENCES araclar(id),
    musteri_id      INTEGER NOT NULL REFERENCES musteriler(id),
    baslangic       DATE,
    bitis           DATE,
    sahiplik_tipi   TEXT,          -- ör. "İlk Sahip", "İkinci El" vb.
    kaynak          TEXT,          -- bu bilgi nereden geldi (fatura, servis kaydı, manuel...)
    fatura_id       INTEGER REFERENCES alis_faturalari(id)
);

CREATE INDEX idx_arac_sahipligi_arac ON arac_sahipligi(arac_id);
CREATE INDEX idx_arac_sahipligi_musteri ON arac_sahipligi(musteri_id);

-- ============================================================
-- SATIŞ / SERVİS (sonradan eklenecek modül)
-- YAZAN: ŞU AN HİÇBİR PYTHON DOSYASI. satis_faturalari.arac_id ve
-- servis_is_emirleri.arac_id, araclar tablosuna bağlı olduğu için bu
-- modüller eklendiğinde de "şasi merkez" prensibi korunuyor.
-- ============================================================

CREATE TABLE satis_faturalari (
    id              SERIAL PRIMARY KEY,
    bayi_id         INTEGER REFERENCES bayiler(id),
    arac_id         INTEGER REFERENCES araclar(id),
    fatura_no       TEXT,
    fatura_tarihi   DATE,
    fiyat           NUMERIC(14,2),
    kdv             NUMERIC(14,2),
    toplam          NUMERIC(14,2),
    durum           TEXT
);

CREATE INDEX idx_satis_faturalari_arac ON satis_faturalari(arac_id);

CREATE TABLE servis_is_emirleri (
    id              SERIAL PRIMARY KEY,
    arac_id         INTEGER NOT NULL REFERENCES araclar(id),
    bayi_id         INTEGER REFERENCES bayiler(id),
    wo_no           TEXT,
    acilis_tarihi   DATE,
    kapanis_tarihi  DATE,
    durum           TEXT
);

CREATE INDEX idx_servis_is_emirleri_arac ON servis_is_emirleri(arac_id);

COMMIT;

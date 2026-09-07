-- ============================================================
-- ERK ARAÇ DATABASE - PostgreSQL Şeması
-- Şasi numarası (VIN) merkezli, tam normalize araç/fatura/müşteri şeması.
-- Hyundai DMS API'sinden (GetPurchaseInvoicesByDates ve sonrası) beslenir.
-- ============================================================

BEGIN;

-- Küçük not: her tabloya olusturulma_tarihi/guncellenme_tarihi eklendi.
-- Özette yoktu ama ETL'in ne zaman ne yazdığını görebilmek (debug,
-- "bu kayıt ne zaman değişti" gibi sorular) için pratik bir ekleme.
-- İstemezsen kaldırabiliriz.

-- ============================================================
-- LOOKUP TABLOLARI
-- ============================================================

CREATE TABLE arac_tipleri (
    id                  SERIAL PRIMARY KEY,
    hyundai_tip_id      TEXT UNIQUE,          -- API: carLineTypeID
    adi                 TEXT NOT NULL,
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE carline (
    id                  SERIAL PRIMARY KEY,
    kod                 TEXT NOT NULL UNIQUE, -- API: carlineCode
    adi                 TEXT,                 -- API: carlineName
    tip_id              INTEGER REFERENCES arac_tipleri(id),
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE model_yillari (
    id                  SERIAL PRIMARY KEY,
    yil                 INTEGER NOT NULL UNIQUE  -- API: modelYear
);

-- ============================================================
-- RENK
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
    kategori_id     INTEGER REFERENCES dis_renk_kategorileri(id),
    ozellik_id      INTEGER REFERENCES dis_renk_ozellikleri(id),
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
    kategori_id     INTEGER REFERENCES ic_renk_kategorileri(id),
    malzeme_id      INTEGER REFERENCES ic_renk_malzemeleri(id),
    aktif_mi        BOOLEAN NOT NULL DEFAULT TRUE
);

-- ============================================================
-- MOTOR / TEKNİK
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
-- (Bir "spec", bir carline + model yılı kombinasyonudur.
--  Bir "ocn", o spec üzerindeki donanım/motor/vites paketidir.
--  spec_ocn, ikisinin birleşimidir (API: fullSpecCode).
--  spec_ocn_renk, o kombinasyonun belirli bir dış/iç renk versiyonudur.)
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
    motor_id        INTEGER REFERENCES motor_tipleri(id),
    vites_id        INTEGER REFERENCES vites_tipleri(id),
    donanim         TEXT,
    ecall_var_mi    BOOLEAN
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
-- ============================================================

CREATE TABLE araclar (
    id                  SERIAL PRIMARY KEY,
    sasi_no             TEXT NOT NULL UNIQUE,   -- API: vinNumber
    motor_no            TEXT,                   -- API: engineNumber
    model_yili          INTEGER,                -- API: modelYear (denormalize edilmiş hızlı erişim için)
    spec_ocn_renk_id    INTEGER REFERENCES spec_ocn_renk(id),
    aktif_mi            BOOLEAN NOT NULL DEFAULT TRUE,
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now(),
    guncellenme_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_araclar_spec_ocn_renk ON araclar(spec_ocn_renk_id);

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
-- ============================================================

CREATE TABLE alis_faturalari (
    id                  SERIAL PRIMARY KEY,
    arac_id             INTEGER NOT NULL REFERENCES araclar(id),
    bayi_id             INTEGER REFERENCES bayiler(id),
    hyundai_fatura_id   TEXT NOT NULL UNIQUE,   -- API: fatura.id
    fatura_no           TEXT,                   -- API: formalInvoiceNumber
    irsaliye_no         TEXT,                   -- API: waybillNumber
    fatura_tarihi       DATE,                   -- API: invoiceDate
    irsaliye_tarihi     DATE,                   -- API: waybillDate
    liste_fiyat         NUMERIC(14,2),          -- API: totalBaseAmount
    indirim             NUMERIC(14,2),          -- API: totalDiscountAmount
    indirimli_fiyat     NUMERIC(14,2),          -- liste_fiyat - indirim
    kdv_orani           NUMERIC(5,2),
    kdv_tutari          NUMERIC(14,2),          -- API: totalTaxAmount
    toplam              NUMERIC(14,2),          -- API: totalInvoiceAmount
    durum               TEXT,                   -- API: invoiceStatus
    olusturulma_tarihi  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_alis_faturalari_arac ON alis_faturalari(arac_id);
CREATE INDEX idx_alis_faturalari_bayi ON alis_faturalari(bayi_id);
CREATE INDEX idx_alis_faturalari_tarih ON alis_faturalari(fatura_tarihi);

-- ============================================================
-- MÜŞTERİ (sonradan eklenecek modül)
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

"""
ERK Araç Database - Görüntüleyici

Bu GERÇEK bir uygulama değil -- sadece veritabanındaki veriyi tarayıcıda
tablo halinde GÖRMEK için küçük bir Flask sayfası. Veri ekleme/silme/
düzenleme yapmıyor, sadece okuyor (SELECT). ETL sürecine hiçbir etkisi yok.

Çalıştırma:
    python -m src.viewer
    (veya proje köşesindeki goruntule.bat'a çift tıkla)

Sonra tarayıcıda: http://localhost:5050

ÖĞRENME NOTU (Flask): Flask, Python ile web sayfası/servis yazmaya yarayan
küçük bir kütüphane. @app.route("/") gibi bir "dekoratör" (fonksiyonun
üstündeki @...), o fonksiyonu belirli bir web adresine (URL) bağlar --
tarayıcıda o adrese gidildiğinde o fonksiyon çalışır ve döndürdüğü HTML
tarayıcıda gösterilir.

SAYFA YAPISI (6. tasarım):
  1) Ana sayfa ("/"): üstte 8 tane TIKLANABİLİR özet kartı (Toplam Araç,
     Gümrük Kaydı Olan Araç, Bu Yıl/Geçen Ay/Bu Ay/Bu Hafta/Dün/Bugün
     eklenen fatura sayısı). Bir karta tıklayınca alttaki tablo o karta
     göre otomatik filtrelenir (sayfa "/" adresine ilgili ?baslangic=...
     &bitis=... ya da ?gorunum=... parametreleriyle gider).
     Altında GENEL bir arama kutusu var -- şase, motor no, model, renk,
     plaka, fatura no HANGİSİYLE eşleşirse eşleşsin sonuç getirir (tek
     tek ayrı arama kutuları yerine TEK bir "ara" kutusu). Aynı kutunun
     altında Model / Dış Renk / Yakıt Tipi seçilebilen ÜÇ combobox +
     "Filtrele" butonu var -- veritabanındaki BENZERSİZ değerlerle
     dolduruluyor, seçilince tabloyu o kritere göre filtreler.
     Ayrıca ayrı bir tarih aralığı arama formu var, Bitiş kutusunun
     YANINDA (altında değil) Bugün/Dün/Bu Hafta/Bu Ay/Geçen Ay/Bu Yıl
     hızlı butonları.
     Sonuç HER ZAMAN tek bir listeleme tablosunda gösterilir (şase, motor
     no, model, renkler, YAKIT TİPİ, plaka, fatura no/tarihi, toplam gibi
     ÖZET bilgiler). Bu tablo, sonuç bulunamadığında bile başlıklarıyla
     birlikte sabit durur -- boş diye kaybolmaz.
  2) Bir satıra tıklanınca ayrı bir DETAY sayfası ("/arac/<sasi_no>")
     KÜÇÜK, AYRI BİR PENCEREDE (popup) açılır -- ana sayfa (liste/arama)
     OLDUĞU GİBİ, hiç etkilenmeden kalır. O aracın TÜM bilgileri
     (özellikler, YAKIT TİPİ, tüm alış faturaları, gümrük bilgisi) o
     küçük pencerede gösterilir.

NOT (yakıt tipi hakkında, 2026-09-08): "Yakıt Tipi" (Benzin/Dizel/
Elektrik) DMS API'sinden gelen gerçek bir alan DEĞİL -- motor_no'nun ilk
harfinden TAHMİN ediliyor (bkz. src/etl.py: yakit_tipi_belirle()). Bu
sayfa sadece o tahmini gösterir/filtreler, kendisi bir hesaplama yapmaz.

ETKİ HARİTASI: Bu dosya db.py ve config.py'yi kullanır (okuma amaçlı).
etl.py/api_client.py'ye hiç dokunmaz, onları da etkilemez -- tamamen
bağımsız, istersen bu dosyayı silsen bile ETL çalışmaya devam eder.
"""
import calendar
import datetime as dt

from flask import Flask, request, render_template_string
import psycopg2.extras

from . import db

app = Flask(__name__)

# ------------------------------------------------------------------
# SQL sorguları
# ------------------------------------------------------------------
# ÖĞRENME NOTU: psycopg2.extras.RealDictCursor kullanıyoruz -- normal
# cursor sonuçları (a, b, c) gibi sırayla değer döner, RealDictCursor ise
# {"kolon_adi": deger} şeklinde sözlük döner. HTML şablonunda kolon ismiyle
# erişmek (row["sasi_no"] gibi) daha okunaklı olduğu için bunu tercih ettik.

# ---- Ana sayfadaki ÖZET liste tablosu için BEŞ sorgu ---------------------
# Hepsi AYNI kolonları (aynı sırayla) döndürüyor ki tek bir HTML tablo
# şablonu hepsi için de kullanılabilsin: sasi_no, motor_no, carline_adi,
# model_yili, dis_renk, ic_renk, yakit_adi, plaka, fatura_no,
# fatura_tarihi, toplam.

# 1) GENEL ARAMA: tek bir kutuya yazılan metin; şase, motor no, model,
#    dış/iç renk, fatura no ya da plakadan HERHANGİ BİRİYLE eşleşirse
#    sonuca girer (ILIKE = büyük/küçük harf duyarsız, "içerir" araması).
#    ÖĞRENME NOTU: %s yedi kere geçiyor, bu yüzden çağırırken aynı
#    joker'i ([joker]*7) yedi kere parametre olarak veriyoruz.
GENEL_ARAMA_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no,
        c.adi AS carline_adi, a.model_yili,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
        yt.adi AS yakit_adi,
        (
            SELECT p.plaka FROM plakalar p
            WHERE p.arac_id = a.id ORDER BY p.id DESC LIMIT 1
        ) AS plaka,
        af.fatura_no, af.fatura_tarihi, af.toplam
    FROM araclar a
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    LEFT JOIN dis_renkler dr ON dr.id = sor.dis_renk_id
    LEFT JOIN ic_renkler ic ON ic.id = sor.ic_renk_id
    LEFT JOIN yakit_tipleri yt ON yt.id = a.yakit_id
    LEFT JOIN alis_faturalari af ON af.arac_id = a.id
    WHERE
        a.sasi_no ILIKE %s
        OR a.motor_no ILIKE %s
        OR c.adi ILIKE %s
        OR dr.adi ILIKE %s
        OR ic.adi ILIKE %s
        OR af.fatura_no ILIKE %s
        OR EXISTS (
            SELECT 1 FROM plakalar p2
            WHERE p2.arac_id = a.id AND p2.plaka ILIKE %s
        )
    ORDER BY af.fatura_tarihi DESC NULLS LAST
    LIMIT 500
"""

# 2) TARİH ARALIĞI: belirli bir aralıkta FATURASI olan araçlar (özet
#    kartlarına tıklayınca da bu sorgu kullanılıyor, kartların linki
#    /?baslangic=...&bitis=... şeklinde).
TARIH_LISTESI_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no,
        c.adi AS carline_adi, a.model_yili,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
        yt.adi AS yakit_adi,
        (
            SELECT p.plaka FROM plakalar p
            WHERE p.arac_id = a.id ORDER BY p.id DESC LIMIT 1
        ) AS plaka,
        af.fatura_no, af.fatura_tarihi, af.toplam
    FROM alis_faturalari af
    JOIN araclar a ON a.id = af.arac_id
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    LEFT JOIN dis_renkler dr ON dr.id = sor.dis_renk_id
    LEFT JOIN ic_renkler ic ON ic.id = sor.ic_renk_id
    LEFT JOIN yakit_tipleri yt ON yt.id = a.yakit_id
    WHERE af.fatura_tarihi BETWEEN %s AND %s
    ORDER BY af.fatura_tarihi DESC
    LIMIT 500
"""

# 3) TÜM ARAÇLAR: "Toplam Araç" kartına tıklayınca -- hiçbir filtre yok,
#    faturası olmayan araçlar bile (varsa) LEFT JOIN sayesinde görünür.
TUM_ARACLAR_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no,
        c.adi AS carline_adi, a.model_yili,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
        yt.adi AS yakit_adi,
        (
            SELECT p.plaka FROM plakalar p
            WHERE p.arac_id = a.id ORDER BY p.id DESC LIMIT 1
        ) AS plaka,
        af.fatura_no, af.fatura_tarihi, af.toplam
    FROM araclar a
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    LEFT JOIN dis_renkler dr ON dr.id = sor.dis_renk_id
    LEFT JOIN ic_renkler ic ON ic.id = sor.ic_renk_id
    LEFT JOIN yakit_tipleri yt ON yt.id = a.yakit_id
    LEFT JOIN alis_faturalari af ON af.arac_id = a.id
    ORDER BY af.fatura_tarihi DESC NULLS LAST
    LIMIT 500
"""

# 4) GÜMRÜK KAYDI OLAN ARAÇLAR: "Gümrük Kaydı Olan Araç" kartına tıklayınca.
ITHAL_ARACLAR_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no,
        c.adi AS carline_adi, a.model_yili,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
        yt.adi AS yakit_adi,
        (
            SELECT p.plaka FROM plakalar p
            WHERE p.arac_id = a.id ORDER BY p.id DESC LIMIT 1
        ) AS plaka,
        af.fatura_no, af.fatura_tarihi, af.toplam
    FROM araclar a
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    LEFT JOIN dis_renkler dr ON dr.id = sor.dis_renk_id
    LEFT JOIN ic_renkler ic ON ic.id = sor.ic_renk_id
    LEFT JOIN yakit_tipleri yt ON yt.id = a.yakit_id
    LEFT JOIN alis_faturalari af ON af.arac_id = a.id
    WHERE EXISTS (SELECT 1 FROM gumruk_bilgileri g WHERE g.arac_id = a.id)
    ORDER BY af.fatura_tarihi DESC NULLS LAST
    LIMIT 500
"""

# 5) FİLTRE: Model / Dış Renk / Yakıt Tipi comboboxlarına göre (istenilen
#    herhangi bir alt kümesi boş bırakılabilir). ÖĞRENME NOTU: "(%s = ''
#    OR kolon = %s)" deseni, tek bir SABİT SQL metniyle OPSİYONEL filtre
#    yapmamızı sağlıyor -- kutu boşsa (%s = '') o koşul hep DOĞRU olur,
#    yani o alanda hiç filtre uygulanmamış gibi davranır. Bu yüzden her
#    kutu için aynı değeri İKİ KERE parametre olarak veriyoruz.
FILTRE_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no,
        c.adi AS carline_adi, a.model_yili,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
        yt.adi AS yakit_adi,
        (
            SELECT p.plaka FROM plakalar p
            WHERE p.arac_id = a.id ORDER BY p.id DESC LIMIT 1
        ) AS plaka,
        af.fatura_no, af.fatura_tarihi, af.toplam
    FROM araclar a
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    LEFT JOIN dis_renkler dr ON dr.id = sor.dis_renk_id
    LEFT JOIN ic_renkler ic ON ic.id = sor.ic_renk_id
    LEFT JOIN yakit_tipleri yt ON yt.id = a.yakit_id
    LEFT JOIN alis_faturalari af ON af.arac_id = a.id
    WHERE
        (%s = '' OR c.adi = %s)
        AND (%s = '' OR dr.adi = %s)
        AND (%s = '' OR yt.adi = %s)
    ORDER BY af.fatura_tarihi DESC NULLS LAST
    LIMIT 500
"""

# ---- Ana sayfadaki 3 combobox'ı (Model/Dış Renk/Yakıt Tipi) doldurmak
#      için veritabanındaki BENZERSİZ değerleri çeken üç küçük sorgu.
MODEL_SECENEKLERI_SORGUSU = """
    SELECT DISTINCT c.adi AS deger
    FROM araclar a
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    WHERE c.adi IS NOT NULL
    ORDER BY c.adi
"""

RENK_SECENEKLERI_SORGUSU = """
    SELECT DISTINCT dr.adi AS deger
    FROM araclar a
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN dis_renkler dr ON dr.id = sor.dis_renk_id
    WHERE dr.adi IS NOT NULL
    ORDER BY dr.adi
"""

YAKIT_SECENEKLERI_SORGUSU = """
    SELECT DISTINCT yt.adi AS deger
    FROM araclar a
    JOIN yakit_tipleri yt ON yt.id = a.yakit_id
    ORDER BY yt.adi
"""
# UYARI: LIMIT 500 kasıtlı -- geniş bir arama/tarih aralığı binlerce satır
# döndürebileceğinden sayfa yavaşlamasın diye. Sıralama/filtreleme sadece
# ekrandaki (en fazla 500) satır üzerinde çalışır.

# ---- Detay sayfası ("/arac/<sasi_no>") için üç sorgu --------------------
SASI_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no, a.model_yili,
        c.adi AS carline_adi, c.kod AS carline_kod,
        s.kod AS spec_kodu,
        o.no AS ocn_no, o.adi AS ocn_adi,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
        yt.adi AS yakit_adi,
        (
            SELECT string_agg(DISTINCT p.plaka, ', ')
            FROM plakalar p WHERE p.arac_id = a.id
        ) AS plakalar
    FROM araclar a
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    LEFT JOIN ocn o ON o.id = so.ocn_id
    LEFT JOIN dis_renkler dr ON dr.id = sor.dis_renk_id
    LEFT JOIN ic_renkler ic ON ic.id = sor.ic_renk_id
    LEFT JOIN yakit_tipleri yt ON yt.id = a.yakit_id
    WHERE a.sasi_no = %s
"""

SASI_FATURA_SORGUSU = """
    SELECT af.fatura_no, af.fatura_tarihi, b.adi AS bayi_adi,
           af.liste_fiyat, af.indirim, af.indirimli_fiyat,
           af.kdv_orani, af.toplam, af.durum
    FROM alis_faturalari af
    JOIN araclar a ON a.id = af.arac_id
    LEFT JOIN bayiler b ON b.id = af.bayi_id
    WHERE a.sasi_no = %s
    ORDER BY af.fatura_tarihi
"""

SASI_GUMRUK_SORGUSU = """
    SELECT g.talep_tarihi, g.talep_no, g.fatura_tarihi, g.fatura_no, g.gumruk_mudurlugu
    FROM gumruk_bilgileri g
    JOIN araclar a ON a.id = g.arac_id
    WHERE a.sasi_no = %s
"""

# ---- Ana sayfa üstündeki 8 özet kartı için tek sorgu --------------------
# ÖĞRENME NOTU: 6 tanesi (bu_yil...bugun) BETWEEN %s AND %s kullanıyor,
# bu yüzden çağırırken 12 tarih parametresi (6 çift) veriyoruz -- sırası
# ÇOK ÖNEMLİ, aşağıdaki anasayfa() fonksiyonundaki sırayla birebir aynı
# olmalı (yıl, geçen ay, bu ay, bu hafta, dün, bugün).
ISTATISTIK_SORGUSU = """
    SELECT
        (SELECT COUNT(*) FROM araclar) AS toplam_arac,
        (SELECT COUNT(DISTINCT arac_id) FROM gumruk_bilgileri) AS ithal_arac,
        (SELECT COUNT(*) FROM alis_faturalari WHERE fatura_tarihi BETWEEN %s AND %s) AS bu_yil_fatura,
        (SELECT COUNT(*) FROM alis_faturalari WHERE fatura_tarihi BETWEEN %s AND %s) AS gecen_ay_fatura,
        (SELECT COUNT(*) FROM alis_faturalari WHERE fatura_tarihi BETWEEN %s AND %s) AS bu_ay_fatura,
        (SELECT COUNT(*) FROM alis_faturalari WHERE fatura_tarihi BETWEEN %s AND %s) AS bu_hafta_fatura,
        (SELECT COUNT(*) FROM alis_faturalari WHERE fatura_tarihi BETWEEN %s AND %s) AS dun_fatura,
        (SELECT COUNT(*) FROM alis_faturalari WHERE fatura_tarihi BETWEEN %s AND %s) AS bugun_fatura
"""


def _sorgu_calistir(sql, params):
    """Tek bir SELECT çalıştırıp sonucu dict listesi olarak döner.
    Küçük bir yardımcı -- yukarıdaki sorguların hepsi aynı şekilde
    çalıştırıldığı için tekrar yazmamak adına buraya alındı."""
    with db.get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


# ------------------------------------------------------------------
# Ortak stil + ortak sıralama/filtreleme JS
# ------------------------------------------------------------------
# ÖĞRENME NOTU: Aynı CSS ve aynı JS hem ana sayfada hem detay sayfasında
# lazım olduğu için tekrar yazmamak adına ortak bir parça olarak buraya
# alındı ve iki şablonun içine de {{ ORTAK_STIL }} / {{ ORTAK_JS }} gibi
# değil, doğrudan Python string birleştirmesiyle ekleniyor (aşağıda
# ANA_SAYFA = ORTAK_STIL + ... şeklinde).
ORTAK_STIL = """
<style>
  * { box-sizing: border-box; }
  body { font-family: "Segoe UI", Arial, sans-serif; margin: 0; background: #eef1f5; color: #1f2937; }

  .ust-serit {
    background: #041e42;
    color: #fff;
    padding: 16px 28px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .ust-serit h1 { font-size: 18px; margin: 0; font-weight: 600; }
  .ust-serit .alt-yazi { font-size: 12px; color: #9db4d1; margin-top: 2px; }
  .ust-serit a { color: #cfe0ff; text-decoration: none; font-size: 13px; }
  .ust-serit a:hover { text-decoration: underline; }

  .icerik { padding: 20px 28px 40px; }

  /* Özet kartları -- TIKLANABİLİR: her kart bir <a> ile sarmalanıyor. */
  .kart-satiri { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 24px; }
  .kart-link { flex: 1 1 140px; text-decoration: none; color: inherit; display: block; }
  .kart-link:hover .kart { box-shadow: 0 4px 12px rgba(0,0,0,0.15); transform: translateY(-1px); }
  .kart {
    background: #fff;
    border-radius: 8px;
    padding: 14px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border-top: 4px solid #ccc;
    transition: box-shadow 0.1s, transform 0.1s;
    height: 100%;
  }
  .kart .sayi { font-size: 24px; font-weight: 700; line-height: 1.2; }
  .kart .etiket { font-size: 11px; color: #6b7280; margin-top: 4px; }
  .kart.mavi { border-top-color: #2563eb; }
  .kart.mavi .sayi { color: #2563eb; }
  .kart.yesil { border-top-color: #16a34a; }
  .kart.yesil .sayi { color: #16a34a; }
  .kart.turuncu { border-top-color: #ea580c; }
  .kart.turuncu .sayi { color: #ea580c; }
  .kart.mor { border-top-color: #7c3aed; }
  .kart.mor .sayi { color: #7c3aed; }

  h2 { font-size: 15px; margin-top: 30px; color: #111827; }
  .arama-kartlari { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 20px; }
  form.arama-formu {
    background: #fff;
    border-radius: 8px;
    padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    flex: 1 1 320px;
  }
  form.arama-formu b { font-size: 13px; color: #111827; }
  /* ÖNEMLİ: label'a sabit min-width VERİLMİYOR -- "Başlangıç:" ile "Bitiş:"
     farklı uzunlukta oldukları için sabit bir min-width, kısa olan
     etiketin ("Bitiş:") yanında kullanılmayan boş bir alan bırakıyordu
     (kullanıcının ekran görüntüsünde siyah çerçeveyle işaretlediği boşluk).
     Bunun yerine etiket kendi metni kadar yer kaplasın, input'a sadece
     küçük sabit bir boşlukla (margin-right) yapışsın. */
  label { display: inline-block; font-size: 13px; margin-top: 10px; margin-right: 6px; }
  input[type=text], input[type=date] {
    padding: 7px 9px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px;
  }
  button {
    padding: 7px 18px; border: 0; background: #2563eb; color: #fff;
    border-radius: 4px; cursor: pointer; font-size: 13px; margin-top: 10px;
  }
  button:hover { background: #1d4ed8; }

  /* Genel "Ara" kutusu: etiket + metin kutusu + buton aynı satırda,
     metin kutusu (input) kalan tüm genişliği doldursun diye flex ile
     büyütülüyor -- kutu artık "çok ufak" kalmıyor. */
  .genel-arama-satiri { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
  .genel-arama-satiri label { margin-top: 0; margin-right: 0; }
  .genel-arama-satiri input[type=text] { flex: 1 1 240px; min-width: 200px; }
  .genel-arama-satiri button { margin-top: 0; }

  /* Model / Dış Renk / Yakıt Tipi comboboxları -- genel arama kutusunun
     ALTINDA, ince bir çizgiyle ayrılmış ikinci bir satır. Her combobox
     kendi etiketiyle alt alta, satır kendisi yan yana (flex). */
  .combo-satiri {
    display: flex; gap: 14px; flex-wrap: wrap; align-items: flex-end;
    margin-top: 12px; padding-top: 12px; border-top: 1px solid #eef0f2;
  }
  .combo-grubu { display: flex; flex-direction: column; gap: 4px; }
  .combo-grubu label { margin: 0; }
  .combo-grubu select {
    padding: 7px 9px; border: 1px solid #cbd5e1; border-radius: 4px;
    font-size: 13px; min-width: 160px; background: #fff;
  }
  .combo-satiri button { margin-top: 0; }

  /* Tarih aralığı formu: Başlangıç + Bitiş + hızlı butonlar (Bugün/Dün/
     Bu Hafta/Bu Ay/Geçen Ay/Bu Yıl) AYNI SATIRDA -- .tarih-satiri hepsini
     tek bir flex satırına alıyor, butonlar Bitiş kutusunun YANINDA durur
     (altında değil). Dar ekranda flex-wrap sayesinde alta sarkar. */
  .tarih-satiri { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 10px; }
  .tarih-satiri label { margin-top: 0; }
  .tarih-buton-satiri { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 0; margin-left: 6px; }
  .tarih-buton-satiri button { margin-top: 0; }
  .buton-ikincil {
    background: #eef1f5; color: #1f2937; border: 1px solid #cbd5e1;
    padding: 7px 12px; font-size: 12px;
  }
  .buton-ikincil:hover { background: #e2e8f0; }

  .tablo-sarmalayici {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    overflow-x: auto;
    margin-bottom: 24px;
  }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid #eef0f2; padding: 7px 10px; text-align: left; white-space: nowrap; }
  thead tr.baslik-satiri th {
    background: #041e42; color: #fff; cursor: pointer; user-select: none;
    position: sticky; top: 0;
  }
  thead tr.baslik-satiri th:hover { background: #0a2d5e; }
  thead tr.baslik-satiri th::after { content: " ⇅"; opacity: 0.5; font-size: 11px; }
  thead tr.baslik-satiri th[data-siralama="artan"]::after { content: " ▲"; opacity: 1; }
  thead tr.baslik-satiri th[data-siralama="azalan"]::after { content: " ▼"; opacity: 1; }
  thead tr.filtre-satiri th { background: #f3f4f6; padding: 4px 6px; cursor: default; }
  thead tr.filtre-satiri th::after { content: ""; }
  thead tr.filtre-satiri input {
    width: 100%; padding: 5px 6px; border: 1px solid #d1d5db; border-radius: 4px; font-size: 12px;
  }
  tbody tr.veri-satiri { cursor: pointer; }
  tbody tr.veri-satiri:nth-child(even) { background: #fafbfc; }
  tbody tr.veri-satiri:hover { background: #eef4ff; }
  tbody tr.bos-satiri td { color: #9ca3af; text-align: center; padding: 18px; font-style: italic; cursor: default; }
  tbody tr.bos-satiri:hover { background: inherit; }
  td a { color: #2563eb; text-decoration: none; }
  td a:hover { text-decoration: underline; }

  .not-bulundu { color: #b91c1c; }
  .bilgi-notu { color: #6b7280; font-size: 12px; }
  .arac-bilgi-tablosu td:first-child, .arac-bilgi-tablosu th:first-child { font-weight: 600; width: 160px; background: #f8f9fb; }
</style>
"""

ORTAK_JS = """
<script>
// ÖĞRENME NOTU: Bu fonksiyonlar SAYFA YENİDEN YÜKLENMEDEN çalışır --
// veritabanına gitmez, sadece o an ekranda olan <table> satırlarını
// tarayıcının kendi belleğinde yeniden sıralar / gizler.

// Sütun başlığına tıklayınca çağrılır. Tablo "bos" (veri yok, sadece
// placeholder satırı) ise hiçbir şey yapmadan çıkar -- yoksa placeholder
// satırındaki tek hücreye kolon index'iyle erişmeye çalışıp hataya düşer.
function sirala(tabloId, kolonIndex) {
  var tablo = document.getElementById(tabloId);
  if (!tablo) return;
  var tbody = tablo.tBodies[0];
  if (tbody.getAttribute('data-dolu') !== '1') return;

  var satirlar = Array.prototype.slice.call(tbody.querySelectorAll('tr.veri-satiri'));
  var basliklar = tablo.querySelectorAll('thead tr.baslik-satiri th');
  var th = basliklar[kolonIndex];
  var artan = th.getAttribute('data-siralama') !== 'artan';

  satirlar.sort(function (a, b) {
    var av = a.children[kolonIndex].innerText.trim();
    var bv = b.children[kolonIndex].innerText.trim();
    var an = parseFloat(av.replace(/\\./g, '').replace(',', '.'));
    var bn = parseFloat(bv.replace(/\\./g, '').replace(',', '.'));
    var sonuc;
    if (!isNaN(an) && !isNaN(bn) && av !== '-' && bv !== '-') {
      sonuc = an - bn;
    } else {
      sonuc = av.localeCompare(bv, 'tr');
    }
    return artan ? sonuc : -sonuc;
  });

  satirlar.forEach(function (satir) { tbody.appendChild(satir); });
  basliklar.forEach(function (el) { el.removeAttribute('data-siralama'); });
  th.setAttribute('data-siralama', artan ? 'artan' : 'azalan');
}

// Filtre kutusuna yazdıkça çağrılır. Aynı şekilde tablo "bos" ise çıkar.
function filtrele(tabloId) {
  var tablo = document.getElementById(tabloId);
  if (!tablo) return;
  var tbody = tablo.tBodies[0];
  if (tbody.getAttribute('data-dolu') !== '1') return;

  var girdiler = tablo.querySelectorAll('thead tr.filtre-satiri input');
  var satirlar = tbody.querySelectorAll('tr.veri-satiri');

  satirlar.forEach(function (satir) {
    var goster = true;
    girdiler.forEach(function (girdi, i) {
      var deger = girdi.value.trim().toLocaleLowerCase('tr');
      if (deger && satir.children[i]) {
        var hucreMetni = satir.children[i].innerText.toLocaleLowerCase('tr');
        if (hucreMetni.indexOf(deger) === -1) goster = false;
      }
    });
    satir.style.display = goster ? '' : 'none';
  });
}

// Satıra tıklanınca detay sayfasını KÜÇÜK, AYRI BİR PENCEREDE (popup) aç.
// ÖNEMLİ: window.open'a "_blank" yerine burada bir PENCERE ADI ("aracDetay")
// ve genişlik/yükseklik gibi "pencere özellikleri" veriyoruz -- tarayıcılar
// bu durumda YENİ SEKME değil, gerçek küçük bir pencere açar. Ana sayfa
// (liste + arama sonucu) olduğu sekmede hiç değişmeden kalır. Aynı isimde
// pencere zaten açıksa (başka bir satıra daha önce tıklanmışsa) onun
// içeriğini değiştirir, yeni yeni pencere açıp ekranı doldurmaz.
function detayPenceresiAc(url) {
  var genislik = 950, yukseklik = 750;
  var sol = Math.max(0, (window.screen.width - genislik) / 2);
  var ust = Math.max(0, (window.screen.height - yukseklik) / 2);
  window.open(
    url,
    'aracDetay',
    'width=' + genislik + ',height=' + yukseklik + ',left=' + sol + ',top=' + ust +
    ',resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=no,status=no'
  );
}

// Satırın onclick'inden çağrılır. Satırın içindeki bir linke tıklandıysa
// (o linkin kendi onclick'i zaten detayPenceresiAc'ı çağırıp false
// dönüyor) burada tekrar açmaya çalışmayalım diye kontrol ediyoruz.
function satiraGit(tr, url) {
  if (event.target.tagName === 'A') return;
  detayPenceresiAc(url);
}

// "Dün / Bu Ay / Geçen Ay / Bu Yıl" butonlarına basınca çağrılır.
// Tarayıcıda (JS ile) tarih hesaplayıp başlangıç/bitiş kutularını
// dolduruyor ve tarih arama formunu OTOMATIK gönderiyor (sanki kullanıcı
// tarihleri kendisi yazıp "Ara"ya basmış gibi).
function tarihAyarla(tur) {
  var bugun = new Date();
  var yil = bugun.getFullYear();
  var ay = bugun.getMonth(); // 0 = Ocak

  function ikiBasamak(sayi) { return (sayi < 10 ? '0' : '') + sayi; }
  function formatla(d) { return d.getFullYear() + '-' + ikiBasamak(d.getMonth() + 1) + '-' + ikiBasamak(d.getDate()); }

  var baslangic, bitis;
  if (tur === 'bugun') {
    baslangic = bitis = formatla(bugun);
  } else if (tur === 'dun') {
    var dun = new Date(yil, ay, bugun.getDate() - 1);
    baslangic = bitis = formatla(dun);
  } else if (tur === 'bu-hafta') {
    // Pazartesi -- Pazar. getDay(): 0=Pazar, 1=Pazartesi, ... 6=Cumartesi.
    // Pazartesi'ye kaç gün geriye gidileceğini hesaplıyoruz (Pazar için 6).
    var gun = bugun.getDay();
    var pazartesiyeFark = (gun === 0) ? 6 : (gun - 1);
    var pazartesi = new Date(yil, ay, bugun.getDate() - pazartesiyeFark);
    var pazar = new Date(pazartesi.getFullYear(), pazartesi.getMonth(), pazartesi.getDate() + 6);
    baslangic = formatla(pazartesi);
    bitis = formatla(pazar);
  } else if (tur === 'bu-ay') {
    baslangic = formatla(new Date(yil, ay, 1));
    bitis = formatla(new Date(yil, ay + 1, 0)); // ayın son günü (bir sonraki ayın 0. günü)
  } else if (tur === 'gecen-ay') {
    baslangic = formatla(new Date(yil, ay - 1, 1));
    bitis = formatla(new Date(yil, ay, 0));
  } else if (tur === 'bu-yil') {
    baslangic = formatla(new Date(yil, 0, 1));
    bitis = formatla(new Date(yil, 11, 31));
  } else {
    return;
  }

  document.getElementById('baslangic-girdi').value = baslangic;
  document.getElementById('bitis-girdi').value = bitis;
  document.getElementById('tarih-arama-formu').submit();
}
</script>
"""


# ------------------------------------------------------------------
# Ana sayfa şablonu -- her zaman görünen özet liste tablosu
# ------------------------------------------------------------------
ANA_SAYFA = """
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>ERK Araç Database - Görüntüleyici</title>
""" + ORTAK_STIL + """
</head>
<body>

<div class="ust-serit">
  <div>
    <h1>ERK Araç Database</h1>
    <div class="alt-yazi">Sadece görüntüleme amaçlı -- veri eklemez/değiştirmez.</div>
  </div>
</div>

<div class="icerik">

  <div class="kart-satiri">
    <a class="kart-link" href="/?gorunum=tum">
      <div class="kart mavi">
        <div class="sayi">{{ istatistik.toplam_arac }}</div>
        <div class="etiket">TOPLAM ARAÇ</div>
      </div>
    </a>
    <a class="kart-link" href="/?gorunum=ithal">
      <div class="kart yesil">
        <div class="sayi">{{ istatistik.ithal_arac }}</div>
        <div class="etiket">GÜMRÜK KAYDI OLAN ARAÇ</div>
      </div>
    </a>
    <a class="kart-link" href="/?baslangic={{ kart_tarihleri.bu_yil[0] }}&bitis={{ kart_tarihleri.bu_yil[1] }}">
      <div class="kart turuncu">
        <div class="sayi">{{ istatistik.bu_yil_fatura }}</div>
        <div class="etiket">BU YIL EKLENEN FATURA</div>
      </div>
    </a>
    <a class="kart-link" href="/?baslangic={{ kart_tarihleri.gecen_ay[0] }}&bitis={{ kart_tarihleri.gecen_ay[1] }}">
      <div class="kart mor">
        <div class="sayi">{{ istatistik.gecen_ay_fatura }}</div>
        <div class="etiket">GEÇEN AY EKLENEN FATURA</div>
      </div>
    </a>
    <a class="kart-link" href="/?baslangic={{ kart_tarihleri.bu_ay[0] }}&bitis={{ kart_tarihleri.bu_ay[1] }}">
      <div class="kart mavi">
        <div class="sayi">{{ istatistik.bu_ay_fatura }}</div>
        <div class="etiket">BU AY EKLENEN FATURA</div>
      </div>
    </a>
    <a class="kart-link" href="/?baslangic={{ kart_tarihleri.bu_hafta[0] }}&bitis={{ kart_tarihleri.bu_hafta[1] }}">
      <div class="kart yesil">
        <div class="sayi">{{ istatistik.bu_hafta_fatura }}</div>
        <div class="etiket">BU HAFTA EKLENEN FATURA</div>
      </div>
    </a>
    <a class="kart-link" href="/?baslangic={{ kart_tarihleri.dun[0] }}&bitis={{ kart_tarihleri.dun[1] }}">
      <div class="kart turuncu">
        <div class="sayi">{{ istatistik.dun_fatura }}</div>
        <div class="etiket">DÜN EKLENEN FATURA</div>
      </div>
    </a>
    <a class="kart-link" href="/?baslangic={{ kart_tarihleri.bugun[0] }}&bitis={{ kart_tarihleri.bugun[1] }}">
      <div class="kart mor">
        <div class="sayi">{{ istatistik.bugun_fatura }}</div>
        <div class="etiket">BUGÜN EKLENEN FATURA</div>
      </div>
    </a>
  </div>

  <div class="arama-kartlari">
    <form class="arama-formu" method="get">
      <b>Ara / Filtrele</b> <span class="bilgi-notu">(şase, motor no, model, renk, plaka, fatura no; ya da alttan model/renk/yakıt tipi seçerek)</span><br>
      <div class="genel-arama-satiri">
        <label>Ne arıyorsun:</label>
        <input type="text" name="q" value="{{ arama_metni }}" placeholder="örn. KMHM341..., 34 ABC 123, kırmızı, Tucson...">
        <button type="submit" name="eylem" value="ara">Ara</button>
      </div>
      <div class="combo-satiri">
        <div class="combo-grubu">
          <label>Model</label>
          <select name="model">
            <option value="">Tümü</option>
            {% for m in model_secenekleri %}
            <option value="{{ m }}" {{ "selected" if model_secili == m else "" }}>{{ m }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="combo-grubu">
          <label>Dış Renk</label>
          <select name="renk">
            <option value="">Tümü</option>
            {% for r in renk_secenekleri %}
            <option value="{{ r }}" {{ "selected" if renk_secili == r else "" }}>{{ r }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="combo-grubu">
          <label>Yakıt Tipi</label>
          <select name="yakit">
            <option value="">Tümü</option>
            {% for y in yakit_secenekleri %}
            <option value="{{ y }}" {{ "selected" if yakit_secili == y else "" }}>{{ y }}</option>
            {% endfor %}
          </select>
        </div>
        <button type="submit" name="eylem" value="filtrele">Filtrele</button>
      </div>
    </form>

    <form class="arama-formu" method="get" id="tarih-arama-formu">
      <b>Tarih aralığına göre ara</b><br>
      <div class="tarih-satiri">
        <label>Başlangıç:</label>
        <input type="date" name="baslangic" id="baslangic-girdi" value="{{ baslangic_deger }}">
        <label>Bitiş:</label>
        <input type="date" name="bitis" id="bitis-girdi" value="{{ bitis_deger }}">
        <div class="tarih-buton-satiri">
          <button type="submit">Ara</button>
          <button type="button" class="buton-ikincil" onclick="tarihAyarla('bugun')">Bugün</button>
          <button type="button" class="buton-ikincil" onclick="tarihAyarla('dun')">Dün</button>
          <button type="button" class="buton-ikincil" onclick="tarihAyarla('bu-hafta')">Bu Hafta</button>
          <button type="button" class="buton-ikincil" onclick="tarihAyarla('bu-ay')">Bu Ay</button>
          <button type="button" class="buton-ikincil" onclick="tarihAyarla('gecen-ay')">Geçen Ay</button>
          <button type="button" class="buton-ikincil" onclick="tarihAyarla('bu-yil')">Bu Yıl</button>
        </div>
      </div>
    </form>
  </div>

  <h2>{{ baslik_metni }} ({{ sonuclar|length }} kayıt{{ ", en fazla 500 gösteriliyor" if sonuclar|length >= 500 else "" }})</h2>
  <p class="bilgi-notu">Bir satıra tıklayınca o aracın tüm detayları (özellikler, faturalar, gümrük bilgisi) küçük, ayrı bir PENCEREDE açılır -- bu sayfa olduğu gibi kalır.</p>

  <div class="tablo-sarmalayici">
  <table id="tablo-sonuclar">
    <thead>
      <tr class="baslik-satiri" onclick="event.target.tagName === 'TH' && sirala('tablo-sonuclar', Array.from(event.target.parentNode.children).indexOf(event.target))">
        <th>Şase</th><th>Motor No</th><th>Model</th><th>Model Yılı</th><th>Dış Renk</th><th>İç Renk</th><th>Yakıt</th><th>Plaka</th><th>Fatura No</th><th>Fatura Tarihi</th><th>Toplam</th>
      </tr>
      <tr class="filtre-satiri">
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-sonuclar')" placeholder="ara..."></th>
      </tr>
    </thead>
    <tbody data-dolu="{{ '1' if sonuclar else '0' }}">
    {% if sonuclar %}
      {% for r in sonuclar %}
      <tr class="veri-satiri" onclick="satiraGit(this, '/arac/{{ r.sasi_no }}')">
        <td><a href="/arac/{{ r.sasi_no }}" onclick="detayPenceresiAc('/arac/{{ r.sasi_no }}'); return false;">{{ r.sasi_no }}</a></td>
        <td>{{ r.motor_no or "-" }}</td>
        <td>{{ r.carline_adi or "-" }}</td>
        <td>{{ r.model_yili or "-" }}</td>
        <td>{{ r.dis_renk or "-" }}</td>
        <td>{{ r.ic_renk or "-" }}</td>
        <td>{{ r.yakit_adi or "-" }}</td>
        <td>{{ r.plaka or "-" }}</td>
        <td>{{ r.fatura_no or "-" }}</td>
        <td>{{ r.fatura_tarihi or "-" }}</td>
        <td>{{ "%.2f"|format(r.toplam) if r.toplam is not none else "-" }}</td>
      </tr>
      {% endfor %}
    {% else %}
      <tr class="bos-satiri">
        <td colspan="11">
          {% if arama_yapildi %}
            Bu aramayla eşleşen kayıt bulunamadı.
          {% else %}
            Henüz arama yapmadınız -- yukarıdan bir şey arayın, tarih seçin ya da bir karta tıklayın.
          {% endif %}
        </td>
      </tr>
    {% endif %}
    </tbody>
  </table>
  </div>

</div>
""" + ORTAK_JS + """
</body>
</html>
"""


# ------------------------------------------------------------------
# Detay sayfası şablonu -- "/arac/<sasi_no>"
# ------------------------------------------------------------------
DETAY_SAYFA = """
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>{{ sasi_no }} - Araç Detayı</title>
""" + ORTAK_STIL + """
</head>
<body>

<div class="ust-serit">
  <div>
    <h1>Araç Detayı: {{ sasi_no }}</h1>
    <div class="alt-yazi">Sadece görüntüleme amaçlı -- veri eklemez/değiştirmez.</div>
  </div>
  <a href="/">&larr; Listeye dön</a>
</div>

<div class="icerik">

{% if arac %}
  <h2>Araç bilgisi</h2>
  <div class="tablo-sarmalayici">
  <table class="arac-bilgi-tablosu">
    <tr><th>Şasi</th><td>{{ arac.sasi_no }}</td></tr>
    <tr><th>Motor No</th><td>{{ arac.motor_no or "-" }}</td></tr>
    <tr><th>Model Yılı</th><td>{{ arac.model_yili or "-" }}</td></tr>
    <tr><th>Model</th><td>{{ arac.carline_adi or "-" }} ({{ arac.carline_kod or "-" }})</td></tr>
    <tr><th>Spec Kodu</th><td>{{ arac.spec_kodu or "-" }}</td></tr>
    <tr><th>Donanım (OCN)</th><td>{{ arac.ocn_adi or "-" }} ({{ arac.ocn_no or "-" }})</td></tr>
    <tr><th>Dış Renk</th><td>{{ arac.dis_renk or "-" }}</td></tr>
    <tr><th>İç Renk</th><td>{{ arac.ic_renk or "-" }}</td></tr>
    <tr><th>Yakıt Tipi</th><td>{{ arac.yakit_adi or "-" }} <span class="bilgi-notu">(motor no'nun ilk harfinden tahmin)</span></td></tr>
    <tr><th>Plaka(lar)</th><td>{{ arac.plakalar or "-" }}</td></tr>
  </table>
  </div>

  <h2>Alış faturaları</h2>
  <div class="tablo-sarmalayici">
  <table id="tablo-fatura">
    <thead>
      <tr class="baslik-satiri" onclick="event.target.tagName === 'TH' && sirala('tablo-fatura', Array.from(event.target.parentNode.children).indexOf(event.target))">
        <th>Fatura No</th><th>Tarih</th><th>Bayi</th><th>Liste Fiyat</th><th>İndirim</th><th>İndirimli Fiyat</th><th>KDV %</th><th>Toplam</th><th>Durum</th>
      </tr>
      <tr class="filtre-satiri">
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-fatura')" placeholder="ara..."></th>
      </tr>
    </thead>
    <tbody data-dolu="{{ '1' if faturalar else '0' }}">
    {% if faturalar %}
      {% for f in faturalar %}
      <tr class="veri-satiri">
        <td>{{ f.fatura_no or "-" }}</td>
        <td>{{ f.fatura_tarihi or "-" }}</td>
        <td>{{ f.bayi_adi or "-" }}</td>
        <td>{{ "%.2f"|format(f.liste_fiyat) if f.liste_fiyat is not none else "-" }}</td>
        <td>{{ "%.2f"|format(f.indirim) if f.indirim is not none else "-" }}</td>
        <td>{{ "%.2f"|format(f.indirimli_fiyat) if f.indirimli_fiyat is not none else "-" }}</td>
        <td>{{ f.kdv_orani if f.kdv_orani is not none else "-" }}</td>
        <td>{{ "%.2f"|format(f.toplam) if f.toplam is not none else "-" }}</td>
        <td>{{ f.durum or "-" }}</td>
      </tr>
      {% endfor %}
    {% else %}
      <tr class="bos-satiri"><td colspan="9">Fatura bulunamadı.</td></tr>
    {% endif %}
    </tbody>
  </table>
  </div>

  <h2>Gümrük bilgisi</h2>
  <div class="tablo-sarmalayici">
  <table id="tablo-gumruk">
    <thead>
      <tr class="baslik-satiri" onclick="event.target.tagName === 'TH' && sirala('tablo-gumruk', Array.from(event.target.parentNode.children).indexOf(event.target))">
        <th>Talep Tarihi</th><th>Talep No</th><th>Fatura Tarihi</th><th>Fatura No</th><th>Gümrük Müdürlüğü</th>
      </tr>
      <tr class="filtre-satiri">
        <th><input type="text" oninput="filtrele('tablo-gumruk')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-gumruk')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-gumruk')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-gumruk')" placeholder="ara..."></th>
        <th><input type="text" oninput="filtrele('tablo-gumruk')" placeholder="ara..."></th>
      </tr>
    </thead>
    <tbody data-dolu="{{ '1' if gumruk else '0' }}">
    {% if gumruk %}
      {% for g in gumruk %}
      <tr class="veri-satiri">
        <td>{{ g.talep_tarihi or "-" }}</td>
        <td>{{ g.talep_no or "-" }}</td>
        <td>{{ g.fatura_tarihi or "-" }}</td>
        <td>{{ g.fatura_no or "-" }}</td>
        <td>{{ g.gumruk_mudurlugu or "-" }}</td>
      </tr>
      {% endfor %}
    {% else %}
      <tr class="bos-satiri"><td colspan="5">Gümrük kaydı bulunamadı.</td></tr>
    {% endif %}
    </tbody>
  </table>
  </div>
{% else %}
  <p class="not-bulundu">"{{ sasi_no }}" şasi numarasıyla bir araç bulunamadı.</p>
{% endif %}

</div>
""" + ORTAK_JS + """
</body>
</html>
"""


@app.route("/")
def anasayfa():
    """Ana sayfa: 8 tıklanabilir özet kartı + genel arama kutusu + Model/
    Dış Renk/Yakıt Tipi comboboxları + tarih aralığı arama formu -- hepsi
    AYNI özet liste tablosunu doldurur.

    ÖNCELİK SIRASI (hangi arama önce kontrol edilir):
      1) ?gorunum=tum       -> tüm araçlar (Toplam Araç kartı)
      2) ?gorunum=ithal     -> gümrük kaydı olan araçlar (o kart)
      3) ?eylem=filtrele    -> Model/Dış Renk/Yakıt Tipi comboboxları
                               (üçü de boşsa bile "Filtrele" basıldıysa
                               bu dala girer, sonuç tüm araçlar olur)
      4) ?q=...             -> genel arama (şase/motor/model/renk/plaka/fatura)
      5) ?baslangic=&bitis= -> tarih aralığı (diğer 6 kart da buraya düşer)
      6) hiçbiri yoksa      -> varsayılan: bu ayı otomatik göster

    ÖĞRENME NOTU (varsayılan tarih): Tarih kutuları hiçbir zaman boş
    görünmesin diye (ve sayfa ilk açıldığında hemen işe yarasın diye)
    parametre hiç verilmemişse varsayılan olarak İÇİNDE BULUNULAN AYIN
    ilk günü / son günü kullanılıyor."""
    bugun = dt.date.today()
    dun = bugun - dt.timedelta(days=1)
    hafta_baslangic = bugun - dt.timedelta(days=bugun.weekday())  # Pazartesi
    hafta_bitis = hafta_baslangic + dt.timedelta(days=6)  # Pazar

    ay_baslangic = bugun.replace(day=1)
    ay_bitis = bugun.replace(day=calendar.monthrange(bugun.year, bugun.month)[1])

    if ay_baslangic.month == 1:
        gecen_ay_baslangic = dt.date(ay_baslangic.year - 1, 12, 1)
    else:
        gecen_ay_baslangic = dt.date(ay_baslangic.year, ay_baslangic.month - 1, 1)
    gecen_ay_bitis = gecen_ay_baslangic.replace(
        day=calendar.monthrange(gecen_ay_baslangic.year, gecen_ay_baslangic.month)[1]
    )

    yil_baslangic = dt.date(bugun.year, 1, 1)
    yil_bitis = dt.date(bugun.year, 12, 31)

    # Kartlara tıklayınca gidilecek linkler için tarihleri metne çeviriyoruz.
    kart_tarihleri = {
        "bu_yil": (yil_baslangic.isoformat(), yil_bitis.isoformat()),
        "gecen_ay": (gecen_ay_baslangic.isoformat(), gecen_ay_bitis.isoformat()),
        "bu_ay": (ay_baslangic.isoformat(), ay_bitis.isoformat()),
        "bu_hafta": (hafta_baslangic.isoformat(), hafta_bitis.isoformat()),
        "dun": (dun.isoformat(), dun.isoformat()),
        "bugun": (bugun.isoformat(), bugun.isoformat()),
    }

    istatistik = _sorgu_calistir(ISTATISTIK_SORGUSU, [
        yil_baslangic, yil_bitis,
        gecen_ay_baslangic, gecen_ay_bitis,
        ay_baslangic, ay_bitis,
        hafta_baslangic, hafta_bitis,
        dun, dun,
        bugun, bugun,
    ])[0]

    arama_metni = request.args.get("q", "").strip()
    baslangic_deger = request.args.get("baslangic", "").strip()
    bitis_deger = request.args.get("bitis", "").strip()
    gorunum = request.args.get("gorunum", "").strip()
    eylem = request.args.get("eylem", "").strip()
    model_secili = request.args.get("model", "").strip()
    renk_secili = request.args.get("renk", "").strip()
    yakit_secili = request.args.get("yakit", "").strip()

    # Model/Dış Renk/Yakıt Tipi comboboxlarını dolduracak benzersiz
    # değerler -- HER istekte çekiliyor (sayfa yenilendiğinde combobox
    # seçenekleri güncel kalsın diye), veri az olduğu için (birkaç bin
    # araç) performans sorunu yaratmaz.
    model_secenekleri = [r["deger"] for r in _sorgu_calistir(MODEL_SECENEKLERI_SORGUSU, [])]
    renk_secenekleri = [r["deger"] for r in _sorgu_calistir(RENK_SECENEKLERI_SORGUSU, [])]
    yakit_secenekleri = [r["deger"] for r in _sorgu_calistir(YAKIT_SECENEKLERI_SORGUSU, [])]

    hicbir_parametre_yok = (
        not arama_metni and not baslangic_deger and not bitis_deger
        and not gorunum and not eylem
        and not model_secili and not renk_secili and not yakit_secili
    )

    # Tarih kutucukları HER ZAMAN dolu görünsün -- kullanıcı henüz kendi
    # tarihini girmediyse kutularda bu ayın tarihlerini GÖSTERİYORUZ
    # (bu değişkenler sadece HTML'e gidiyor, arama mantığını etkilemiyor).
    if not baslangic_deger and not bitis_deger:
        baslangic_gosterim = ay_baslangic.isoformat()
        bitis_gosterim = ay_bitis.isoformat()
    else:
        baslangic_gosterim = baslangic_deger
        bitis_gosterim = bitis_deger

    sonuclar = []
    arama_yapildi = False
    baslik_metni = "Araç listesi"

    if gorunum == "tum":
        arama_yapildi = True
        sonuclar = _sorgu_calistir(TUM_ARACLAR_SORGUSU, [])
        baslik_metni = "Tüm araçlar"
    elif gorunum == "ithal":
        arama_yapildi = True
        sonuclar = _sorgu_calistir(ITHAL_ARACLAR_SORGUSU, [])
        baslik_metni = "Gümrük kaydı olan araçlar"
    elif eylem == "filtrele":
        arama_yapildi = True
        sonuclar = _sorgu_calistir(FILTRE_SORGUSU, [
            model_secili, model_secili,
            renk_secili, renk_secili,
            yakit_secili, yakit_secili,
        ])
        parcalar = []
        if model_secili:
            parcalar.append("Model: %s" % model_secili)
        if renk_secili:
            parcalar.append("Dış Renk: %s" % renk_secili)
        if yakit_secili:
            parcalar.append("Yakıt: %s" % yakit_secili)
        baslik_metni = "Filtre sonucu (%s)" % ", ".join(parcalar) if parcalar else "Tüm araçlar"
    elif arama_metni:
        arama_yapildi = True
        joker = "%" + arama_metni + "%"
        sonuclar = _sorgu_calistir(GENEL_ARAMA_SORGUSU, [joker] * 7)
        baslik_metni = '"%s" için arama sonucu' % arama_metni
    elif baslangic_deger and bitis_deger:
        try:
            b = dt.datetime.strptime(baslangic_deger, "%Y-%m-%d").date()
            e = dt.datetime.strptime(bitis_deger, "%Y-%m-%d").date()
            arama_yapildi = True
            sonuclar = _sorgu_calistir(TARIH_LISTESI_SORGUSU, [b, e])
            baslik_metni = "%s - %s arası" % (baslangic_deger, bitis_deger)
        except ValueError:
            pass  # geçersiz tarih girildiyse sessizce boş sonuç göster
    elif hicbir_parametre_yok:
        # Sayfa hiç parametresiz ilk açıldığında: otomatik olarak BU AYI
        # göster (boş "araç listesi" yerine hemen işe yarar bir görünüm).
        arama_yapildi = True
        sonuclar = _sorgu_calistir(TARIH_LISTESI_SORGUSU, [ay_baslangic, ay_bitis])
        baslik_metni = "Bu ay"

    return render_template_string(
        ANA_SAYFA,
        istatistik=istatistik,
        kart_tarihleri=kart_tarihleri,
        arama_metni=arama_metni,
        baslangic_deger=baslangic_gosterim,
        bitis_deger=bitis_gosterim,
        sonuclar=sonuclar,
        arama_yapildi=arama_yapildi,
        baslik_metni=baslik_metni,
        model_secenekleri=model_secenekleri,
        renk_secenekleri=renk_secenekleri,
        yakit_secenekleri=yakit_secenekleri,
        model_secili=model_secili,
        renk_secili=renk_secili,
        yakit_secili=yakit_secili,
    )


@app.route("/arac/<sasi_no>")
def arac_detay(sasi_no):
    """Detay sayfası: tek bir aracın TÜM bilgileri (özellikler, faturalar,
    gümrük bilgisi). Ana sayfadaki listede bir satıra tıklanınca buraya
    gelinir -- URL'nin sonunda şase numarası olur (örn. /arac/KMHM...)."""
    sonuc = _sorgu_calistir(SASI_SORGUSU, [sasi_no])
    arac = sonuc[0] if sonuc else None

    faturalar = []
    gumruk = []
    if arac:
        faturalar = _sorgu_calistir(SASI_FATURA_SORGUSU, [sasi_no])
        gumruk = _sorgu_calistir(SASI_GUMRUK_SORGUSU, [sasi_no])

    return render_template_string(
        DETAY_SAYFA,
        sasi_no=sasi_no,
        arac=arac,
        faturalar=faturalar,
        gumruk=gumruk,
    )


if __name__ == "__main__":
    # host="127.0.0.1": SADECE bu bilgisayardan erişilebilir, ağdaki başka
    # bir cihazdan (örn. telefon) açılamaz -- bilerek böyle, çünkü içeride
    # fiyat/fatura gibi hassas veri var. Ağ genelinde erişim istersen
    # host="0.0.0.0" yapman gerekir ama bunu bilerek ve güvenlik riskini
    # göze alarak yap.
    print("Tarayıcıda şu adresi aç: http://localhost:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)

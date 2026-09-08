"""
ERK Araç Database - Görüntüleyici

ÖNEMLİ (2026-09-08'de değişti): Bu dosya artık TAMAMEN salt-okunur değil.
Üst barda bir "Veri Çek" butonu var -- bu, src/etl.py'deki run_range()
fonksiyonunu (yani normalde "python -m src.etl BAŞLANGIÇ BİTİŞ" ile elle
çalıştırılan DMS çekimini) bir arka plan thread'inde tetikliyor. Tablo
görünümlerinin kendisi hâlâ salt-okunur (SELECT dışında bir şey yapmazlar).

Çalıştırma:
    python -m src.viewer
    (veya proje köşesindeki goruntule.bat'a çift tıkla)

Sonra tarayıcıda: http://localhost:5050

ÖĞRENME NOTU (Flask): Flask, Python ile web sayfası/servis yazmaya yarayan
küçük bir kütüphane. @app.route("/") gibi bir "dekoratör" (fonksiyonun
üstündeki @...), o fonksiyonu belirli bir web adresine (URL) bağlar --
tarayıcıda o adrese gidildiğinde o fonksiyon çalışır ve döndürdüğü HTML
tarayıcıda gösterilir.

SAYFA YAPISI (7. tasarım):
  0) Üst bar + özet kartlar + Ara/Filtrele kutusu SABİT (position:
     sticky, .sabit-ust) -- aşağı kaydırınca tablo altta kayar, üst kısım
     YERİNDE kalır (2026-09-08: "aşağı inince neyin ne olduğu belli
     olmuyordu" diye eklendi). ÖNEMLİ SINIR: bu sadece ÜST BARDA çalışıyor
     -- TABLONUN KENDİ başlığı (thead) SABİT DEĞİL, kaydırınca sayfayla
     birlikte kayıp gözden kaybolur. Bu bilinçli bir tercih: tablo
     `.tablo-sarmalayici` içinde ve o kutuda (geniş tabloyu dar ekranda
     yatay kaydırabilmek için) "overflow-x: auto" var -- Chrome'da (canlı
     testle doğrulandı, CSS Overflow spesifikasyonu gereği TÜM
     tarayıcılarda) bu, position:sticky'yi kutunun İÇİNDE hapsediyor ve
     sticky satırlar veri satırlarının ÜSTÜNE BİNİYOR ("1 kayıt var ama
     görünmüyor" gibi ciddi bir görsel hataya yol açtı, "overflow-y: clip"
     ile atlatma denendi ama Chrome bunu "hidden" ile aynı ele alıyor,
     çözmedi) -- bu yüzden tablo başlığını sabitleme fikri TAMAMEN GERİ
     ALINDI, sadece üst bar sabit kalıyor. Üst barda ayrıca bir "Veri Çek"
     formu var (Başlangıç/Bitiş tarihi + buton) -- src/etl.py'deki
     run_range()'i (28 günlük otomatik parçalama zaten orada var, burada
     TEKRAR yazılmadı) arka planda bir thread'de çalıştırır, sonucu (kaç
     fatura eklendi/atlandı) birkaç saniyede bir sorgulanıp (polling) üst
     barda gösterilir.
  1) Ana sayfa ("/"): üstte 8 tane TIKLANABİLİR özet kartı (Toplam Araç,
     Gümrük Kaydı Olan Araç, Bu Yıl/Geçen Ay/Bu Ay/Bu Hafta/Dün/Bugün
     eklenen fatura sayısı). Bir karta tıklayınca alttaki tablo o karta
     göre otomatik filtrelenir (sayfa "/" adresine ilgili ?baslangic=...
     &bitis=... ya da ?gorunum=... parametreleriyle gider).
     Altında TEK bir kutu/form var (2026-09-08, kısa ömürlü bir ara
     tasarım denemesinden sonra: önce Ara/Filtrele/Tarih üç ayrı kutuya
     bölünmüştü, ama "hepsinde ayrı bir gönder butonu olmasına gerek yok,
     bir tane yeterli" diye TEK kutuya/forma/butona geri BİRLEŞTİRİLDİ --
     "Filtrele" ve "Tarih aralığı"nın kendi ayrı submit butonları
     KALKTI). Kutunun içinde üç satır var, aralarında ince bir çizgi:
       a) GENEL bir arama satırı: şase, motor no, model, renk, plaka,
          fatura no HANGİSİYLE eşleşirse eşleşsin sonuç getirir (tek tek
          ayrı arama kutuları yerine TEK bir "ara" kutusu).
       b) Model / Dış Renk / Yakıt Tipi seçilebilen ÜÇ combobox --
          veritabanındaki BENZERSİZ değerlerle dolduruluyor.
       c) Tarih aralığı: Başlangıç/Bitiş + Bitiş kutusunun YANINDA
          (altında değil) Bugün/Dün/Bu Hafta/Bu Ay/Geçen Ay/Bu Yıl hızlı
          butonları.
     En altta TEK bir "Ara" butonu + yanında tüm alanları sıfırlayıp
     "/" adresine (varsayılan görünüme) dönen bir "Temizle" linki.
     ÖNCELİK SIRASI (backend'de anasayfa() route'unda, hepsi aynı formda
     olduğu için AYNI ANDA birden fazla alan doldurulabilir -- bu durumda
     hepsi BİRLİKTE VE mantığıyla birleştirilmiyor, şu öncelik sırasındaki
     İLK dolu olan kullanılıyor): combobox seçimi (model/renk/yakıt) >
     genel arama metni (q) > tarih aralığı (baslangic/bitis). Örn. hem
     bir Model seçilip hem de arama kutusuna bir şey yazılırsa, SADECE
     Model filtresi uygulanır -- bu, üç kutu ayrıyken de zaten böyleydi
     (eskiden "eylem" parametresiyle hangi butona basıldığı ayırt
     ediliyordu, tek buton kalınca bunun yerine doğrudan hangi alan(lar)ın
     dolu olduğuna bakılıyor, davranış DEĞİŞMEDİ).
     Sonuç HER ZAMAN tek bir listeleme tablosunda gösterilir (şase, motor
     no, model, renkler, YAKIT TİPİ, plaka, fatura no/tarihi, toplam gibi
     ÖZET bilgiler). Bu tablo, sonuç bulunamadığında bile sütun
     başlıklarıyla birlikte RENDER EDİLİR -- boş diye tablonun kendisi
     kaybolmaz, sadece gövdede "kayıt yok" yazan bir satır görünür (bu,
     yukarıdaki 0. maddedeki kaydırma/sabitlik konusundan AYRI bir şey).
     Sütun başlıklarının
     altındaki "Filtrele ▾" butonuna tıklayınca EXCEL BENZERİ bir filtre
     kutusu açılır (o kolonda o an görünen BENZERSİZ değerler onay
     kutularıyla listelenir, birden fazlası işaretlenebilir, üstte küçük
     bir arama kutusuyla liste daraltılabilir) -- bu tamamen tarayıcıda
     (JS ile) çalışır, veritabanına gitmez, sadece ekrandaki (en fazla
     500) satırı süzer. Bu mantık ORTAK_JS/ORTAK_STIL içinde -- yeni bir
     tablo eklerken (bkz. sablonlar/basit-goruntuleyici/) aynen kopyalanır.
  2) Bir satıra tıklanınca ayrı bir DETAY sayfası ("/arac/<sasi_no>")
     KÜÇÜK, AYRI BİR PENCEREDE (popup) açılır -- ana sayfa (liste/arama)
     OLDUĞU GİBİ, hiç etkilenmeden kalır. O aracın TÜM bilgileri
     (özellikler, YAKIT TİPİ, tüm alış faturaları, gümrük bilgisi) o
     küçük pencerede gösterilir.

NOT (yakıt tipi hakkında, 2026-09-08): "Yakıt Tipi" (Benzin/Dizel/
Elektrik) DMS API'sinden gelen gerçek bir alan DEĞİL -- motor_no'nun ilk
harfinden TAHMİN ediliyor (bkz. src/etl.py: yakit_tipi_belirle()). Bu
sayfa sadece o tahmini gösterir/filtreler, kendisi bir hesaplama yapmaz.

ETKİ HARİTASI: Bu dosya db.py ve config.py'yi OKUMA amaçlı kullanır (tüm
tablo sorguları SELECT). AYRICA (2026-09-08'den itibaren) src/etl.py'deki
run_range() fonksiyonunu ÇAĞIRIR -- "Veri Çek" butonuna basılınca bu
fonksiyon normal şekilde çalışır (aynı 28 günlük parçalama, aynı upsert
mantığı), tek fark elle "python -m src.etl ..." yazmak yerine tarayıcıdan
tetiklenmesi. etl.py'nin KENDİSİNE hiçbir değişiklik YAPMAZ, sadece onu
çağırır -- yani etl.py'yi elden çalıştırmaya devam etmek de her zaman
mümkün, ikisi çakışmaz (ama İKİSİNİ AYNI ANDA çalıştırma, bkz. aşağıdaki
_VERI_CEK_KILIT notu).
"""
import calendar
import datetime as dt
import threading
from urllib.parse import urlencode

from flask import Flask, jsonify, redirect, request, render_template_string, url_for
import psycopg2.extras

from . import db
from . import etl

app = Flask(__name__)

# Ana sayfa sonuç tablosunda sayfa başına gösterilecek kayıt sayısı.
# 2026-09-08: eskiden "LIMIT 500" ile SESSİZCE kesiliyordu (500'den fazla
# sonuç varsa geri kalanı hiç gösterilmiyordu) -- şimdi bunun yerine
# sayfalama var, veri kaybı yok, sadece 500'er 500'er sayfalara bölünüyor.
SAYFA_BOYUTU = 500

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

# 1) BİRLEŞİK ARAMA (2026-09-08, İKİNCİ sürüm -- eskiden GENEL ARAMA /
#    TARİH ARALIĞI / FİLTRE diye ÜÇ AYRI sorguydu, hangisi kullanılacağı
#    bir ÖNCELİK SIRASINA göre seçiliyordu ("model seçiliyse SADECE ona
#    göre ara, metin/tarih YOK SAYILIR" gibi) -- kullanıcı "Ara butonu hiç
#    bir filtreye takılmamalı, tarih filitreleri bağımsız olmalı" diye
#    haklı olarak ŞİKAYET ETTİ: model seçiliyken tarih ya da metin
#    kutusunun hiçbir etkisi olmuyordu. ŞİMDİ TEK bir sorgu -- doldurulan
#    HER alan (metin, model, dış renk, yakıt tipi, tarih aralığı) AYNI
#    ANDA, VE (AND) mantığıyla birlikte uygulanıyor; boş bırakılan alan
#    hiç filtre uygulamıyormuş gibi davranıyor (ÖĞRENME NOTU: "(%s = ''
#    OR kolon = %s)" deseni -- kutu boşsa ilk taraf hep DOĞRU olduğu için
#    o AND koşulu sonucu etkilemiyor). GÖVDE (FROM/JOIN/WHERE) hem satır
#    sorgusunda hem de sayısını almak için COUNT sorgusunda TEKRAR
#    kullanılıyor (bkz. BIRLESIK_ARAMA_SAYISI_SORGUSU) -- ikisi arasında
#    fark varsa "toplam X kayıt" ile gerçekte gelen satırlar TUTARSIZ
#    olur, o yüzden gövdeyi TEK bir yerde (BIRLESIK_ARAMA_GOVDESI) tutup
#    ikisine de aynısını ekliyoruz.
#
#    TARİH ARALIĞI PARAMETRESİ: "(%s OR af.fatura_tarihi BETWEEN %s AND
#    %s)" -- ilk %s, Python'dan gelen bir BOOLEAN (tarih_filtresi_yok).
#    SQL'in üç-değerli mantığı sayesinde bu TRUE olduğunda (tarih filtresi
#    istenmiyorsa) BETWEEN'in sonucu ne olursa olsun (hatta tarih alanları
#    NULL/anlamsız olsa bile) tüm OR ifadesi DOĞRU olur -- bu yüzden tarih
#    filtresi YOKKEN bas/bit'e gerçek (uzak) tarihler veriyoruz, NULL değil
#    (NULL ile BETWEEN'in sonucu UNKNOWN olur, "FALSE OR UNKNOWN" YANLIŞ
#    sonuç doğurup satırları YANLIŞLIKLA elerdi -- bu yüzden None yerine
#    1900-01-01 / 2100-01-01 gibi zararsız sabit tarihler kullanılıyor).
BIRLESIK_ARAMA_GOVDESI = """
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
        AND (%s = '' OR (%s = 'TANIMSIZ_ISARETI' AND a.yakit_id IS NULL) OR yt.adi = %s)
        AND (
            %s = ''
            OR a.sasi_no ILIKE %s
            OR a.motor_no ILIKE %s
            OR c.adi ILIKE %s
            OR dr.adi ILIKE %s
            OR ic.adi ILIKE %s
            OR af.fatura_no ILIKE %s
            OR EXISTS (
                SELECT 1 FROM plakalar p2
                WHERE p2.arac_id = a.id AND p2.plaka ILIKE %s
            )
        )
        AND (%s OR af.fatura_tarihi BETWEEN %s AND %s)
"""

BIRLESIK_ARAMA_SORGUSU = """
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
""" + BIRLESIK_ARAMA_GOVDESI + """
    ORDER BY af.fatura_tarihi DESC NULLS LAST
    LIMIT %s OFFSET %s
"""

BIRLESIK_ARAMA_SAYISI_SORGUSU = "SELECT COUNT(*) AS sayi " + BIRLESIK_ARAMA_GOVDESI

# 2) TÜM ARAÇLAR: "Toplam Araç" kartına tıklayınca -- hiçbir filtre yok,
#    faturası olmayan araçlar bile (varsa) LEFT JOIN sayesinde görünür.
#    2026-09-08: 500 sınırı KALDIRILDI, bunun yerine sayfalama (LIMIT/
#    OFFSET) eklendi -- bkz. anasayfa()'daki SAYFA_BOYUTU.
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
    LIMIT %s OFFSET %s
"""
TUM_ARACLAR_SAYISI_SORGUSU = "SELECT COUNT(*) AS sayi FROM araclar"

# 3) GÜMRÜK KAYDI OLAN ARAÇLAR: "Gümrük Kaydı Olan Araç" kartına tıklayınca.
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
    LIMIT %s OFFSET %s
"""
ITHAL_ARACLAR_SAYISI_SORGUSU = """
    SELECT COUNT(*) AS sayi FROM araclar a
    WHERE EXISTS (SELECT 1 FROM gumruk_bilgileri g WHERE g.arac_id = a.id)
"""

# Yakıt Tipi comboboxunda "Tanımsız" seçeneğini temsil eden özel bir
# değer -- veritabanında böyle bir SATIR yok (yakit_tipleri tablosunda
# "Tanımsız" diye bir kayıt YOK, olmasını da istemiyoruz, çünkü bu bir
# GERÇEK yakıt tipi değil, "motor_no'dan tahmin edilemedi" durumu). Bu
# yüzden combobox'ta gösterilen metin Python tarafında SENTETIK olarak
# ekleniyor (bkz. aşağıdaki anasayfa() fonksiyonu), SQL'e gönderilirken de
# "yt.adi = %s" yerine "a.yakit_id IS NULL" koşuluna çevriliyor.
# UYARI: Bu METİN yukarıdaki BIRLESIK_ARAMA_GOVDESI'NİN İÇİNDE SABİT
# (literal) olarak da geçiyor ('TANIMSIZ_ISARETI') -- ikisini birbirinden
# BAĞIMSIZ değiştirme, aynı kalmaları gerekiyor, yoksa "Tanımsız" filtresi
# sessizce çalışmaz hale gelir.
YAKIT_TANIMSIZ_DEGER = "TANIMSIZ_ISARETI"

# ---- Ana sayfadaki 3 combobox'ı (Model/Dış Renk/Yakıt Tipi) doldurmak
#      için veritabanındaki BENZERSİZ değerleri çeken üç sorgu.
#      2026-09-08: "İL SEÇİNCE İLÇE ONA GÖRE DOLSUN" mantığı eklendi --
#      Model seçiliyse (model_secili doluysa) Dış Renk ve Yakıt Tipi
#      seçenekleri SADECE o modelde GERÇEKTEN VAR OLAN değerlerle
#      sınırlanıyor (yoksa kullanıcı var olmayan bir renk/yakıt
#      kombinasyonunda "0 sonuç" filtresine takılıp kalıyordu). Model
#      seçili DEĞİLSE (%s = '' ise) eskisi gibi TÜM değerler listelenir.
#      NOT: renk ve yakıt seçimleri birbirini KISITLAMIYOR (sadece model
#      -> renk ve model -> yakıt yönünde cascade var, kullanıcı sadece bu
#      yönü istedi).
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
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    LEFT JOIN dis_renkler dr ON dr.id = sor.dis_renk_id
    WHERE dr.adi IS NOT NULL
        AND (%s = '' OR c.adi = %s)
    ORDER BY dr.adi
"""

YAKIT_SECENEKLERI_SORGUSU = """
    SELECT DISTINCT yt.adi AS deger
    FROM araclar a
    JOIN yakit_tipleri yt ON yt.id = a.yakit_id
    LEFT JOIN spec_ocn_renk sor ON sor.id = a.spec_ocn_renk_id
    LEFT JOIN spec_ocn so ON so.id = sor.spec_ocn_id
    LEFT JOIN spec s ON s.id = so.spec_id
    LEFT JOIN carline c ON c.id = s.carline_id
    WHERE (%s = '' OR c.adi = %s)
    ORDER BY yt.adi
"""

# Yakıt tipi TANIMSIZ (yakit_id NULL) kaç araç var -- combobox'taki
# "Tanımsız" seçeneğinin yanında kaç araç olduğunu göstermek için.
YAKIT_TANIMSIZ_SAYISI_SORGUSU = """
    SELECT COUNT(*) AS sayi FROM araclar WHERE yakit_id IS NULL
"""

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
# "Veri Çek" butonu -- src/etl.py'yi arka planda tetikleme
# ------------------------------------------------------------------
# ÖĞRENME NOTU (neden thread, neden global bir durum sözlüğü?): Flask
# normalde her isteği hızlıca cevaplayıp bitirmek ister -- run_range() ise
# (özellikle aylarca süren bir aralık için) DAKİKALARCA sürebilir (her 28
# günlük parça için ayrı bir DMS API çağrısı yapıyor). Eğer bunu doğrudan
# "Veri Çek" butonunun isteği İÇİNDE çalıştırsaydık, tarayıcı sekmesi o
# süre boyunca "yükleniyor" halinde takılı kalırdı. Bunun yerine:
#   1) buton basılınca run_range() AYRI BİR THREAD'DE başlatılır,
#   2) istek HEMEN "/" adresine geri döner (sayfa donmaz),
#   3) üst bardaki JS, /veri-cek/durum adresini birkaç saniyede bir
#      sorgulayarak (polling) ilerlemeyi gösterir.
# _VERI_CEK_KILIT (threading.Lock): aynı anda İKİ çekimin birden
# başlamasını engellemek için -- ikisi aynı anda aynı satırlara
# UPDATE/INSERT atmaya çalışırsa veri karışabilir/yavaşlar. Bu kilit
# olmadan, kullanıcı butona hızlı hızlı birkaç kez basarsa (ya da iki
# farklı sekmeden aynı anda) birden fazla run_range() aynı anda çalışırdı.
_VERI_CEK_KILIT = threading.Lock()
_VERI_CEK_DURUMU = {
    "calisiyor": False,
    "baslangic": None,
    "bitis": None,
    "eklenen": None,
    "atlanan": None,
    "basarisiz_parca": None,
    "hata": None,
    "baslama_zamani": None,
    "bitis_zamani": None,
}


def _veri_cek_calistir(baslangic, bitis):
    """Arka plan thread'inin çalıştırdığı fonksiyon -- run_range()'i
    çağırır, sonucu (ya da hatayı) _VERI_CEK_DURUMU'na yazar. Flask'ın
    ana request/response döngüsünün DIŞINDA çalışır -- burada bir hata
    olsa bile kullanıcının tarayıcısına doğrudan bir hata sayfası GİTMEZ,
    sadece durum sözlüğüne "hata" olarak yazılır (JS bunu okuyup gösterir).
    """
    try:
        eklenen, atlanan, basarisiz = etl.run_range(baslangic, bitis)
        with _VERI_CEK_KILIT:
            _VERI_CEK_DURUMU.update({
                "calisiyor": False,
                "eklenen": eklenen,
                "atlanan": atlanan,
                "basarisiz_parca": basarisiz,
                "hata": None,
                "bitis_zamani": dt.datetime.now().strftime("%H:%M:%S"),
            })
    except Exception as exc:  # noqa: BLE001 -- kasıtlı: hiçbir hata thread'i sessizce öldürmesin
        log_mesaji = "Veri çekme başarısız: %s" % exc
        with _VERI_CEK_KILIT:
            _VERI_CEK_DURUMU.update({
                "calisiyor": False,
                "hata": log_mesaji,
                "bitis_zamani": dt.datetime.now().strftime("%H:%M:%S"),
            })


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

  /* "Veri Çek" formu -- koyu lacivert üst barın İÇİNDE, sağ tarafta.
     Kutular/buton beyaz zeminli (barın kendisi koyu olduğu için). */
  .ust-serit-sag { display: flex; flex-direction: column; align-items: flex-end; gap: 4px; }
  .veri-cek-formu { display: flex; align-items: center; gap: 6px; }
  .veri-cek-formu label { margin: 0; color: #cfe0ff; font-size: 12px; }
  .veri-cek-formu input[type=date] { padding: 5px 7px; font-size: 12px; }
  .veri-cek-formu span { color: #9db4d1; font-size: 12px; }
  .veri-cek-formu button { margin-top: 0; padding: 5px 14px; font-size: 12px; background: #16a34a; }
  .veri-cek-formu button:hover { background: #128a3e; }
  .veri-cek-durum { font-size: 12px; color: #9db4d1; min-height: 16px; text-align: right; }
  .veri-cek-durum.vc-calisiyor { color: #fbbf24; }
  .veri-cek-durum.vc-tamam { color: #4ade80; }
  .veri-cek-durum.vc-hata { color: #f87171; }

  /* Bir "Veri Çek" isteği reddedilince (örn. geçersiz tarih, ya da zaten
     bir çekim çalışıyorken) gösterilen kırmızı uyarı şeridi. */
  .uyari-bar {
    background: #fef2f2; color: #b91c1c; border-bottom: 1px solid #fecaca;
    padding: 8px 28px; font-size: 13px;
  }

  /* SABİT (sticky) ÜST BÖLÜM -- üst bar + özet kartlar + Ara/Filtrele
     kutuları bunun İÇİNDE. Aşağı kaydırınca bu blok EKRANIN ÜSTÜNE
     yapışıp kalır, sadece tablo (.icerik-alt) altında kayar -- 2026-09-08:
     "aşağı inince neyin ne olduğu belli olmuyordu" diye eklendi. Arka
     plan rengi body'yle AYNI (#eef1f5) olmalı, yoksa altından kayan
     tablo satırları şeffaf üstten görünür. */
  .sabit-ust { position: sticky; top: 0; z-index: 300; background: #eef1f5; box-shadow: 0 2px 6px rgba(0,0,0,0.08); }
  /* Bölümler arası boşluklar (2026-09-08: "aradaki boşlukları azaltarak
     gidelim" diye sıkıştırıldı -- eskiden 20px/24px'ti). Amaç: .sabit-ust
     bloğu (üst bar + kartlar + arama kutusu) daha az yer kaplasın ki hem
     tablo başlığı ekrana daha erken/daha az boşlukla yapışsın, hem de
     kaydırmadan görünen satır sayısı artsın. */
  .icerik-ust { padding: 14px 28px 0; }
  .icerik-alt { padding: 8px 28px 40px; }

  /* Özet kartları -- TIKLANABİLİR: her kart bir <a> ile sarmalanıyor. */
  .kart-satiri { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
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

  h2 { font-size: 15px; margin: 10px 0 4px; color: #111827; }
  /* Sonuç başlığı ("Bu ay (40 kayıt)" gibi) -- 2026-09-08: "filitre
     kısmındaki not araya giriyor aşağı inerken sabit kalmıyor oda sabit
     kalsın" diye bu da .sabit-ust ile TABLONUN sticky thead'i ARASINDA
     kendi katmanı olarak sabitlendi (sticky yığını: .sabit-ust -> bu ->
     thead). Arka planı sayfayla AYNI (#eef1f5) olmalı, yoksa altından
     kayan tablo satırları şeffaf üstten görünür -- z-index, .sabit-ust'un
     (300) altında ama thead'in (20) üstünde. */
  .sonuc-basligi {
    position: sticky; top: var(--sabit-yukseklik); z-index: 250;
    background: #eef1f5; padding: 4px 0;
  }
  .arama-kartlari { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 0; align-items: flex-start; }
  form.arama-formu {
    background: #fff;
    border-radius: 8px;
    padding: 10px 16px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
  }
  /* TEK SATIRLIK arama/filtre kutusu (2026-09-08, ÜÇÜNCÜ deneme): önceki
     hal (Ara / Model-Renk-Yakıt / Tarih / Ara-Temizle diye ÜST ÜSTE dört
     satır, aralarında çizgiyle bölünmüş) "sayfanın yarısından fazlasını
     kaplıyor, dağınık, çorba gibi" diye BEĞENİLMEDİ. Şimdi HER alan
     (metin kutusu, comboboxlar, tarih, hızlı tarih seçimi, Ara/Temizle
     butonları) kendi küçük "grup"u -- üstte minik bir etiket, altında
     kendi girdisi -- ve bütün gruplar TEK bir flex satırında yan yana
     dizilir, aralarında çizgi/bölüm YOK. Normal ekran genişliğinde HEP
     TEK SATIR görünür; sadece pencere çok daralırsa (örn. yarım ekran)
     flex-wrap sayesinde gruplar alt satıra kayar -- ama bu istisna,
     kural değil. */
  .arama-formu-birlesik { flex: 1 1 100%; }
  label { display: inline-block; font-size: 13px; }
  input[type=text], input[type=date] {
    padding: 7px 9px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px;
  }
  select {
    padding: 7px 9px; border: 1px solid #cbd5e1; border-radius: 4px;
    font-size: 13px; background: #fff;
  }
  button {
    padding: 7px 16px; border: 0; background: #2563eb; color: #fff;
    border-radius: 4px; cursor: pointer; font-size: 13px;
  }
  button:hover { background: #1d4ed8; }

  /* Tek satırdaki her alan böyle bir "grup": üstte minik büyük harfli
     etiket, altında girdi -- hangi kutunun ne olduğu (Model mi Renk mi)
     hâlâ belli olsun diye, ama eski uzun label'lardan ("Başlangıç:" gibi)
     çok daha az yer kaplasın diye. */
  .arama-tek-satir {
    display: flex; align-items: flex-end; gap: 10px; flex-wrap: wrap;
  }
  .arama-grup { display: flex; flex-direction: column; gap: 3px; }
  .arama-grup label {
    font-size: 10px; font-weight: 700; color: #6b7280; text-transform: uppercase;
    letter-spacing: 0.02em;
  }
  /* Genel arama kutusu -- önce (2026-09-08 sabah) "ara çubuğunu kısaltıp
     hızlı tarihin yanına hızlı tarih butonlarını ekleyelim" diye 170px'e
     KISALTILDI, sonra AYNI GÜN "ne arıyorsun arama çubuğunun boyunu 2 kat
     artıralım" diye 340px'e (2x) BÜYÜTÜLDÜ. flex-grow hâlâ 0 -- kalan
     boşluğu doldurmak için büyümüyor, sabit genişlikte duruyor. */
  .arama-grup-genel { flex: 0 0 340px; }
  .arama-grup-genel input[type=text] { width: 100%; }
  .arama-grup select { width: 112px; }
  .arama-grup input[type=date] { width: 126px; }
  .arama-tarih-ayrac { padding-bottom: 8px; color: #9ca3af; font-size: 13px; }
  .arama-hizli-tarih { width: 106px; }
  /* Hızlı Tarih açılır listesinin YANINDA aynı işi yapan butonlar (2026-
     09-08: kullanıcı "combobox olarak güzel olmuş ama buton seçimlerini
     de istiyorum" dedi -- ikisi BİRLİKTE duruyor, hangisi kullanışlıysa
     o kullanılabilsin diye). */
  .arama-hizli-tarih-butonlar { display: flex; gap: 4px; flex-wrap: wrap; }
  .arama-hizli-tarih-butonlar button {
    padding: 7px 9px; font-size: 11.5px;
  }

  /* Temizle: <button> DEĞİL, düz "/" linkine giden bir <a> -- tüm alanları
     sıfırlayıp sayfayı varsayılan (bu ay) görünümle yeniden yükler.
     a.buton-ikincil: .buton-ikincil normalde <button> için (aşağıdaki
     kural) -- <a>'ya da uygulandığı için, <button>'ın taban CSS'inden
     (tag selector "button") gelen ama <a>'ya otomatik gelmeyen özellikleri
     (kenar yuvarlama, imleç, kutu gibi davranma) elle ekliyoruz. */
  a.buton-ikincil {
    display: inline-block; text-decoration: none; border-radius: 4px; cursor: pointer;
  }
  .buton-ikincil {
    background: #eef1f5; color: #1f2937; border: 1px solid #cbd5e1;
    padding: 7px 12px; font-size: 12px;
  }
  .buton-ikincil:hover { background: #e2e8f0; }

  .tablo-sarmalayici {
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    margin-bottom: 16px;
  }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid #eef0f2; padding: 7px 10px; text-align: left; white-space: nowrap; }
  /* TABLO BAŞLIĞINI SABİT (sticky) YAPMA -- ÜÇÜNCÜ deneme (2026-09-08),
     bu kez ÇALIŞIYOR (canlı Playwright/Chromium testiyle doğrulandı).
     İLK iki denemede .tablo-sarmalayici'de "overflow-x: auto" vardı (geniş
     11 sütunlu tabloyu dar ekranda yatay kaydırmak için) -- CSS Overflow
     spesifikasyonu gereği bu, kutuyu position:sticky torunları için bir
     "scroll container" yapıyordu, ve kutu kendisi bağımsız kaymadığından
     içindeki sticky thead satırları YA gözden kayboluyordu YA DA veri
     satırlarının üstüne biniyordu ("1 kayıt var ama görünmüyor" hatası).
     "overflow-y: clip" de bunu çözmüyordu (Chrome'da hidden ile aynı).
     ÇÖZÜM: overflow-x:auto'yu TAMAMEN KALDIRDIK (tablo zaten normal
     ekranlarda yatay kaydırmaya gerek kalmadan sığıyor -- çok dar bir
     pencerede tablo taşarsa artık SAYFANIN KENDİSİ yatay kayar, bu kutu
     değil). Böylece bu tablonun sticky thead'i, .sabit-ust ile AYNI
     kaydırma bağlamını (viewport) paylaşıyor ve gerçekten çalışıyor.
     --sabit-yukseklik / --baslik-satiri-yukseklik: .sabit-ust'un ve
     başlık satırının o anki yüksekliği -- JS ile ölçülüp yazılıyor (bkz.
     ORTAK_JS sabitBoyutlariGuncelle()), çünkü .sabit-ust'un yüksekliği
     sabit bir sayı değil (uyarı şeridi çıkıp/kaybolabiliyor, ekran
     genişliğine göre sarabiliyor). */
  :root {
    --sabit-yukseklik: 0px;
    --baslik-metni-yukseklik: 0px;
    --baslik-satiri-yukseklik: 0px;
  }
  thead tr.baslik-satiri th {
    background: #041e42; color: #fff; cursor: pointer; user-select: none;
    position: sticky; top: calc(var(--sabit-yukseklik) + var(--baslik-metni-yukseklik)); z-index: 20;
  }
  thead tr.baslik-satiri th:hover { background: #0a2d5e; }
  thead tr.baslik-satiri th::after { content: " ⇅"; opacity: 0.5; font-size: 11px; }
  thead tr.baslik-satiri th[data-siralama="artan"]::after { content: " ▲"; opacity: 1; }
  thead tr.baslik-satiri th[data-siralama="azalan"]::after { content: " ▼"; opacity: 1; }
  thead tr.filtre-satiri th {
    background: #f3f4f6; padding: 4px 6px; cursor: default;
    position: sticky;
    top: calc(var(--sabit-yukseklik) + var(--baslik-metni-yukseklik) + var(--baslik-satiri-yukseklik));
    z-index: 20;
  }
  thead tr.filtre-satiri th::after { content: ""; }

  /* Sütun başlığının altındaki "Excel benzeri" filtre butonu (bkz.
     ORTAK_JS: sutunFiltrePopupAc/filtreleUygula). Filtre AKTİFSE
     (.sfp-aktif) mavi renkte, değilse gri/nötr durur. */
  .sutun-filtre-buton {
    width: 100%; padding: 5px 6px; border: 1px solid #d1d5db; border-radius: 4px;
    font-size: 11px; background: #fff; color: #4b5563; cursor: pointer;
    margin-top: 0; text-align: left;
  }
  .sutun-filtre-buton:hover { background: #f3f4f6; }
  .sutun-filtre-buton.sfp-aktif { background: #dbeafe; border-color: #93c5fd; color: #1d4ed8; font-weight: 600; }

  /* Sütun filtre popup'ı -- document.body'ye EKLENIYOR (tablo hücresinin
     İÇİNE değil), çünkü hücre içine sığdırmaya çalışmak taşma/kırpılma
     sorunu çıkarır. JS ile th'nin altına konumlandırılıyor. */
  .sutun-filtre-panel {
    position: absolute; z-index: 500; background: #fff; border: 1px solid #cbd5e1;
    border-radius: 6px; box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    padding: 10px; width: 240px; font-size: 13px; white-space: normal;
  }
  .sutun-filtre-panel .sfp-arama {
    width: 100%; padding: 6px 8px; border: 1px solid #cbd5e1; border-radius: 4px;
    font-size: 12px; margin-bottom: 8px;
  }
  .sutun-filtre-panel .sfp-hizli { font-size: 11px; margin-bottom: 6px; }
  .sutun-filtre-panel .sfp-hizli a { color: #2563eb; text-decoration: none; }
  .sutun-filtre-panel .sfp-hizli a:hover { text-decoration: underline; }
  .sutun-filtre-panel .sfp-liste {
    max-height: 220px; overflow-y: auto; border: 1px solid #eef0f2; border-radius: 4px;
    padding: 4px 6px; margin-bottom: 8px;
  }
  .sutun-filtre-panel .sfp-oge {
    display: flex; align-items: center; gap: 6px; padding: 3px 2px;
    font-size: 12.5px; font-weight: 400; cursor: pointer;
  }
  .sutun-filtre-panel .sfp-oge input { margin: 0; }
  .sutun-filtre-panel .sfp-butonlar { display: flex; gap: 6px; }
  .sutun-filtre-panel .sfp-butonlar button { flex: 1; margin-top: 0; padding: 6px 8px; font-size: 12px; }

  tbody tr.veri-satiri { cursor: pointer; }
  tbody tr.veri-satiri:nth-child(even) { background: #fafbfc; }
  tbody tr.veri-satiri:hover { background: #eef4ff; }
  tbody tr.bos-satiri td { color: #9ca3af; text-align: center; padding: 18px; font-style: italic; cursor: default; }
  tbody tr.bos-satiri:hover { background: inherit; }
  td a { color: #2563eb; text-decoration: none; }
  td a:hover { text-decoration: underline; }

  /* Sayfalama (2026-09-08: "500'den fazla gösterilmesin diye bir kısıt
     olmasın, gerekirse birden fazla sayfa olsun" diye eklendi -- artık
     500'den fazla sonuç SESSİZCE kesilmiyor, 500'er 500'er sayfalanıyor). */
  .sayfalama {
    display: flex; align-items: center; gap: 10px; justify-content: center;
    margin-top: 14px; font-size: 13px; color: #4b5563;
  }
  .sayfalama a.buton-ikincil.sf-pasif {
    opacity: 0.4; pointer-events: none;
  }

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
  // Kullanıcı GERÇEKTEN bir tarih seçti -- submit listener'ı bu kutuları
  // boşaltmasın (bkz. tarihDokunulduAyarla() / tarih-arama-formu submit
  // dinleyicisi).
  tarihDokunulduAyarla(true);
  document.getElementById('tarih-arama-formu').requestSubmit();
}

// ------------------------------------------------------------------
// TARİH KUTULARI "GÖRÜNÜŞTE DOLU AMA KULLANICI DOKUNMADI" HATASI (2026-
// 09-08'de bulundu): Başlangıç/Bitiş kutuları kullanıcı hiç dokunmasa
// bile HER ZAMAN "bu ayın tarihleri" ile dolu görünüyor (bkz. Python
// tarafındaki baslangic_gosterim/bitis_gosterim). Bu SADECE görsel bir
// kolaylık olması gerekiyordu ama kutular AYNI ZAMANDA formun gerçek
// <input name="baslangic">/<input name="bitis"> alanları -- yani kullanıcı
// sadece Model seçince (ya da Ara'ya basınca) form gönderildiğinde, bu
// "bu ay" tarihleri SESSİZCE tarih filtresi olarak da gönderiliyordu.
// Sonuç: "Model seçtim ama sonuçlar yanlış/eksik" şikayeti -- aslında
// hem Model HEM DE görünmeyen bir "bu ay" filtresi BİRLİKTE uygulanıyordu.
//
// ÇÖZÜM: tarihDokunuldu bayrağı -- kullanıcı tarih kutularına GERÇEKTEN
// dokunduysa (yazı girdi, hızlı tarih butonu/listesi kullandı) true olur.
// Form gönderilirken (submit event -- Ara butonu, Enter, ya da JS'teki
// requestSubmit() çağrıları) bayrak HÂLÂ false ise, kutular submit anında
// (tarayıcı query string'i oluşturmadan hemen önce) boşaltılıyor -- böylece
// "görünüşte dolu" tarih artık arama mantığını etkilemiyor, sadece
// kullanıcıya bilgi veriyor (sunucu tarafında da zaten böyle
// yorumlanıyordu, ama form HTML'i bunu GERÇEKTEN sağlamıyordu).
// ------------------------------------------------------------------
var tarihDokunuldu = false;

function tarihDokunulduAyarla(deger) {
  tarihDokunuldu = deger;
}

document.addEventListener('DOMContentLoaded', function () {
  var form = document.getElementById('tarih-arama-formu');
  if (!form) return;

  // Sayfa, kullanıcının GERÇEKTEN seçtiği bir tarih aralığıyla mı açıldı
  // (örn. bir arama sonucunu yeniledi/sayfaladı) -- öyleyse kutular zaten
  // "dokunulmuş" sayılmalı, yoksa bir sonraki Model/Renk/Yakıt seçiminde
  // kullanıcının kendi seçtiği tarih aralığı YANLIŞLIKLA silinirdi.
  tarihDokunuldu = form.getAttribute('data-tarih-kullanici-secti') === '1';

  var baslangicKutu = document.getElementById('baslangic-girdi');
  var bitisKutu = document.getElementById('bitis-girdi');
  ['input', 'change'].forEach(function (olay) {
    if (baslangicKutu) baslangicKutu.addEventListener(olay, function () { tarihDokunulduAyarla(true); });
    if (bitisKutu) bitisKutu.addEventListener(olay, function () { tarihDokunulduAyarla(true); });
  });

  form.addEventListener('submit', function () {
    if (!tarihDokunuldu) {
      if (baslangicKutu) baslangicKutu.value = '';
      if (bitisKutu) bitisKutu.value = '';
    }
  });
});

// ------------------------------------------------------------------
// Sütun bazlı "Excel benzeri" çoklu-seçim filtre (2026-09-08 eklendi)
// ------------------------------------------------------------------
// ÖĞRENME NOTU: Eskiden her sütunun altında serbest metin kutusu vardı
// (yukarıda kaldırılan eski filtrele() fonksiyonu). Şimdi her sütun
// başlığının altında "Filtrele ▾" butonu var -- tıklayınca o sütunda
// GEÇEN TÜM FARKLI DEĞERLER onay kutulu bir liste halinde bir popup'ta
// gösteriliyor, kullanıcı istediği kadarını seçip "Uygula"ya basıyor.
// Birden fazla sütunda filtre varsa hepsi birlikte (VE mantığıyla)
// uygulanıyor -- tıpkı Excel'deki sütun filtreleri gibi.
//
// _sutunFiltreDurumu: { tabloId: { kolonIndex: Set(seçili değerler) } }
// Bir kolon için Set YOKSA, o kolonda filtre YOK demektir (tüm satırlar
// o kolon için "geçer" sayılır) -- "hepsi seçili" ile "filtre yok" aynı
// şey, bu yüzden "Uygula"da hepsi seçiliyse Set'i hiç saklamıyoruz.
var _sutunFiltreDurumu = {};
var _acikSutunFiltrePaneli = null;  // aynı anda tek panel açık olabilir

function _hucreMetni(satir, kolonIndex) {
  var hucre = satir.children[kolonIndex];
  return hucre ? hucre.innerText.trim() : '';
}

// Bir tablonun bir kolonundaki TÜM farklı değerleri toplar (satır o an
// başka bir filtreyle gizlenmiş olsa bile -- Excel'de de filtre listesi
// diğer sütunlardaki filtrelerden etkilenmez, hep TÜM veriyi gösterir).
function _kolonDegerleriTopla(tabloId, kolonIndex) {
  var tablo = document.getElementById(tabloId);
  var tbody = tablo.tBodies[0];
  var degerler = [];
  var gorulen = {};
  tbody.querySelectorAll('tr.veri-satiri').forEach(function (satir) {
    var v = _hucreMetni(satir, kolonIndex);
    if (v === '') v = '(boş)';
    if (!gorulen[v]) { gorulen[v] = true; degerler.push(v); }
  });
  degerler.sort(function (a, b) { return a.localeCompare(b, 'tr'); });
  return degerler;
}

function sutunFiltrePopupAc(evt, tabloId, buton) {
  evt.stopPropagation();
  // Aynı butona tekrar basıldıysa panel aç/kapa gibi davranır.
  if (_acikSutunFiltrePaneli && _acikSutunFiltrePaneli._buton === buton) {
    sutunFiltrePopupKapat();
    return;
  }
  sutunFiltrePopupKapat();  // başka bir panel açıksa önce onu kapat

  var th = buton.closest('th');
  var basliklar = Array.prototype.slice.call(th.parentElement.children);
  var kolonIndex = basliklar.indexOf(th);

  var degerler = _kolonDegerleriTopla(tabloId, kolonIndex);
  if (!_sutunFiltreDurumu[tabloId]) _sutunFiltreDurumu[tabloId] = {};
  var seciliSet = _sutunFiltreDurumu[tabloId][kolonIndex];  // undefined = hepsi seçili

  var panel = document.createElement('div');
  panel.className = 'sutun-filtre-panel';
  panel._buton = buton;

  var aramaKutu = document.createElement('input');
  aramaKutu.type = 'text';
  aramaKutu.className = 'sfp-arama';
  aramaKutu.placeholder = 'değer ara...';
  panel.appendChild(aramaKutu);

  var hizli = document.createElement('div');
  hizli.className = 'sfp-hizli';
  var tumSec = document.createElement('a');
  tumSec.href = '#';
  tumSec.textContent = 'Tümünü Seç';
  var tumKaldir = document.createElement('a');
  tumKaldir.href = '#';
  tumKaldir.textContent = 'Tümünü Kaldır';
  hizli.appendChild(tumSec);
  hizli.appendChild(document.createTextNode(' \\u00b7 '));
  hizli.appendChild(tumKaldir);
  panel.appendChild(hizli);

  var liste = document.createElement('div');
  liste.className = 'sfp-liste';
  panel.appendChild(liste);

  function ogeleriCiz(filtreMetni) {
    liste.innerHTML = '';
    degerler.forEach(function (deger) {
      if (filtreMetni && deger.toLocaleLowerCase('tr').indexOf(filtreMetni) === -1) return;
      var etiket = document.createElement('label');
      etiket.className = 'sfp-oge';
      var kutu = document.createElement('input');
      kutu.type = 'checkbox';
      kutu.value = deger;
      kutu.checked = !seciliSet || seciliSet.has(deger);
      etiket.appendChild(kutu);
      etiket.appendChild(document.createTextNode(deger));
      liste.appendChild(etiket);
    });
  }
  ogeleriCiz('');

  aramaKutu.addEventListener('input', function () {
    ogeleriCiz(aramaKutu.value.trim().toLocaleLowerCase('tr'));
  });
  tumSec.addEventListener('click', function (e) {
    e.preventDefault();
    liste.querySelectorAll('input[type=checkbox]').forEach(function (k) { k.checked = true; });
  });
  tumKaldir.addEventListener('click', function (e) {
    e.preventDefault();
    liste.querySelectorAll('input[type=checkbox]').forEach(function (k) { k.checked = false; });
  });

  var butonlar = document.createElement('div');
  butonlar.className = 'sfp-butonlar';
  var uygulaBtn = document.createElement('button');
  uygulaBtn.type = 'button';
  uygulaBtn.textContent = 'Uygula';
  var temizleBtn = document.createElement('button');
  temizleBtn.type = 'button';
  temizleBtn.className = 'buton-ikincil';
  temizleBtn.textContent = 'Temizle';
  butonlar.appendChild(uygulaBtn);
  butonlar.appendChild(temizleBtn);
  panel.appendChild(butonlar);

  uygulaBtn.addEventListener('click', function () {
    // Arama kutusu doluyken "Uygula"ya basılırsa, aramayla elenmiş
    // (DOM'dan silinmiş) kutucuklar okunamaz -- bu yüzden önce arama
    // metnini temizleyip listeyi TAM haliyle yeniden çiziyoruz, öyle
    // okuyoruz (kullanıcının arama sırasında yaptığı işaretlemeler
    // ogeleriCiz() her çağrıldığında seciliSet üzerinden korunmuyor
    // olabileceğinden, önce mevcut işaretleri seciliSet'e yansıtmadan
    // TEMİZ bir okuma yapmak yerine: arama kutusu boşken zaten TÜM
    // değerler DOM'da olduğu için, normal akışta bu adım sadece bir
    // güvenlik önlemi).
    var tumKutular = liste.querySelectorAll('input[type=checkbox]');
    var yeniSet = new Set();
    var hepsiSecili = true;
    tumKutular.forEach(function (k) { if (k.checked) yeniSet.add(k.value); else hepsiSecili = false; });
    if (hepsiSecili) {
      delete _sutunFiltreDurumu[tabloId][kolonIndex];
    } else {
      _sutunFiltreDurumu[tabloId][kolonIndex] = yeniSet;
    }
    filtreleUygula(tabloId);
    sutunFiltrePopupKapat();
  });
  temizleBtn.addEventListener('click', function () {
    delete _sutunFiltreDurumu[tabloId][kolonIndex];
    filtreleUygula(tabloId);
    sutunFiltrePopupKapat();
  });

  document.body.appendChild(panel);
  var konum = th.getBoundingClientRect();
  var solKenar = konum.left + window.scrollX;
  var panelGenislik = 240;
  if (solKenar + panelGenislik > window.scrollX + document.documentElement.clientWidth - 8) {
    solKenar = window.scrollX + document.documentElement.clientWidth - panelGenislik - 8;
  }
  panel.style.left = Math.max(4, solKenar) + 'px';
  panel.style.top = (konum.bottom + window.scrollY + 4) + 'px';

  _acikSutunFiltrePaneli = panel;
  document.addEventListener('click', _sutunFiltrePopupDisKapat);
  document.addEventListener('keydown', _sutunFiltrePopupEscKapat);
}

function sutunFiltrePopupKapat() {
  if (_acikSutunFiltrePaneli) {
    _acikSutunFiltrePaneli.remove();
    _acikSutunFiltrePaneli = null;
  }
  document.removeEventListener('click', _sutunFiltrePopupDisKapat);
  document.removeEventListener('keydown', _sutunFiltrePopupEscKapat);
}

function _sutunFiltrePopupDisKapat(evt) {
  if (_acikSutunFiltrePaneli && !_acikSutunFiltrePaneli.contains(evt.target)) {
    sutunFiltrePopupKapat();
  }
}

function _sutunFiltrePopupEscKapat(evt) {
  if (evt.key === 'Escape') sutunFiltrePopupKapat();
}

// Bir tablonun TÜM sütunlarındaki aktif filtreleri (Set halinde saklanan)
// birlikte (VE mantığıyla) uygular -- eskiden metin kutularını okuyan
// filtrele() fonksiyonunun YERİNE geçti. Ayrıca her sütun başlığındaki
// butona filtre aktifse .sfp-aktif class'ını ekler/kaldırır ki kullanıcı
// hangi sütunlarda filtre olduğunu (ve kaç değer seçili olduğunu) görsün.
function filtreleUygula(tabloId) {
  var tablo = document.getElementById(tabloId);
  if (!tablo) return;
  var tbody = tablo.tBodies[0];
  if (tbody.getAttribute('data-dolu') !== '1') return;

  var durum = _sutunFiltreDurumu[tabloId] || {};
  var satirlar = tbody.querySelectorAll('tr.veri-satiri');

  satirlar.forEach(function (satir) {
    var goster = true;
    for (var kolonIndex in durum) {
      var seciliSet = durum[kolonIndex];
      if (!seciliSet) continue;
      var deger = _hucreMetni(satir, kolonIndex);
      if (deger === '') deger = '(boş)';
      if (!seciliSet.has(deger)) { goster = false; break; }
    }
    satir.style.display = goster ? '' : 'none';
  });

  var basliklar = tablo.querySelectorAll('thead tr.filtre-satiri th');
  basliklar.forEach(function (th, kolonIndex) {
    var btn = th.querySelector('.sutun-filtre-buton');
    if (!btn) return;
    if (durum[kolonIndex]) {
      btn.classList.add('sfp-aktif');
      btn.textContent = 'Filtrele ▾ (' + durum[kolonIndex].size + ')';
    } else {
      btn.classList.remove('sfp-aktif');
      btn.textContent = 'Filtrele ▾';
    }
  });
}

// ------------------------------------------------------------------
// "Veri Çek" durumunu (arka planda çalışan thread'in ilerlemesini)
// birkaç saniyede bir sorgulayıp (polling) üst bardaki küçük yazıyı
// günceller. Sayfada #veri-cek-durum YOKSA (örn. detay sayfası) hiçbir
// şey yapmaz.
// ------------------------------------------------------------------
function _veriCekDurumGuncelle() {
  var kutu = document.getElementById('veri-cek-durum');
  if (!kutu) return;
  fetch('/veri-cek/durum').then(function (r) { return r.json(); }).then(function (d) {
    if (d.calisiyor) {
      kutu.className = 'veri-cek-durum vc-calisiyor';
      kutu.textContent = 'Çekiliyor... (' + (d.baslangic || '') + ' - ' + (d.bitis || '') + ')';
      setTimeout(_veriCekDurumGuncelle, 3000);
    } else if (d.hata) {
      kutu.className = 'veri-cek-durum vc-hata';
      kutu.textContent = d.hata;
    } else if (d.bitis_zamani) {
      kutu.className = 'veri-cek-durum vc-tamam';
      kutu.textContent = 'Tamamlandı (' + d.bitis_zamani + '): ' + d.eklenen + ' eklendi, ' + d.atlanan + ' atlandı' +
        (d.basarisiz_parca ? ', ' + d.basarisiz_parca + ' parça başarısız' : '') + '.';
    }
    // Metin değişince (örn. "Çekiliyor..." <-> "Tamamlandı...") satır
    // sayısı/yüksekliği değişebilir -- sticky tablo başlığının offset'i
    // bayatlamasın diye yeniden ölçüyoruz.
    sabitBoyutlariGuncelle();
  }).catch(function () {});
}

// ------------------------------------------------------------------
// Tablo başlığını (.sabit-ust'un HEMEN ALTINA) sabit/sticky yapabilmek
// için .sabit-ust'un VE başlık satırının o anki yüksekliğini ölçüp CSS
// değişkenlerine yazar (bkz. ORTAK_STIL'deki --sabit-yukseklik notu).
// Sayfada .sabit-ust YOKSA (örn. detay sayfası) SESSİZCE hiçbir şey
// yapmaz -- CSS değişkenleri 0px kalır.
// ------------------------------------------------------------------
function sabitBoyutlariGuncelle() {
  var sabitUst = document.querySelector('.sabit-ust');
  if (!sabitUst) return;
  document.documentElement.style.setProperty('--sabit-yukseklik', sabitUst.offsetHeight + 'px');

  // Sonuç başlığı ("Bu ay (40 kayıt)") -- 2026-09-08: bu da sticky yığınına
  // eklendi (.sabit-ust -> bu -> thead), o yüzden yüksekliği de ölçülüp
  // thead'in top offset'ine eklenmesi gerekiyor (bkz. ORTAK_STIL).
  var baslikMetni = document.querySelector('.sonuc-basligi');
  if (baslikMetni) {
    document.documentElement.style.setProperty('--baslik-metni-yukseklik', baslikMetni.offsetHeight + 'px');
  } else {
    document.documentElement.style.setProperty('--baslik-metni-yukseklik', '0px');
  }

  var baslikSatiri = document.querySelector('thead tr.baslik-satiri');
  if (baslikSatiri) {
    document.documentElement.style.setProperty('--baslik-satiri-yukseklik', baslikSatiri.offsetHeight + 'px');
  }
}

document.addEventListener('DOMContentLoaded', function () {
  _veriCekDurumGuncelle();
  sabitBoyutlariGuncelle();
});
window.addEventListener('load', sabitBoyutlariGuncelle);
window.addEventListener('resize', sabitBoyutlariGuncelle);
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

<div class="sabit-ust">
<div class="ust-serit">
  <div>
    <h1>ERK Araç Database</h1>
    <div class="alt-yazi">Not: "Veri Çek" ile DMS'ten yeni fatura çekebilirsiniz -- geri kalanı sadece görüntüleme.</div>
  </div>
  <div class="ust-serit-sag">
    <form class="veri-cek-formu" method="post" action="/veri-cek">
      <label>Veri Çek:</label>
      <input type="date" name="baslangic" required>
      <span>-</span>
      <input type="date" name="bitis" required>
      <button type="submit">Çek</button>
    </form>
    <div class="veri-cek-durum" id="veri-cek-durum"></div>
  </div>
</div>
{% if veri_cek_hata %}
<div class="uyari-bar">{{ veri_cek_hata }}</div>
{% endif %}

<div class="icerik-ust">

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
    <!-- TEK kutu, TEK form, TEK SATIR. Şase/motor/model/renk/plaka/fatura
         no metin araması, Model/Dış Renk/Yakıt Tipi comboboxları, tarih
         aralığı VE hızlı tarih seçimi hepsi AYNI formda -- TEK "Ara"
         butonu hangi alan(lar) doluysa hepsini BİRLİKTE (VE mantığıyla)
         uygular (bkz. anasayfa() route'undaki güncel docstring -- Ara
         butonu artık hiçbir filtreye "takılıp" diğerlerini yok saymıyor),
         yanındaki "Temizle" linki tüm alanları sıfırlayıp "/" adresine
         (varsayılan görünüme) döner.
         "Ara / Filtrele" başlığı KALDIRILDI (2026-09-08: kutuyu
         gereksiz yere yükseltiyordu).
         MODEL/RENK/YAKIT SEÇİMİ (il-ilçe mantığı): üçünün de onchange'i
         formu OTOMATİK gönderir (2026-09-08: "renk kısmı yakıt kısmı ...
         çalışmıyor" -- kullanıcı seçince HİÇBİR ŞEY olmuyordu çünkü sadece
         Model'de otomatik gönderim vardı; artık üçü de TUTARLI). Model
         değiştiğinde sayfa yeniden yüklenince Dış Renk/Yakıt Tipi
         seçenekleri SUNUCU tarafında o modele göre daraltılmış olarak
         gelir (bkz. RENK_SECENEKLERI_SORGUSU/YAKIT_SECENEKLERI_SORGUSU).
         NOT: .submit() DEĞİL .requestSubmit() kullanıyoruz -- ilki formun
         "submit" event'ini TETİKLEMEZ (bkz. ORTAK_JS'teki tarih-arama-formu
         submit listener'ı -- dokunulmamış tarih kutularını temizleyen kod,
         event tetiklenmezse hiç çalışmazdı).
         HIZLI TARİH: hem açılır liste hem YANINDA aynı işi yapan butonlar
         var (2026-09-08: "combobox güzel olmuş ama buton seçimlerini de
         istiyorum" diye ikisi BİRLİKTE bırakıldı) -- ikisi de aynı
         tarihAyarla() fonksiyonunu çağırıp formu gönderiyor. -->
    <form class="arama-formu arama-formu-birlesik" method="get" id="tarih-arama-formu"
          data-tarih-kullanici-secti="{{ '1' if tarih_kullanici_secti else '0' }}">
      <div class="arama-tek-satir">
        <div class="arama-grup arama-grup-genel">
          <label>Ne arıyorsun</label>
          <input type="text" name="q" value="{{ arama_metni }}" placeholder="şase, motor no, plaka, fatura no...">
        </div>
        <div class="arama-grup">
          <label>Model</label>
          <select name="model" onchange="this.form.requestSubmit()">
            <option value="">Tümü</option>
            {% for m in model_secenekleri %}
            <option value="{{ m }}" {{ "selected" if model_secili == m else "" }}>{{ m }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="arama-grup">
          <label>Dış Renk</label>
          <select name="renk" onchange="this.form.requestSubmit()">
            <option value="">Tümü</option>
            {% for r in renk_secenekleri %}
            <option value="{{ r }}" {{ "selected" if renk_secili == r else "" }}>{{ r }}</option>
            {% endfor %}
          </select>
        </div>
        <div class="arama-grup">
          <label>Yakıt Tipi</label>
          <select name="yakit" onchange="this.form.requestSubmit()">
            <option value="">Tümü</option>
            {% for y in yakit_secenekleri %}
            <option value="{{ y }}" {{ "selected" if yakit_secili == y else "" }}>{{ y }}</option>
            {% endfor %}
            {% if yakit_tanimsiz_sayisi %}
            <option value="{{ yakit_tanimsiz_deger }}" {{ "selected" if yakit_secili == yakit_tanimsiz_deger else "" }}>Tanımsız ({{ yakit_tanimsiz_sayisi }} araç)</option>
            {% endif %}
          </select>
        </div>
        <div class="arama-grup">
          <label>Başlangıç</label>
          <input type="date" name="baslangic" id="baslangic-girdi" value="{{ baslangic_deger }}">
        </div>
        <div class="arama-tarih-ayrac">&ndash;</div>
        <div class="arama-grup">
          <label>Bitiş</label>
          <input type="date" name="bitis" id="bitis-girdi" value="{{ bitis_deger }}">
        </div>
        <div class="arama-grup">
          <label>Hızlı Tarih</label>
          <select class="arama-hizli-tarih" onchange="if (this.value) { tarihAyarla(this.value); }">
            <option value="">Seç...</option>
            <option value="bugun">Bugün</option>
            <option value="dun">Dün</option>
            <option value="bu-hafta">Bu Hafta</option>
            <option value="bu-ay">Bu Ay</option>
            <option value="gecen-ay">Geçen Ay</option>
            <option value="bu-yil">Bu Yıl</option>
          </select>
        </div>
        <div class="arama-grup">
          <label>&nbsp;</label>
          <div class="arama-hizli-tarih-butonlar">
            <button type="button" class="buton-ikincil" onclick="tarihAyarla('bugun')">Bugün</button>
            <button type="button" class="buton-ikincil" onclick="tarihAyarla('dun')">Dün</button>
            <button type="button" class="buton-ikincil" onclick="tarihAyarla('bu-hafta')">Bu Hafta</button>
            <button type="button" class="buton-ikincil" onclick="tarihAyarla('bu-ay')">Bu Ay</button>
            <button type="button" class="buton-ikincil" onclick="tarihAyarla('gecen-ay')">Geçen Ay</button>
            <button type="button" class="buton-ikincil" onclick="tarihAyarla('bu-yil')">Bu Yıl</button>
          </div>
        </div>
        <button type="submit">Ara</button>
        <a href="/" class="buton-ikincil buton-link">Temizle</a>
      </div>
    </form>
  </div>

</div>
</div>

<div class="icerik-alt">

  <h2 class="sonuc-basligi">{{ baslik_metni }} ({{ toplam_kayit }} kayıt{{ ", sayfa %d / %d"|format(sayfa, toplam_sayfa) if toplam_sayfa > 1 else "" }})</h2>

  <div class="tablo-sarmalayici">
  <table id="tablo-sonuclar">
    <thead>
      <tr class="baslik-satiri" onclick="event.target.tagName === 'TH' && sirala('tablo-sonuclar', Array.from(event.target.parentNode.children).indexOf(event.target))">
        <th>Şase</th><th>Motor No</th><th>Model</th><th>Model Yılı</th><th>Dış Renk</th><th>İç Renk</th><th>Yakıt</th><th>Plaka</th><th>Fatura No</th><th>Fatura Tarihi</th><th>Toplam</th>
      </tr>
      <tr class="filtre-satiri">
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-sonuclar', this)">Filtrele ▾</button></th>
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

  {% if toplam_sayfa > 1 %}
  <div class="sayfalama">
    <a class="buton-ikincil {{ 'sf-pasif' if sayfa <= 1 else '' }}"
       href="/?{{ sayfalama_taban_qs }}{{ '&' if sayfalama_taban_qs else '' }}sayfa={{ sayfa - 1 }}">&larr; Önceki</a>
    <span>Sayfa {{ sayfa }} / {{ toplam_sayfa }} ({{ toplam_kayit }} kayıt)</span>
    <a class="buton-ikincil {{ 'sf-pasif' if sayfa >= toplam_sayfa else '' }}"
       href="/?{{ sayfalama_taban_qs }}{{ '&' if sayfalama_taban_qs else '' }}sayfa={{ sayfa + 1 }}">Sonraki &rarr;</a>
  </div>
  {% endif %}

</div>
""" + ORTAK_JS + """
</body>
</html>
"""


# ------------------------------------------------------------------
# Detay sayfası şablonu -- "/arac/<sasi_no>" (ORTAK_JS'i kullanır ama
# .sabit-ust'u YOK -- bu sayfada sticky üst bar/veri çek yok. Fatura/gümrük
# tablolarının KENDİ başlıkları yine de sticky (top: 0) olur -- bu sayfada
# .sabit-ust olmadığından --sabit-yukseklik hep 0px kalır, bu da "bu küçük
# popup penceresinin en üstüne yapış" anlamına gelir, zararsız/faydalı bir
# yan etki. Bkz. ORTAK_STIL'deki thead sticky notu.)
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
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-fatura', this)">Filtrele ▾</button></th>
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
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-gumruk', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-gumruk', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-gumruk', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-gumruk', this)">Filtrele ▾</button></th>
        <th><button type="button" class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event, 'tablo-gumruk', this)">Filtrele ▾</button></th>
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
    """Ana sayfa: 8 tıklanabilir özet kartı + TEK bir arama/filtre formu
    (genel arama + Model/Dış Renk/Yakıt Tipi comboboxları + tarih aralığı,
    hepsi AYNI form/TEK "Ara" butonu) -- hepsi AYNI özet liste tablosunu
    doldurur.

    FİLTRE MANTIĞI (2026-09-08, İKİNCİ sürüm): eskiden bir ÖNCELİK
    SIRASI vardı ("model seçiliyse SADECE ona göre ara, metin/tarih YOK
    SAYILIR" gibi) -- kullanıcı "Ara butonu hiç bir filtreye takılmamalı,
    tarih filitreleri bağımsız olmalı" diye haklı olarak şikayet etti.
    ŞİMDİ: ?gorunum=tum ve ?gorunum=ithal (özet kartlarından gelen özel
    görünümler) hâlâ kendi başına, ama geri kalan HER ŞEY (metin, model,
    dış renk, yakıt tipi, tarih aralığı) TEK sorguda VE (AND) mantığıyla
    BİRLİKTE uygulanıyor -- doldurulan alanlar birlikte daraltır, boş
    alan hiç filtre uygulamamış gibi davranır (bkz. BIRLESIK_ARAMA_GOVDESI
    yorumu). Hiçbir alan doldurulmamışsa (ve gorunum da yoksa) varsayılan
    olarak İÇİNDE BULUNULAN AY gösterilir.

    SAYFALAMA (2026-09-08): sonuçlar artık 500'de SESSİZCE kesilmiyor --
    ?sayfa=N ile 500'er 500'er sayfalara bölünüyor (bkz. SAYFA_BOYUTU),
    toplam kayıt sayısına göre "Sayfa X / Y" + Önceki/Sonraki linkleri
    tabloların altında gösteriliyor."""
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
    model_secili = request.args.get("model", "").strip()
    renk_secili = request.args.get("renk", "").strip()
    yakit_secili = request.args.get("yakit", "").strip()
    # "Veri Çek" butonu bir işlemi REDDETTİĞİNDE (bkz. veri_cek_baslat())
    # ?veri_cek_hata=... ile buraya geri yönlendiriyor -- üst barın altında
    # kırmızı bir uyarı şeridi olarak gösteriliyor (bkz. ANA_SAYFA'daki
    # {% if veri_cek_hata %} bloğu).
    veri_cek_hata = request.args.get("veri_cek_hata", "").strip()

    # Hangi sayfadayız (1'den başlar, geçersiz/eksik değer sessizce 1'e
    # düşer) -- bkz. modül üstündeki SAYFA_BOYUTU.
    try:
        sayfa = max(1, int(request.args.get("sayfa", "1")))
    except ValueError:
        sayfa = 1
    sayfa_offset = (sayfa - 1) * SAYFA_BOYUTU

    # Model/Dış Renk/Yakıt Tipi comboboxlarını dolduracak benzersiz
    # değerler -- HER istekte çekiliyor (sayfa yenilendiğinde combobox
    # seçenekleri güncel kalsın diye), veri az olduğu için (birkaç bin
    # araç) performans sorunu yaratmaz. "İl seçince ilçe ona göre dolsun"
    # mantığı: model_secili doluysa Dış Renk/Yakıt Tipi seçenekleri SADECE
    # o modelde var olan değerlerle sınırlanıyor (bkz. sorgulardaki not).
    model_secenekleri = [r["deger"] for r in _sorgu_calistir(MODEL_SECENEKLERI_SORGUSU, [])]
    renk_secenekleri = [r["deger"] for r in _sorgu_calistir(
        RENK_SECENEKLERI_SORGUSU, [model_secili, model_secili]
    )]
    yakit_secenekleri = [r["deger"] for r in _sorgu_calistir(
        YAKIT_SECENEKLERI_SORGUSU, [model_secili, model_secili]
    )]
    # "Tanımsız" (yakit_id NULL -- motor_no'dan tahmin edilemeyen) araç
    # sayısı -- 0 ise combobox'ta bu seçenek hiç gösterilmiyor (bkz. ANA_SAYFA).
    yakit_tanimsiz_sayisi = _sorgu_calistir(YAKIT_TANIMSIZ_SAYISI_SORGUSU, [])[0]["sayi"]

    # Tarih aralığı SADECE hem başlangıç hem bitiş geçerli bir tarihse
    # "aktif" sayılır -- geçersiz/eksikse filtre uygulanmaz (sessizce boş
    # sonuç göstermek yerine, artık diğer alanlarla birlikte çalışabilsin
    # diye eskisi gibi tüm aramayı iptal etmiyoruz).
    tarih_filtresi_var = False
    tarih_bas_sql = dt.date(1900, 1, 1)
    tarih_bit_sql = dt.date(2100, 1, 1)
    if baslangic_deger and bitis_deger:
        try:
            tarih_bas_sql = dt.datetime.strptime(baslangic_deger, "%Y-%m-%d").date()
            tarih_bit_sql = dt.datetime.strptime(bitis_deger, "%Y-%m-%d").date()
            tarih_filtresi_var = True
        except ValueError:
            tarih_bas_sql = dt.date(1900, 1, 1)
            tarih_bit_sql = dt.date(2100, 1, 1)

    herhangi_bir_alan_dolu = bool(
        arama_metni or model_secili or renk_secili or yakit_secili or tarih_filtresi_var
    )

    # Tarih kutucukları HER ZAMAN dolu görünsün -- kullanıcı henüz kendi
    # tarihini girmediyse kutularda bu ayın tarihlerini GÖSTERİYORUZ.
    # UYARI (2026-09-08'de bulunan gerçek hata): bu değerler görünüşte
    # "sadece HTML'e gidiyor" gibi dursa da, GERÇEKTE <input name="baslangic">
    # kutusunun value'su olarak basılıyor -- yani kullanıcı hiç dokunmasa
    # bile, formun HERHANGİ bir şekilde gönderilmesinde (Model seçince
    # otomatik gönderim, ya da Ara'ya basmak) bu ayın tarihleri SESSİZCE
    # tarih filtresi olarak katılıyordu. Sonuç: "Model seçtim ama yanlış/eksik
    # sonuç geliyor" şikayeti -- kullanıcı sadece Model'e göre bakmak
    # isterken, görünmeden "VE bu ay" filtresi de uygulanıyordu. ÇÖZÜM:
    # ORTAK_JS'teki tarihDokunuldu bayrağı -- kullanıcı tarih kutularına
    # GERÇEKTEN dokunmadıysa (yazı girmedi, hızlı tarih butonu/listesi
    # kullanmadıysa), form gönderilirken bu kutular JS tarafından submit
    # anında boşaltılıyor (bkz. ORTAK_JS'teki submit event listener'ı) --
    # o yüzden kutuların GÖRÜNÜŞTE dolu olması artık arama sonucunu
    # etkilemiyor, sadece kullanıcıya "bu ayı görüyorsun" bilgisini veriyor.
    if not baslangic_deger and not bitis_deger:
        baslangic_gosterim = ay_baslangic.isoformat()
        bitis_gosterim = ay_bitis.isoformat()
    else:
        baslangic_gosterim = baslangic_deger
        bitis_gosterim = bitis_deger

    sonuclar = []
    toplam_kayit = 0
    arama_yapildi = False
    baslik_metni = "Araç listesi"

    if gorunum == "tum":
        arama_yapildi = True
        sonuclar = _sorgu_calistir(TUM_ARACLAR_SORGUSU, [SAYFA_BOYUTU, sayfa_offset])
        toplam_kayit = _sorgu_calistir(TUM_ARACLAR_SAYISI_SORGUSU, [])[0]["sayi"]
        baslik_metni = "Tüm araçlar"
    elif gorunum == "ithal":
        arama_yapildi = True
        sonuclar = _sorgu_calistir(ITHAL_ARACLAR_SORGUSU, [SAYFA_BOYUTU, sayfa_offset])
        toplam_kayit = _sorgu_calistir(ITHAL_ARACLAR_SAYISI_SORGUSU, [])[0]["sayi"]
        baslik_metni = "Gümrük kaydı olan araçlar"
    elif herhangi_bir_alan_dolu:
        # Metin, model, dış renk, yakıt tipi ve tarih aralığı -- hangileri
        # doluysa hepsi BİRLİKTE (VE mantığıyla) uygulanıyor (bkz.
        # BIRLESIK_ARAMA_GOVDESI'nin üstündeki yorum). Ara butonu ve tarih
        # filtresi artık başka bir filtreye "takılıp" yok sayılmıyor.
        arama_yapildi = True
        joker = "%" + arama_metni + "%"
        govde_parametreleri = [
            model_secili, model_secili,
            renk_secili, renk_secili,
            yakit_secili, yakit_secili, yakit_secili,
            arama_metni, joker, joker, joker, joker, joker, joker, joker,
            not tarih_filtresi_var, tarih_bas_sql, tarih_bit_sql,
        ]
        sonuclar = _sorgu_calistir(
            BIRLESIK_ARAMA_SORGUSU, govde_parametreleri + [SAYFA_BOYUTU, sayfa_offset]
        )
        toplam_kayit = _sorgu_calistir(BIRLESIK_ARAMA_SAYISI_SORGUSU, govde_parametreleri)[0]["sayi"]

        parcalar = []
        if model_secili:
            parcalar.append("Model: %s" % model_secili)
        if renk_secili:
            parcalar.append("Dış Renk: %s" % renk_secili)
        if yakit_secili == YAKIT_TANIMSIZ_DEGER:
            parcalar.append("Yakıt: Tanımsız")
        elif yakit_secili:
            parcalar.append("Yakıt: %s" % yakit_secili)
        if arama_metni:
            parcalar.append('"%s"' % arama_metni)
        if tarih_filtresi_var:
            parcalar.append("%s - %s arası" % (baslangic_deger, bitis_deger))
        baslik_metni = "Arama sonucu (%s)" % ", ".join(parcalar) if parcalar else "Araç listesi"
    else:
        # Hiçbir alan doldurulmamış: sayfa ilk açıldığında otomatik olarak
        # BU AYI göster (boş "araç listesi" yerine hemen işe yarar bir
        # görünüm) -- bu da aynı birleşik sorgudan geçiyor, sadece tarih
        # aralığı Python tarafından "bu ay" olarak dolduruluyor.
        arama_yapildi = True
        joker = "%%"
        govde_parametreleri = [
            "", "", "", "", "", "", "",
            "", joker, joker, joker, joker, joker, joker, joker,
            False, ay_baslangic, ay_bitis,
        ]
        sonuclar = _sorgu_calistir(
            BIRLESIK_ARAMA_SORGUSU, govde_parametreleri + [SAYFA_BOYUTU, sayfa_offset]
        )
        toplam_kayit = _sorgu_calistir(BIRLESIK_ARAMA_SAYISI_SORGUSU, govde_parametreleri)[0]["sayi"]
        baslik_metni = "Bu ay"

    # Sayfalama: mevcut filtreleri (sayfa numarası HARİÇ) query string'e
    # çevirip Önceki/Sonraki linklerinin altına ekliyoruz -- bkz. ANA_SAYFA
    # şablonundaki sayfalama bloğu.
    toplam_sayfa = max(1, -(-toplam_kayit // SAYFA_BOYUTU))  # yukarı yuvarlama
    sayfa = min(sayfa, toplam_sayfa)
    mevcut_parametreler = {}
    if gorunum:
        mevcut_parametreler["gorunum"] = gorunum
    if arama_metni:
        mevcut_parametreler["q"] = arama_metni
    if model_secili:
        mevcut_parametreler["model"] = model_secili
    if renk_secili:
        mevcut_parametreler["renk"] = renk_secili
    if yakit_secili:
        mevcut_parametreler["yakit"] = yakit_secili
    if baslangic_deger:
        mevcut_parametreler["baslangic"] = baslangic_deger
    if bitis_deger:
        mevcut_parametreler["bitis"] = bitis_deger
    sayfalama_taban_qs = urlencode(mevcut_parametreler)

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
        toplam_kayit=toplam_kayit,
        sayfa=sayfa,
        toplam_sayfa=toplam_sayfa,
        sayfalama_taban_qs=sayfalama_taban_qs,
        model_secenekleri=model_secenekleri,
        renk_secenekleri=renk_secenekleri,
        yakit_secenekleri=yakit_secenekleri,
        model_secili=model_secili,
        renk_secili=renk_secili,
        yakit_secili=yakit_secili,
        yakit_tanimsiz_deger=YAKIT_TANIMSIZ_DEGER,
        yakit_tanimsiz_sayisi=yakit_tanimsiz_sayisi,
        veri_cek_hata=veri_cek_hata,
        tarih_kullanici_secti=tarih_filtresi_var,
    )


@app.route("/veri-cek", methods=["POST"])
def veri_cek_baslat():
    """"Veri Çek" formunun POST hedefi. Arka planda etl.run_range()'i
    başlatıp HEMEN "/" adresine geri döner -- run_range bitene kadar
    beklemez (bkz. yukarıdaki "Veri Çek butonu" bölümündeki ÖĞRENME NOTU).
    Tarihler geçersizse, başlangıç bitişten sonraysa, ya da zaten bir
    çekim çalışıyorsa YENİ bir çekim BAŞLATMAZ -- kullanıcıya
    ?veri_cek_hata=... ile bir uyarı mesajı gösterip "/" adresine döner.

    NOT: 28 günden uzun aralıklar burada AYRICA parçalanmıyor -- etl.py
    zaten run_range() içinde bunu otomatik yapıyor (varsayılan
    chunk_days=28), o mantık burada TEKRAR YAZILMADI (tek doğru kaynak
    etl.py)."""
    baslangic_metin = request.form.get("baslangic", "").strip()
    bitis_metin = request.form.get("bitis", "").strip()

    try:
        baslangic = dt.datetime.strptime(baslangic_metin, "%Y-%m-%d").date()
        bitis = dt.datetime.strptime(bitis_metin, "%Y-%m-%d").date()
    except ValueError:
        return redirect(url_for(
            "anasayfa",
            veri_cek_hata="Veri çekme başlatılamadı: geçerli bir başlangıç/bitiş tarihi girin.",
        ))

    if baslangic > bitis:
        return redirect(url_for(
            "anasayfa",
            veri_cek_hata="Veri çekme başlatılamadı: başlangıç tarihi bitiş tarihinden sonra olamaz.",
        ))

    with _VERI_CEK_KILIT:
        if _VERI_CEK_DURUMU["calisiyor"]:
            return redirect(url_for(
                "anasayfa",
                veri_cek_hata="Zaten bir veri çekme işlemi çalışıyor -- bitmesini bekleyin.",
            ))
        _VERI_CEK_DURUMU.update({
            "calisiyor": True,
            "baslangic": baslangic.isoformat(),
            "bitis": bitis.isoformat(),
            "eklenen": None,
            "atlanan": None,
            "basarisiz_parca": None,
            "hata": None,
            "baslama_zamani": dt.datetime.now().strftime("%H:%M:%S"),
            "bitis_zamani": None,
        })

    thread = threading.Thread(target=_veri_cek_calistir, args=(baslangic, bitis), daemon=True)
    thread.start()

    return redirect(url_for("anasayfa"))


@app.route("/veri-cek/durum")
def veri_cek_durum():
    """Üst bardaki JS'in (bkz. ORTAK_JS: _veriCekDurumGuncelle) birkaç
    saniyede bir sorguladığı JSON durum uç noktası. _VERI_CEK_KILIT ile
    korunan global sözlüğü olduğu gibi JSON olarak döner."""
    with _VERI_CEK_KILIT:
        return jsonify(dict(_VERI_CEK_DURUMU))


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
    # host="0.0.0.0" (2026-09-08: bilerek ağa açıldı -- Engin'in isteğiyle,
    # ağdaki başka bir cihazdan http://<bu bilgisayarın IP'si>:5050 ile
    # erişilebilsin diye). UYARI: içeride fatura/fiyat gibi hassas veri var
    # ve burada HİÇBİR giriş/şifre koruması YOK -- aynı ağdaki (Wi-Fi/LAN)
    # HERKES bu adrese girip görebilir. Windows Firewall'da 5050 portu için
    # "gelen bağlantılara izin ver" kuralı da AYRICA gerekiyor, kod bunu
    # kendi başına açamaz. Tekrar sadece bu bilgisayardan erişilir hale
    # getirmek istersen host="127.0.0.1" olarak geri al.
    print("Tarayıcıda şu adresi aç: http://localhost:5050")
    print("Ağdaki diğer cihazlardan: http://<bu bilgisayarın IP'si>:5050")
    app.run(host="0.0.0.0", port=5050, debug=False)

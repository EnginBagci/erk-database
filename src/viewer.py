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

SAYFA YAPISI (4. tasarım):
  1) Ana sayfa ("/"): üstte özet kartları (toplam araç, toplam fatura,
     ithal araç, bu ay eklenen). Altında şase VEYA tarih aralığı ile
     arama yapılır -- tarih aralığı varsayılan olarak İÇİNDE BULUNULAN
     AYIN başlangıcı/bitişi ile gelir ve sayfa ilk açıldığında otomatik
     bu ayı gösterir; yanında Dün/Bu Ay/Geçen Ay/Bu Yıl hızlı butonları
     var. Sonuç HER ZAMAN tek bir listeleme tablosunda gösterilir (şase,
     motor no, model, plaka, fatura no/tarihi, toplam gibi ÖZET
     bilgiler). Bu tablo, sonuç bulunamadığında bile başlıklarıyla
     birlikte sabit durur -- boş diye kaybolmaz.
  2) Bir satıra tıklanınca ayrı bir DETAY sayfası ("/arac/<sasi_no>")
     KÜÇÜK, AYRI BİR PENCEREDE (popup) açılır -- ana sayfa (liste/arama)
     OLDUĞU GİBİ, hiç etkilenmeden kalır (ne yeni sekme ne de üzerine
     yazma -- kullanıcı özellikle "ana sayfa sabit kalsın, ufak bir
     pencerede göster" istedi). O aracın TÜM bilgileri (özellikler, tüm
     alış faturaları, gümrük bilgisi) o küçük pencerede gösterilir.

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

# ---- Ana sayfadaki ÖZET liste tablosu için iki sorgu -------------------
# İkisi de AYNI kolonları (aynı sırayla) döndürüyor ki tek bir HTML tablo
# şablonu her ikisi için de kullanılabilsin.
#
# ÖĞRENME NOTU (LEFT JOIN farkı): Şase araması araclar tablosundan başlar
# ve alis_faturalari'na LEFT JOIN yapar -- böylece henüz faturası
# işlenmemiş bir araç bile (varsa) listede görünür. Tarih aralığı araması
# ise alis_faturalari'ndan başlar (JOIN, LEFT JOIN değil) çünkü zaten
# "bu tarih aralığında FATURASI olan araçlar" aranıyor.
SASI_LISTESI_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no,
        c.adi AS carline_adi, a.model_yili,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
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
    LEFT JOIN alis_faturalari af ON af.arac_id = a.id
    WHERE a.sasi_no = %s
    ORDER BY af.fatura_tarihi DESC NULLS LAST
"""

TARIH_LISTESI_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no,
        c.adi AS carline_adi, a.model_yili,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
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
    WHERE af.fatura_tarihi BETWEEN %s AND %s
    ORDER BY af.fatura_tarihi DESC
    LIMIT 500
"""
# UYARI: LIMIT 500 kasıtlı -- geniş bir tarih aralığı girilirse (örn.
# 2020-2026) sayfa binlerce satırla yavaşlamasın diye. Sıralama/filtreleme
# sadece ekrandaki (en fazla 500) satır üzerinde çalışır.

# ---- Detay sayfası ("/arac/<sasi_no>") için üç sorgu --------------------
SASI_SORGUSU = """
    SELECT
        a.sasi_no, a.motor_no, a.model_yili,
        c.adi AS carline_adi, c.kod AS carline_kod,
        s.kod AS spec_kodu,
        o.no AS ocn_no, o.adi AS ocn_adi,
        dr.adi AS dis_renk, ic.adi AS ic_renk,
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

# ---- Ana sayfa üstündeki özet kartları için tek sorgu -------------------
# GERİ EKLENDİ: bu kartlar 2. tasarımda kaldırılmıştı, kullanıcı
# "kaldırmanı istemedim" deyince tekrar eklendi.
ISTATISTIK_SORGUSU = """
    SELECT
        (SELECT COUNT(*) FROM araclar) AS toplam_arac,
        (SELECT COUNT(*) FROM alis_faturalari) AS toplam_fatura,
        (SELECT COUNT(DISTINCT arac_id) FROM gumruk_bilgileri) AS ithal_arac,
        (SELECT COUNT(*) FROM alis_faturalari
         WHERE fatura_tarihi >= date_trunc('month', CURRENT_DATE)) AS bu_ay_fatura
"""


def _sorgu_calistir(sql, params):
    """Tek bir SELECT çalıştırıp sonucu dict listesi olarak döner.
    Küçük bir yardımcı -- yukarıdaki sorguların hepsi aynı şekilde
    çalıştırıldığı için tekrar yazmamak adına buraya alındı."""
    with db.get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def _istatistikleri_al():
    """Üstteki 4 kartın sayılarını tek sorguda getirir."""
    sonuc = _sorgu_calistir(ISTATISTIK_SORGUSU, [])
    return sonuc[0] if sonuc else {
        "toplam_arac": 0, "toplam_fatura": 0, "ithal_arac": 0, "bu_ay_fatura": 0,
    }


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

  /* Özet kartları -- geri eklendi */
  .kart-satiri { display: flex; gap: 16px; flex-wrap: wrap; margin-bottom: 24px; }
  .kart {
    flex: 1 1 200px;
    background: #fff;
    border-radius: 8px;
    padding: 16px 18px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    border-top: 4px solid #ccc;
  }
  .kart .sayi { font-size: 28px; font-weight: 700; line-height: 1.2; }
  .kart .etiket { font-size: 12px; color: #6b7280; margin-top: 4px; }
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
  label { display: inline-block; min-width: 90px; font-size: 13px; margin-top: 10px; }
  input[type=text], input[type=date] {
    padding: 7px 9px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px;
  }
  button {
    padding: 7px 18px; border: 0; background: #2563eb; color: #fff;
    border-radius: 4px; cursor: pointer; font-size: 13px; margin-top: 10px;
  }
  button:hover { background: #1d4ed8; }

  /* Dün / Bu Ay / Geçen Ay / Bu Yıl kısayol butonları -- ana "Ara"
     butonundan ayırt edilsin diye daha küçük ve gri/ikincil renkte. */
  .hizli-tarih-butonlari { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
  .hizli-tarih-butonlari button {
    background: #eef1f5; color: #1f2937; border: 1px solid #cbd5e1;
    padding: 5px 12px; font-size: 12px; margin-top: 0;
  }
  .hizli-tarih-butonlari button:hover { background: #e2e8f0; }

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
// ÖĞRENME NOTU: Bu iki fonksiyon SAYFA YENİDEN YÜKLENMEDEN çalışır --
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
  if (tur === 'dun') {
    var dun = new Date(yil, ay, bugun.getDate() - 1);
    baslangic = bitis = formatla(dun);
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
    <div class="kart mavi">
      <div class="sayi">{{ istatistik.toplam_arac }}</div>
      <div class="etiket">TOPLAM ARAÇ</div>
    </div>
    <div class="kart yesil">
      <div class="sayi">{{ istatistik.toplam_fatura }}</div>
      <div class="etiket">TOPLAM ALIŞ FATURASI</div>
    </div>
    <div class="kart turuncu">
      <div class="sayi">{{ istatistik.ithal_arac }}</div>
      <div class="etiket">İTHAL (GÜMRÜK KAYDI OLAN) ARAÇ</div>
    </div>
    <div class="kart mor">
      <div class="sayi">{{ istatistik.bu_ay_fatura }}</div>
      <div class="etiket">BU AY EKLENEN FATURA</div>
    </div>
  </div>

  <div class="arama-kartlari">
    <form class="arama-formu" method="get">
      <b>Şasi ile ara</b><br>
      <label>Şasi no:</label>
      <input type="text" name="sasi" value="{{ sasi_deger }}" placeholder="örn. KMHM341B1TA123333">
      <button type="submit">Ara</button>
    </form>

    <form class="arama-formu" method="get" id="tarih-arama-formu">
      <b>Tarih aralığına göre ara</b><br>
      <label>Başlangıç:</label>
      <input type="date" name="baslangic" id="baslangic-girdi" value="{{ baslangic_deger }}">
      &nbsp;
      <label>Bitiş:</label>
      <input type="date" name="bitis" id="bitis-girdi" value="{{ bitis_deger }}">
      <button type="submit">Ara</button>
      <div class="hizli-tarih-butonlari">
        <button type="button" onclick="tarihAyarla('dun')">Dün</button>
        <button type="button" onclick="tarihAyarla('bu-ay')">Bu Ay</button>
        <button type="button" onclick="tarihAyarla('gecen-ay')">Geçen Ay</button>
        <button type="button" onclick="tarihAyarla('bu-yil')">Bu Yıl</button>
      </div>
    </form>
  </div>

  <h2>
    {% if arama_yapildi %}
      Arama sonucu ({{ sonuclar|length }} kayıt{{ ", en fazla 500 gösteriliyor" if sonuclar|length >= 500 else "" }})
    {% else %}
      Araç listesi
    {% endif %}
  </h2>
  <p class="bilgi-notu">Bir satıra tıklayınca o aracın tüm detayları (özellikler, faturalar, gümrük bilgisi) küçük, ayrı bir PENCEREDE açılır -- bu sayfa olduğu gibi kalır.</p>

  <div class="tablo-sarmalayici">
  <table id="tablo-sonuclar">
    <thead>
      <tr class="baslik-satiri" onclick="event.target.tagName === 'TH' && sirala('tablo-sonuclar', Array.from(event.target.parentNode.children).indexOf(event.target))">
        <th>Şase</th><th>Motor No</th><th>Model</th><th>Model Yılı</th><th>Dış Renk</th><th>İç Renk</th><th>Plaka</th><th>Fatura No</th><th>Fatura Tarihi</th><th>Toplam</th>
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
        <td>{{ r.plaka or "-" }}</td>
        <td>{{ r.fatura_no or "-" }}</td>
        <td>{{ r.fatura_tarihi or "-" }}</td>
        <td>{{ "%.2f"|format(r.toplam) if r.toplam is not none else "-" }}</td>
      </tr>
      {% endfor %}
    {% else %}
      <tr class="bos-satiri">
        <td colspan="10">
          {% if arama_yapildi %}
            Bu aramayla eşleşen kayıt bulunamadı.
          {% else %}
            Henüz arama yapmadınız -- yukarıdan şase numarası girin ya da bir tarih aralığı seçin.
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
    """Ana sayfa: şase VEYA tarih aralığı arama formları + HER ZAMAN
    görünen tek bir özet liste tablosu. Hangi form gönderildiyse (URL'deki
    ?sasi=... ya da ?baslangic=...&bitis=... parametrelerine bakarak)
    ilgili sorguyu çalıştırıp sonucu bu tabloya koyuyoruz.

    ÖĞRENME NOTU (varsayılan tarih): Tarih kutuları hiçbir zaman boş
    görünmesin diye (ve sayfa ilk açıldığında hemen işe yarasın diye)
    parametre hiç verilmemişse varsayılan olarak İÇİNDE BULUNULAN AYIN
    ilk günü / son günü kullanılıyor -- hem kutucuklarda GÖRÜNÜR hem de
    (hiç arama yapılmamışsa) bu ayla otomatik arama yapılır."""
    istatistik = _istatistikleri_al()

    bugun = dt.date.today()
    ay_baslangic = bugun.replace(day=1)
    ay_bitis = bugun.replace(day=calendar.monthrange(bugun.year, bugun.month)[1])

    sasi_deger = request.args.get("sasi", "").strip()
    baslangic_deger = request.args.get("baslangic", "").strip()
    bitis_deger = request.args.get("bitis", "").strip()

    hicbir_parametre_yok = not sasi_deger and not baslangic_deger and not bitis_deger

    # Tarih kutucukları HER ZAMAN dolu görünsün -- kullanıcı henüz kendi
    # tarihini girmediyse (baslangic_deger/bitis_deger boşsa) kutularda bu
    # ayın tarihlerini GÖSTERİYORUZ (aşağıdaki değişkenler sadece HTML'e
    # gidiyor, arama mantığını etkilemiyor).
    if not baslangic_deger and not bitis_deger:
        baslangic_gosterim = ay_baslangic.isoformat()
        bitis_gosterim = ay_bitis.isoformat()
    else:
        baslangic_gosterim = baslangic_deger
        bitis_gosterim = bitis_deger

    sonuclar = []
    arama_yapildi = False

    if sasi_deger:
        arama_yapildi = True
        sonuclar = _sorgu_calistir(SASI_LISTESI_SORGUSU, [sasi_deger])
    elif baslangic_deger and bitis_deger:
        try:
            b = dt.datetime.strptime(baslangic_deger, "%Y-%m-%d").date()
            e = dt.datetime.strptime(bitis_deger, "%Y-%m-%d").date()
            arama_yapildi = True
            sonuclar = _sorgu_calistir(TARIH_LISTESI_SORGUSU, [b, e])
        except ValueError:
            pass  # geçersiz tarih girildiyse sessizce boş sonuç göster
    elif hicbir_parametre_yok:
        # Sayfa hiç parametresiz ilk açıldığında: otomatik olarak BU AYI
        # göster (boş "araç listesi" yerine hemen işe yarar bir görünüm).
        arama_yapildi = True
        sonuclar = _sorgu_calistir(TARIH_LISTESI_SORGUSU, [ay_baslangic, ay_bitis])

    return render_template_string(
        ANA_SAYFA,
        istatistik=istatistik,
        sasi_deger=sasi_deger,
        baslangic_deger=baslangic_gosterim,
        bitis_deger=bitis_gosterim,
        sonuclar=sonuclar,
        arama_yapildi=arama_yapildi,
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

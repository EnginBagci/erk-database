"""
Basit Görüntüleyici Şablonu - ornek_uygulama.py

Bu dosya TEK BAŞINA çalışır (veritabanı gerekmez) -- amacı, ortak.py'deki
görsel tasarımın nasıl kullanılacağını göstermek. Yeni bir küçük
görüntüleme aracı yaparken bu dosyayı kopyalayıp:
  1) ORNEK_KAYITLAR listesini gerçek veri kaynağınla (DB sorgusu, CSV,
     API çağrısı, ne olursa) değiştir,
  2) KOLONLAR listesini kendi alanlarına göre güncelle,
  3) detay sayfasındaki alanları güncelle.

Çalıştırma: python ornek_uygulama.py
Sonra tarayıcıda: http://localhost:5051

DESEN (erk-database/src/viewer.py'den alındı):
  - Liste sayfası ("/"): arama formu/formları + HER ZAMAN görünen, başlıklı
    tek bir tablo (veri yoksa bile başlıklar kaybolmaz, sadece "kayıt yok"
    yazan bir satır görünür).
  - Detay sayfası ("/kayit/<id>"): bir satıra tıklanınca o kaydın TÜM
    bilgilerini gösteren ayrı sayfa.
  - Sütun başlığına tıklayınca sıralama, filtre kutularına yazınca anlık
    filtreleme (tarayıcıda, sayfa yenilenmeden -- bkz. ortak.py ORTAK_JS).
"""
from flask import Flask, request, render_template_string

from ortak import ORTAK_STIL, ORTAK_JS

app = Flask(__name__)

# ------------------------------------------------------------------
# ÖRNEK VERİ -- gerçek projede burası bir veritabanı sorgusuyla
# (örn. erk-database'deki db.py + SQL gibi) değiştirilir.
# ------------------------------------------------------------------
ORNEK_KAYITLAR = [
    {"id": 1, "ad": "Ahmet Yılmaz", "kategori": "Motor", "tarih": "2026-08-01", "tutar": 1250.50},
    {"id": 2, "ad": "Mehmet Demir", "kategori": "Kaporta", "tarih": "2026-08-03", "tutar": 3400.00},
    {"id": 3, "ad": "Ayşe Kaya", "kategori": "Motor", "tarih": "2026-08-15", "tutar": 890.75},
]

# Liste tablosunda gösterilecek kolonlar: (başlık, kayıt sözlüğündeki anahtar)
KOLONLAR = [
    ("Ad", "ad"),
    ("Kategori", "kategori"),
    ("Tarih", "tarih"),
    ("Tutar", "tutar"),
]


def _kayitlari_ara(arama_metni):
    """ÖRNEK arama fonksiyonu -- gerçek projede bu bir SQL WHERE ... LIKE
    ya da benzeri bir sorguya dönüşür. Burada basitçe Python listesinde
    "ad" alanında arıyor."""
    if not arama_metni:
        return ORNEK_KAYITLAR
    arama_kucuk = arama_metni.strip().lower()
    return [k for k in ORNEK_KAYITLAR if arama_kucuk in k["ad"].lower()]


def _kayit_bul(kayit_id):
    for k in ORNEK_KAYITLAR:
        if k["id"] == kayit_id:
            return k
    return None


# ------------------------------------------------------------------
# Liste sayfası şablonu
# ------------------------------------------------------------------
LISTE_SAYFASI = """
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>Örnek Görüntüleyici</title>
""" + ORTAK_STIL + """
</head>
<body>

<div class="ust-serit">
  <div>
    <h1>Örnek Görüntüleyici</h1>
    <div class="alt-yazi">Şablon örneği -- gerçek veri yok, sadece bellekte 3 örnek kayıt var.</div>
  </div>
</div>

<div class="icerik">

  <div class="arama-kartlari">
    <form class="arama-formu" method="get">
      <b>İsimle ara</b><br>
      <label>Ad:</label>
      <input type="text" name="ara" value="{{ arama_metni }}" placeholder="örn. Ahmet">
      <button type="submit">Ara</button>
    </form>
  </div>

  <h2>Kayıt listesi ({{ kayitlar|length }} kayıt)</h2>
  <p class="bilgi-notu">Bir satıra tıklayınca o kaydın detayları küçük, ayrı bir PENCEREDE açılır -- bu sayfa olduğu gibi kalır.</p>

  <div class="tablo-sarmalayici">
  <table id="tablo-liste">
    <thead>
      <tr class="baslik-satiri" onclick="event.target.tagName === 'TH' && sirala('tablo-liste', Array.from(event.target.parentNode.children).indexOf(event.target))">
        {% for baslik, anahtar in kolonlar %}<th>{{ baslik }}</th>{% endfor %}
      </tr>
      <tr class="filtre-satiri">
        {% for baslik, anahtar in kolonlar %}<th><input type="text" oninput="filtrele('tablo-liste')" placeholder="ara..."></th>{% endfor %}
      </tr>
    </thead>
    <tbody data-dolu="{{ '1' if kayitlar else '0' }}">
    {% if kayitlar %}
      {% for k in kayitlar %}
      <tr class="veri-satiri" onclick="satiraGit('/kayit/{{ k.id }}')">
        <td><a href="/kayit/{{ k.id }}" onclick="detayPenceresiAc('/kayit/{{ k.id }}'); return false;">{{ k.ad }}</a></td>
        <td>{{ k.kategori }}</td>
        <td>{{ k.tarih }}</td>
        <td>{{ "%.2f"|format(k.tutar) }}</td>
      </tr>
      {% endfor %}
    {% else %}
      <tr class="bos-satiri"><td colspan="{{ kolonlar|length }}">Bu aramayla eşleşen kayıt bulunamadı.</td></tr>
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
# Detay sayfası şablonu
# ------------------------------------------------------------------
DETAY_SAYFASI = """
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>Kayıt Detayı</title>
""" + ORTAK_STIL + """
</head>
<body>

<div class="ust-serit">
  <div>
    <h1>Kayıt Detayı</h1>
    <div class="alt-yazi">Şablon örneği</div>
  </div>
  <a href="/">&larr; Listeye dön</a>
</div>

<div class="icerik">
{% if kayit %}
  <div class="tablo-sarmalayici">
  <table class="detay-bilgi-tablosu">
    <tr><th>Ad</th><td>{{ kayit.ad }}</td></tr>
    <tr><th>Kategori</th><td>{{ kayit.kategori }}</td></tr>
    <tr><th>Tarih</th><td>{{ kayit.tarih }}</td></tr>
    <tr><th>Tutar</th><td>{{ "%.2f"|format(kayit.tutar) }}</td></tr>
  </table>
  </div>
{% else %}
  <p class="not-bulundu">Kayıt bulunamadı.</p>
{% endif %}
</div>
""" + ORTAK_JS + """
</body>
</html>
"""


@app.route("/")
def liste():
    arama_metni = request.args.get("ara", "").strip()
    kayitlar = _kayitlari_ara(arama_metni)
    return render_template_string(
        LISTE_SAYFASI, kayitlar=kayitlar, kolonlar=KOLONLAR, arama_metni=arama_metni
    )


@app.route("/kayit/<int:kayit_id>")
def detay(kayit_id):
    kayit = _kayit_bul(kayit_id)
    return render_template_string(DETAY_SAYFASI, kayit=kayit)


if __name__ == "__main__":
    print("Tarayıcıda şu adresi aç: http://localhost:5051")
    app.run(host="127.0.0.1", port=5051, debug=False)

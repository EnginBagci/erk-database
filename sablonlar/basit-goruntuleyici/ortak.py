"""
Basit Görüntüleyici Şablonu - ortak.py

Bu dosya `erk-database/src/viewer.py` içinde geliştirilen görsel tasarımın
(koyu lacivert üst şerit, arama kartları, her zaman görünen başlıklı
tablo, sıralama/filtreleme) PROJEDEN BAĞIMSIZ halidir. Herhangi bir
veritabanına, tabloya ya da şemaya referans vermez -- sadece HTML/CSS/JS.

Kullanımı: yeni bir küçük görüntüleme aracı yazarken bu dosyayı olduğu
gibi kopyala, `ornek_uygulama.py`'deki gibi kendi Python string'lerinin
(sayfa şablonlarının) içine ORTAK_STIL ve ORTAK_JS'i ekle.

ÖĞRENME NOTU: Bu iki değişken (ORTAK_STIL, ORTAK_JS) düz metin (string) --
Flask'a özel bir şey değiller. render_template_string ile birlikte
kullanılan HTML şablonunun İÇİNE Python string birleştirmesiyle (+)
ekleniyorlar. Örneğin:
    SAYFA = "<html>...</html>"  # şablonun geri kalanı
    SAYFA = "<head>" + ORTAK_STIL + "</head><body>...</body></html>"
"""

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

  /* Üstte özet/istatistik kartları göstermek istersen (opsiyonel --
     erk-database'de "Toplam Araç", "Bu Ay Eklenen Fatura" gibi sayılar
     için kullanılıyor). Kullanmayan projeler bu bloğu HTML'e hiç
     eklemeyebilir, CSS'te durması zararsız.
     TIKLANABİLİR KART DESENİ: her kart bir <a class="kart-link"
     href="/?..."> ile SARMALANIR -- kart görünümü (.kart) linkin İÇİNDE.
     Böylece bir karta tıklamak, o kartın temsil ettiği filtreyle (örn.
     bu ayın tarih aralığı, ya da özel bir "gorunum" parametresi) ana
     sayfaya gidip alttaki tabloyu otomatik doldurur -- erk-database'de
     böyle kullanılıyor (bkz. viewer.py ANA_SAYFA şablonundaki kart-link
     href'leri: "/?gorunum=tum", "/?baslangic=...&bitis=..." gibi). */
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
  /* ÖNEMLİ: label'a sabit min-width VERME -- "Başlangıç:" gibi uzun ve
     "Bitiş:" gibi kısa etiketler aynı forma girdiğinde, sabit bir
     min-width kısa etiketin yanında kullanılmayan boş bir alan bırakır
     (erk-database'de bu boşluk fark edilip düzeltildi). Etiket kendi
     metni kadar yer kaplasın, girdiye küçük sabit bir boşlukla yapışsın. */
  label { display: inline-block; font-size: 13px; margin-top: 10px; margin-right: 6px; }
  input[type=text], input[type=date] {
    padding: 7px 9px; border: 1px solid #cbd5e1; border-radius: 4px; font-size: 13px;
  }
  button {
    padding: 7px 18px; border: 0; background: #2563eb; color: #fff;
    border-radius: 4px; cursor: pointer; font-size: 13px; margin-top: 10px;
  }
  button:hover { background: #1d4ed8; }

  /* Tek kutulu genel arama formları için: etiket + metin kutusu + buton
     aynı satırda, metin kutusu (input) kalan tüm genişliği doldursun diye
     flex ile büyütülüyor -- input'a width vermeden bırakılırsa tarayıcı
     varsayılanı çok dar kalıyor (erk-database'de "ara kutusu çok ufak
     kalmış" diye düzeltildi). Bu sınıfı genel arama formunun etiket+
     girdi+buton'unu saran bir <div>'e koy. */
  .genel-arama-satiri { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-top: 10px; }
  .genel-arama-satiri label { margin-top: 0; margin-right: 0; }
  .genel-arama-satiri input[type=text] { flex: 1 1 240px; min-width: 200px; }
  .genel-arama-satiri button { margin-top: 0; }

  /* Bir arama formunda "Ara" butonunun YANINA hızlı kısayol butonları
     (örn. Dün/Bu Ay/Geçen Ay/Bu Yıl) koymak istersen bu iki sınıfı
     kullan -- ALTINA değil, AYNI SATIRA gelsinler diye tek bir flex
     satırına konuyorlar (erk-database'de tarih aralığı formunda böyle
     kullanılıyor, bkz. viewer.py). */
  .buton-satiri { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; margin-top: 10px; }
  .buton-satiri button { margin-top: 0; }
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
  .detay-bilgi-tablosu td:first-child, .detay-bilgi-tablosu th:first-child { font-weight: 600; width: 160px; background: #f8f9fb; }
</style>
"""

ORTAK_JS = """
<script>
// ÖĞRENME NOTU: Bu fonksiyonlar SAYFA YENİDEN YÜKLENMEDEN çalışır --
// hiçbir sunucuya/veritabanına gitmez, sadece o an ekranda olan <table>
// satırlarını tarayıcının kendi belleğinde yeniden sıralar / gizler.
// Herhangi bir projeye kopyalanabilir -- kolon adı/veri şekli bilmez,
// sadece <table id="..."> yapısına (baslik-satiri + filtre-satiri +
// tbody[data-dolu] + tr.veri-satiri) bakar.

// Sütun başlığına tıklayınca çağrılır. Tablo "bos" (veri yok, sadece
// placeholder satırı) ise hiçbir şey yapmaz.
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
// ÖNEMLİ: "_blank" yerine bir PENCERE ADI ("detaySayfasi") + genişlik/
// yükseklik veriyoruz -- bu, tarayıcının YENİ SEKME değil gerçek küçük
// bir pencere açmasını sağlıyor. Ana sayfa (liste/arama) olduğu sekmede
// HİÇ DEĞİŞMEDEN kalır (bu, erk-database projesinde açıkça istenen
// davranış: "ana sayfa sabit kalsın, ufak bir pencerede detay göster").
function detayPenceresiAc(url) {
  var genislik = 950, yukseklik = 750;
  var sol = Math.max(0, (window.screen.width - genislik) / 2);
  var ust = Math.max(0, (window.screen.height - yukseklik) / 2);
  window.open(
    url,
    'detaySayfasi',
    'width=' + genislik + ',height=' + yukseklik + ',left=' + sol + ',top=' + ust +
    ',resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=no,status=no'
  );
}

// Satırın onclick'inden çağrılır. Satırın içindeki bir linke tıklandıysa
// (o linkin kendi onclick'i zaten detayPenceresiAc'ı çağırıp false
// dönüyor) burada tekrar açmaya çalışmayalım diye kontrol ediyoruz.
function satiraGit(url) {
  if (event.target.tagName === 'A') return;
  detayPenceresiAc(url);
}
</script>
"""

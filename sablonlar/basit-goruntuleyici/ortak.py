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
    /* overflow-x: auto -- geniş tablo (çok sütunlu) dar ekranda yatay
       kaydırılabilsin diye. NOT: bu satırı tablo başlığını (thead) sabit
       (sticky) yapmak için KULLANMA -- ERK-DATABASE'DE 2026-09-08'DE CANLI
       TARAYICI TESTİYLE (Playwright/Chromium) DOĞRULANDI: "overflow-x:
       auto" bu kutuyu position:sticky torunları için bir "scroll
       container" yapıyor, thead SAYFAYA göre değil BU KUTUYA göre
       sabitlenmeye çalışıp veri satırlarının ÜSTÜNE biniyor / görünmez
       oluyor. "overflow-y: clip" de bunu ÇÖZMÜYOR -- ayrıca canlı testle
       doğrulandı: Chromium'da clip, hidden ile AYNI şekilde scroll
       container oluşturuyor. Yani sayfanın üstüne sabit bir .sabit-ust bar
       eklesen bile, BU TABLONUN KENDİ thead'ini sticky yapmaya ÇALIŞMA --
       sadece .sabit-ust'u sticky yap, tablo başlığı normal (static) kalsın. */
    overflow-x: auto;
    margin-bottom: 24px;
  }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { border: 1px solid #eef0f2; padding: 7px 10px; text-align: left; white-space: nowrap; }

  thead tr.baslik-satiri th {
    background: #041e42; color: #fff; cursor: pointer; user-select: none;
  }
  thead tr.baslik-satiri th:hover { background: #0a2d5e; }
  thead tr.baslik-satiri th::after { content: " ⇅"; opacity: 0.5; font-size: 11px; }
  thead tr.baslik-satiri th[data-siralama="artan"]::after { content: " ▲"; opacity: 1; }
  thead tr.baslik-satiri th[data-siralama="azalan"]::after { content: " ▼"; opacity: 1; }
  thead tr.filtre-satiri th {
    background: #f3f4f6; padding: 4px 6px; cursor: default;
  }
  thead tr.filtre-satiri th::after { content: ""; }

  /* Sütun başlığının altındaki "Excel benzeri" çoklu-seçim filtre butonu
     (bkz. ORTAK_JS: sutunFiltrePopupAc/filtreleUygula). Eskiden burada
     serbest metin girilen bir <input> vardı -- erk-database'de 2026-09-08'de
     bu butona çevrildi: tıklayınca o sütunda geçen tüm farklı değerler onay
     kutulu bir listede açılıyor, birden fazlası seçilebiliyor. Filtre
     AKTİFSE (.sfp-aktif) mavi renkte durur. */
  .sutun-filtre-buton {
    width: 100%; padding: 5px 6px; border: 1px solid #d1d5db; border-radius: 4px;
    font-size: 11px; background: #fff; color: #4b5563; cursor: pointer;
    margin-top: 0; text-align: left;
  }
  .sutun-filtre-buton:hover { background: #f3f4f6; }
  .sutun-filtre-buton.sfp-aktif { background: #dbeafe; border-color: #93c5fd; color: #1d4ed8; font-weight: 600; }

  /* Sütun filtre popup'ı -- document.body'ye EKLENIYOR (tablo hücresinin
     İÇİNE değil, taşma/kırpılma sorunu çıkarmasın diye), JS ile th'nin
     altına konumlandırılıyor. */
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

// ------------------------------------------------------------------
// Sütun bazlı "Excel benzeri" çoklu-seçim filtre (erk-database'de
// 2026-09-08'de eklendi, buraya da kopyalandı)
// ------------------------------------------------------------------
// Her sütun başlığının altındaki "Filtrele ▾" butonuna tıklayınca çağrılır
// -- o sütunda GEÇEN TÜM FARKLI DEĞERLER onay kutulu bir liste halinde bir
// popup'ta gösterilir, kullanıcı istediği kadarını seçip "Uygula"ya basar.
// Birden fazla sütunda filtre varsa hepsi birlikte (VE mantığıyla)
// uygulanır. Herhangi bir projeye kopyalanabilir -- kolon adı/veri şekli
// bilmez, sadece <table id="..."> yapısına (baslik-satiri + filtre-satiri
// + tbody[data-dolu] + tr.veri-satiri) bakar; sütun başlıkları
// <th><button class="sutun-filtre-buton" onclick="sutunFiltrePopupAc(event,
// 'tabloId', this)">Filtrele ▾</button></th> şeklinde olmalı (ornek_uygulama.py'ye bak).
//
// _sutunFiltreDurumu: { tabloId: { kolonIndex: Set(seçili değerler) } }
// Bir kolon için Set YOKSA, o kolonda filtre YOK demektir.
var _sutunFiltreDurumu = {};
var _acikSutunFiltrePaneli = null;  // aynı anda tek panel açık olabilir

function _hucreMetni(satir, kolonIndex) {
  var hucre = satir.children[kolonIndex];
  return hucre ? hucre.innerText.trim() : '';
}

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
  if (_acikSutunFiltrePaneli && _acikSutunFiltrePaneli._buton === buton) {
    sutunFiltrePopupKapat();
    return;
  }
  sutunFiltrePopupKapat();

  var th = buton.closest('th');
  var basliklar = Array.prototype.slice.call(th.parentElement.children);
  var kolonIndex = basliklar.indexOf(th);

  var degerler = _kolonDegerleriTopla(tabloId, kolonIndex);
  if (!_sutunFiltreDurumu[tabloId]) _sutunFiltreDurumu[tabloId] = {};
  var seciliSet = _sutunFiltreDurumu[tabloId][kolonIndex];

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

// Bir tablonun TÜM sütunlarındaki aktif filtreleri (VE mantığıyla) uygular.
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
// Sabit (sticky) üst bölüm: sayfanın üstüne class="sabit-ust" ile sarılmış
// bir bölüm eklersen (üst şerit, arama kartları, arama formu vb.) o bölüm
// kendiliğinden (position: sticky; top: 0) sayfaya yapışık kalır -- bunun
// için JS'te ekstra bir şey yapmana GEREK YOK, sadece CSS (bkz. ortak.py
// içindeki .sabit-ust kuralı, eklenecekse). TEK KURAL: tablonun KENDİ
// thead'ini SICKY YAPMA -- erk-database'de 2026-09-08'de canlı tarayıcı
// testiyle doğrulandığı gibi, .tablo-sarmalayici'nin overflow-x:auto'su
// yüzünden bu Chromium'da çalışmıyor (bkz. CSS'teki not).
</script>
"""

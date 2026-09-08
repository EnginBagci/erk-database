# Tablo/Sayfa Şablonu (Basit Görüntüleyici)

Bu klasör, `erk-database` projesinin `src/viewer.py` dosyasında geliştirdiğimiz
"salt-okunur, sadece görüntüleme amaçlı küçük Flask aracı" tasarımının
**genel (projeden bağımsız) taslağı**.

## Nasıl kullanılacak (ÖNEMLİ -- gelecekteki oturumlar için talimat)

Engin ileride "başka bir form/araç yap" dediğinde: sıfırdan tasarım
yapmaya kalkma -- önce BU klasöre (`sablonlar/basit-goruntuleyici/`) bak,
oradaki tablo + filtre + sıralama + detay-sayfası mantığını temel alarak
yeni isteğe göre bir tablo/sayfa oluştur. Yani "form" derken kastedilen,
tam olarak burada kayıtlı olan bu desendir: arama + her zaman görünen
başlıklı tablo + sütun filtreleri + sıralama + satıra tıklayınca, ANA
SAYFA SABİT KALARAK, küçük ayrı bir PENCEREDE (popup, yeni sekme DEĞİL)
açılan detay sayfası. Yeni bir araçta veri kaynağı ve kolonlar
değişir, ama bu iskelet (ve mümkünse `ortak.py`'deki CSS/JS'in birebir
kendisi) aynı kalır.

## Tasarım deseni

1. **Liste sayfası** ("/"): (istenirse) üstte renkli, TIKLANABİLİR özet/
   istatistik kartları + GENEL bir arama kutusu (tek kutuya yazılan metin
   BİRDEN FAZLA alanla -- örn. isim/kod/renk/etiket -- eşleşir, ayrı ayrı
   "şu alana göre ara" kutuları yerine) + gerekiyorsa ayrı bir tarih
   aralığı arama formu + sonucun HER ZAMAN göründüğü tek bir tablo. Tablo,
   hiç arama yapılmamışken veya sonuç bulunamadığında bile BAŞLIKLARIYLA
   birlikte sabit durur -- veri yoksa gövdede sadece "kayıt yok" satırı
   görünür, başlıklar kaybolmaz.
2. **Kartlar tıklanınca filtreler**: her özet kart bir `<a class="kart-
   link" href="/?...">` ile sarmalanır -- tıklanınca o kartın temsil
   ettiği filtreyle (örn. "bu ayın tarih aralığı" ya da özel bir görünüm
   parametresi) ana sayfaya gidip listeyi otomatik doldurur. Kart
   görünümü ile linkin ayrılması (`.kart-link` dışta, `.kart` içte)
   önemli -- CSS'te böyle kurulu (bkz. `ortak.py`).
3. **Detay sayfası** ("/<id>"): Listedeki bir satıra tıklanınca, o kaydın
   TÜM bilgilerini gösteren ayrı bir sayfa **KÜÇÜK, AYRI BİR PENCEREDE**
   (popup -- `window.open` + genişlik/yükseklik verilerek, "_blank" DEĞİL)
   açılır. Ana sayfa (liste + arama sonucu) olduğu sekmede hiç
   değişmeden, hiç kaybolmadan kalır.
4. Tablolarda: sütun başlığına tıklayınca sıralama, başlığın altındaki
   kutucuklara yazınca anlık (sayfa yenilenmeden) filtreleme.
5. Bir arama formunda "Ara" butonunun yanına kısayol butonları (örn.
   Dün/Bu Ay/Geçen Ay/Bu Yıl) koyacaksan bunlar Ara butonunun ALTINA
   DEĞİL, AYNI SATIRA (yanına) konur -- `ortak.py`'deki `.buton-satiri`/
   `.buton-ikincil` CSS sınıfları bunun için.
5b. Genel arama kutusundaki etiket+girdi+buton'u DAİMA `.genel-arama-
   satiri` sınıflı bir `<div>` içine sar (bkz. `ornek_uygulama.py`).
   Bu sayede metin kutusu (input) kalan boşluğu doldurur ve "çok ufak"
   kalmaz. Ayrıca `label`'a ASLA sabit bir `min-width` verme -- "Başlangıç:"
   gibi uzun ve "Bitiş:" gibi kısa etiketler yan yana kullanılınca, sabit
   min-width kısa etiketin yanında kullanılmayan bir boşluk bırakır
   (erk-database'de fark edilip düzeltilen bir hataydı).
6. Görsel dil: koyu lacivert üst şerit, beyaz kartlar, sade kurumsal
   görünüm. Renkli özet/istatistik kartları İSTENİYORSA `ortak.py`'deki
   `.kart-satiri`/`.kart-link`/`.kart` CSS'i kullanılır (erk-database'in
   görüntüleyicisinde 8 kart olarak kullanılıyor).

## Dosyalar

- `ortak.py` -- `ORTAK_STIL` (CSS, özet kartları dahil) ve `ORTAK_JS`
  (sıralama/filtreleme + satıra-tıklayınca-küçük-pencerede-detay-aç
  JavaScript'i -- `detayPenceresiAc()` fonksiyonu). Projeden bağımsız,
  düz HTML/JS -- herhangi bir veritabanına veya şemaya bağlı değil.
- `ornek_uygulama.py` -- Bellek-içi (veritabanı gerektirmeyen) örnek
  veriyle çalışan, doğrudan çalıştırılabilir (`python ornek_uygulama.py`)
  minik bir Flask uygulaması. Deseni gösterir: liste + arama + tıklanınca
  küçük pencerede açılan detay sayfası (özet kartları ve hızlı tarih
  butonları örnek uygulamada yok -- isteğe bağlı olduğu için basit
  tutuldu, gerekirse viewer.py'deki kullanımına bakılabilir).

## Yeni bir araç için nasıl kullanılır

1. `ornek_uygulama.py`'yi yeni projenin klasörüne kopyala, `ortak.py`'yi de
   yanına al.
2. Örnek veri listesini (`ORNEK_KAYITLAR`) gerçek veri kaynağınla değiştir
   (bir veritabanı sorgusu, bir CSV okuma, bir API çağrısı -- ne olursa).
3. Liste sayfasındaki tablo kolonlarını (`KOLONLAR`) ve detay sayfasındaki
   alanları kendi verine göre güncelle.
4. Arama formu/formlarını ihtiyacına göre değiştir (tek kutu, iki kutu,
   tarih aralığı vs.).
5. İstenirse üste TIKLANABİLİR özet kartları ekle (bkz. `erk-database/
   src/viewer.py` içindeki `ISTATISTIK_SORGUSU` + `kart_tarihleri` +
   `.kart-satiri`/`.kart-link` HTML bloğu -- birebir kopyalanabilir
   örnek, her kart `<a href="/?...">` ile sarılı).
6. Ayrı ayrı "şu alana göre ara" kutuları yerine TEK bir genel arama
   kutusu düşünebilirsin -- SQL'de `OR`/`ILIKE` ile birden fazla kolonu
   birden kontrol eder (bkz. `erk-database/src/viewer.py` içindeki
   `GENEL_ARAMA_SORGUSU`).
7. Tarih aralığı araması varsa: varsayılan olarak içinde bulunulan ayı
   göstermek + "Ara" butonunun YANINA (altına değil) "Dün/Bu Ay/Geçen
   Ay/Bu Yıl" gibi hızlı butonlar koymak isteyebilirsin (bkz.
   `erk-database/src/viewer.py` içindeki `tarihAyarla()` JS fonksiyonu,
   `.buton-satiri` CSS'i ve Python tarafındaki `ay_baslangic`/`ay_bitis`
   varsayılan hesaplaması -- birebir kopyalanabilir örnek).

Bu şablon bilerek "ham" ve küçük tutuldu -- her yeni araç için birebir
kopyala-yapıştır + birkaç satır değiştirme yeterli olsun diye.

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

1. **Liste sayfası** ("/"): (istenirse) üstte renkli özet/istatistik
   kartları + bir veya iki arama formu (örn. metin ara, tarih aralığı
   ara) + sonucun HER ZAMAN göründüğü tek bir tablo. Tablo, hiç arama
   yapılmamışken veya sonuç bulunamadığında bile BAŞLIKLARIYLA birlikte
   sabit durur -- veri yoksa gövdede sadece "kayıt yok" satırı görünür,
   başlıklar kaybolmaz.
2. **Detay sayfası** ("/<id>"): Listedeki bir satıra tıklanınca, o kaydın
   TÜM bilgilerini gösteren ayrı bir sayfa **KÜÇÜK, AYRI BİR PENCEREDE**
   (popup -- `window.open` + genişlik/yükseklik verilerek, "_blank" DEĞİL)
   açılır. Ana sayfa (liste + arama sonucu) olduğu sekmede hiç
   değişmeden, hiç kaybolmadan kalır.
3. Tablolarda: sütun başlığına tıklayınca sıralama, başlığın altındaki
   kutucuklara yazınca anlık (sayfa yenilenmeden) filtreleme.
4. Görsel dil: koyu lacivert üst şerit, beyaz kartlar, sade kurumsal
   görünüm. Renkli özet/istatistik kartları (örn. "Toplam Araç", "Toplam
   Fatura") İSTENİYORSA `ortak.py`'deki `.kart-satiri`/`.kart` CSS'i
   kullanılır (erk-database'in görüntüleyicisinde kullanılıyor).

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
5. İstenirse üste özet kartları ekle (bkz. `erk-database/src/viewer.py`
   içindeki `ISTATISTIK_SORGUSU` + `.kart-satiri` HTML bloğu -- birebir
   kopyalanabilir örnek).
6. Tarih aralığı araması varsa: varsayılan olarak içinde bulunulan ayı
   göstermek + yanına "Dün/Bu Ay/Geçen Ay/Bu Yıl" gibi hızlı butonlar
   koymak isteyebilirsin (bkz. `erk-database/src/viewer.py` içindeki
   `tarihAyarla()` JS fonksiyonu ve Python tarafındaki `ay_baslangic`/
   `ay_bitis` varsayılan hesaplaması -- birebir kopyalanabilir örnek).

Bu şablon bilerek "ham" ve küçük tutuldu -- her yeni araç için birebir
kopyala-yapıştır + birkaç satır değiştirme yeterli olsun diye.

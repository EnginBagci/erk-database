"""
Yakıt tipi geriye dönük doldurma (backfill) script'i.

NEDEN BU DOSYA VAR: "Yakıt tipi" (Benzin/Dizel/Elektrik) özelliği,
sistemdeki araçların bir kısmı zaten eklendikten SONRA eklendi. Bundan
sonra çekilecek YENİ araçlar zaten src/etl.py tarafından otomatik
dolduruluyor (bkz. etl.py'deki yakit_tipi_belirle() fonksiyonu ve adım
11b) -- bu script SADECE bu özellik eklenmeden ÖNCE veritabanına girmiş
olan araçlar için TEK SEFERLİK bir "geçmişi doldurma" işlemi yapar.

KURAL: etl.py'deki yakit_tipi_belirle() fonksiyonunu ÇAĞIRIR, kuralı
burada TEKRAR YAZMIYORUZ (tek doğru kaynak orası -- bu dosyayı okuyup
"DD -> Elektrik" istisnasını görmeyebilirsin, güncel kural için her zaman
etl.py'deki fonksiyonun docstring'ine bak). Belirlenemeyen (motor no boş
ya da tanınmayan bir harfle başlıyorsa) araçlara dokunulmuyor, "bilinmiyor"
olarak sayılıp rapor sonunda kaç tane olduğu yazdırılıyor.

NOT: Bu script SADECE yakit_id'si BOŞ olanları doldurur. Kural
DEĞİŞTİĞİNDE (örn. yeni bir harf istisnası eklendiğinde) daha önce
YANLIŞ atanmış araçları düzeltmek için src/yakit_tipi_yeniden_hesapla.py
kullanılmalı -- bu script o durumda işe yaramaz (zaten dolu olana dokunmaz).

Bu script AYRICA veritabanı şemasını da günceller (araclar tablosuna
yakit_id kolonu ekler) -- ayrı bir "migration" SQL dosyası çalıştırmaya
GEREK YOK, hepsi burada. "IF NOT EXISTS" kullanıldığı için script
YANLIŞLIKLA İKİNCİ KEZ çalıştırılsa bile hata vermez (idempotent) --
zaten yakit_id'si dolu olan araçlara tekrar dokunmaz.

Kullanım (bir kere, tüm mevcut araçlar için):
    .venv\\Scripts\\python.exe -m src.backfill_yakit_tipi
(ya da aktif bir venv içindeysen: python -m src.backfill_yakit_tipi)

ETKİ HARİTASI: araclar (yakit_id kolonu + doldurma), yakit_tipleri
(Benzin/Dizel/Elektrik satırları). db.py'deki get_conn/upsert_and_get_id
ve etl.py'deki yakit_tipi_belirle() fonksiyonlarını kullanır, başka hiçbir
dosyaya yazmaz.
"""
import logging

from . import db
from .etl import yakit_tipi_belirle

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("backfill_yakit_tipi")


def _semayi_guncelle(cur):
    """araclar tablosuna yakit_id kolonunu (yoksa) ekler.

    ÖĞRENME NOTU: "ADD COLUMN IF NOT EXISTS" ve "CREATE INDEX IF NOT
    EXISTS" PostgreSQL'e özel, güvenli (idempotent) komutlar -- kolon/index
    zaten varsa hata vermez, sessizce hiçbir şey yapmaz. Bu sayede script
    yanlışlıkla tekrar çalıştırılırsa şema tarafında sorun çıkmaz."""
    cur.execute(
        "ALTER TABLE araclar ADD COLUMN IF NOT EXISTS "
        "yakit_id INTEGER REFERENCES yakit_tipleri(id)"
    )
    cur.execute(
        "CREATE INDEX IF NOT EXISTS idx_araclar_yakit ON araclar(yakit_id)"
    )


def calistir():
    """Tüm araçları tarar, yakit_id'si boş olanları motor_no'ya göre
    doldurur. Sonunda kaç araca hangi yakıt tipi atandığını, kaç tanesinin
    "bilinmiyor" (motor no boş ya da G/D/E dışında bir harfle başlıyor)
    kaldığını yazdırır -- bu proje genelindeki alışkanlık: toplu bir
    işlemden sonra sonucu SAYILARLA doğrula, sessizce güven."""
    sayaclar = {"Benzin": 0, "Dizel": 0, "Elektrik": 0, "bilinmiyor": 0}

    with db.get_conn() as conn:
        with conn.cursor() as cur:
            _semayi_guncelle(cur)
            conn.commit()
            log.info("Şema kontrol edildi (yakit_id kolonu/index hazır).")

            # NOT: "WHERE yakit_id IS NULL" -- script tekrar çalıştırılırsa
            # zaten doldurulmuş araçları BİR DAHA işlemeyiz (gereksiz yere
            # upsert_and_get_id çağırmayız), sadece hâlâ boş olanlara bakar.
            cur.execute("SELECT id, sasi_no, motor_no FROM araclar WHERE yakit_id IS NULL")
            satirlar = cur.fetchall()
            log.info("%d araç kontrol edilecek (yakit_id şu an boş).", len(satirlar))

            for arac_id, sasi_no, motor_no in satirlar:
                yakit_adi = yakit_tipi_belirle(motor_no)
                if yakit_adi is None:
                    sayaclar["bilinmiyor"] += 1
                    continue
                yakit_id = db.upsert_and_get_id(cur, "yakit_tipleri", ["adi"], {"adi": yakit_adi})
                cur.execute("UPDATE araclar SET yakit_id = %s WHERE id = %s", (yakit_id, arac_id))
                sayaclar[yakit_adi] += 1

            conn.commit()

    log.info(
        "Bitti. Benzin=%d, Dizel=%d, Elektrik=%d, bilinmiyor(motor no eksik ya da G/D/E dışında bir harf)=%d",
        sayaclar["Benzin"], sayaclar["Dizel"], sayaclar["Elektrik"], sayaclar["bilinmiyor"],
    )
    if sayaclar["bilinmiyor"]:
        log.info(
            "NOT: 'bilinmiyor' sayılan araçların motor_no'sunu kontrol etmek "
            "istersen: SELECT sasi_no, motor_no FROM araclar WHERE yakit_id IS NULL;"
        )


if __name__ == "__main__":
    calistir()

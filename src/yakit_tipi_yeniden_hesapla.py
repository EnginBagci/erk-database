"""
Yakıt tipi YENİDEN HESAPLA script'i.

NEDEN BU DOSYA VAR: src/backfill_yakit_tipi.py SADECE yakit_id'si BOŞ
(NULL) olan araçları doldurur -- bir kere doldurulmuş bir araca BİR DAHA
DOKUNMAZ. Ama yakit_tipi_belirle() (bkz. etl.py) kuralı zaman zaman
DEĞİŞEBİLİR -- ilk örneği 2026-09-08'de oldu: IONIQ modellerinde motor no
"DD" ile başlıyor ve bunlar ELEKTRİKLİ araçlar, ama genel "D ile başlayan
= Dizel" kuralı bu araçları YANLIŞLIKLA Dizel olarak işaretlemişti (kural
düzeltilmeden önce çalışan backfill_yakit_tipi.py yüzünden). Kural
DEĞİŞTİĞİNDE, daha önce YANLIŞ atanmış araçları düzeltmenin tek yolu bu
script -- TÜM araçları (motor_no'su olanları) güncel kurala göre YENİDEN
hesaplar, mevcut değerden FARKLIYSA düzeltir.

Kullanım (kural her değiştiğinde -- yani yakit_tipi_belirle() fonksiyonu
her güncellendiğinde -- tekrar çalıştırılabilir, İDEMPOTENT: değişiklik
yoksa hiçbir şeye dokunmaz):
    .venv\\Scripts\\python.exe -m src.yakit_tipi_yeniden_hesapla

NOT: Bu script backfill_yakit_tipi.py'nin YERİNE geçmiyor -- backfill,
şema (yakit_id kolonu) ilk kurulduğunda tek seferlik çalıştırıldı. Bu
script ise "kural değişti, geçmişi düzelt" senaryosu için -- ikisi farklı
amaçlara hizmet ediyor, ikisi de kalıcı olarak dursun.

ETKİ HARİTASI: araclar.yakit_id (günceller), yakit_tipleri (gerekirse
yeni satır -- örn. ileride "Hibrit" gibi yeni bir tip eklenirse). Sadece
db.py ve etl.py'deki yakit_tipi_belirle() fonksiyonunu kullanır.
"""
import logging

from . import db
from .etl import yakit_tipi_belirle

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("yakit_tipi_yeniden_hesapla")


def calistir():
    degisiklikler = []  # (sasi_no, eski_adi, yeni_adi) üçlüleri -- rapor için

    with db.get_conn() as conn:
        with conn.cursor() as cur:
            # LEFT JOIN: yt.adi, araç şu an hiç yakıt tipine bağlı değilse
            # (yakit_id NULL) NULL gelir -- bu da normal, "eski_adi" None olur.
            cur.execute(
                """
                SELECT a.id, a.sasi_no, a.motor_no, yt.adi
                FROM araclar a
                LEFT JOIN yakit_tipleri yt ON yt.id = a.yakit_id
                ORDER BY a.sasi_no
                """
            )
            satirlar = cur.fetchall()
            log.info("%d araç kontrol edilecek (güncel kurala göre).", len(satirlar))

            for arac_id, sasi_no, motor_no, eski_adi in satirlar:
                yeni_adi = yakit_tipi_belirle(motor_no)
                if yeni_adi == eski_adi:
                    continue  # değişiklik yok, dokunma

                yeni_id = None
                if yeni_adi:
                    yeni_id = db.upsert_and_get_id(cur, "yakit_tipleri", ["adi"], {"adi": yeni_adi})
                cur.execute("UPDATE araclar SET yakit_id = %s WHERE id = %s", (yeni_id, arac_id))
                degisiklikler.append((sasi_no, eski_adi or "-", yeni_adi or "-"))

            conn.commit()

    log.info("Bitti. %d araç güncellendi.", len(degisiklikler))
    for sasi_no, eski, yeni in degisiklikler:
        log.info("  %s: %s -> %s", sasi_no, eski, yeni)
    if not degisiklikler:
        log.info("Hiçbir araç değişmedi -- veritabanı zaten güncel kuralla uyumlu.")


if __name__ == "__main__":
    calistir()

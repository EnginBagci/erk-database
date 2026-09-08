"""
Yakıt tipi "Tanımsız" kalan araçları ANALİZ ETMEK için salt-okunur bir
rapor script'i. Hiçbir şey YAZMAZ/DEĞİŞTİRMEZ -- sadece ekrana bir özet
basar. backfill_yakit_tipi.py çalıştırıldıktan sonra "bilinmiyor" sayısı
0'dan büyükse, NEDEN tanımsız kaldıklarını (motor_no boş mu, yoksa G/D/E
dışında bir harfle mi başlıyor) görmek için bunu çalıştır.

Kullanım:
    .venv\\Scripts\\python.exe -m src.yakit_tanimsiz_analiz

Ne yapıyor:
  1) yakit_id'si NULL olan tüm araçları çeker.
  2) motor_no'nun İLK HARFİNE göre gruplar (motor_no boşsa "(BOŞ)" grubuna
     koyar) ve her grup için kaç araç olduğunu sayar.
  3) Her gruptan birkaç ÖRNEK şase/motor no yazdırır -- gerçek veriye
     bakıp "bu harf gerçekten ne anlama geliyor" diye karar verebilesin
     diye (örn. belki H harfi Hibrit'i temsil ediyordur, script bunu
     BİLEMEZ, sadece elindeki veriyi gösterir).

Bu script'in çıktısını bana yapıştırırsan (ya da kendin yorumlarsan),
gerekirse etl.py + backfill_yakit_tipi.py'deki yakit_tipi_belirle()
fonksiyonuna yeni bir harf kuralı (örn. "H" -> "Hibrit") eklenebilir.
"""
import logging
from collections import defaultdict

from . import db

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("yakit_tanimsiz_analiz")

ORNEK_SAYISI = 5  # her harf grubundan en fazla kaç örnek gösterilecek


def calistir():
    with db.get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT sasi_no, motor_no FROM araclar WHERE yakit_id IS NULL "
                "ORDER BY motor_no NULLS FIRST"
            )
            satirlar = cur.fetchall()

    toplam = len(satirlar)
    log.info("Yakıt tipi TANIMSIZ (yakit_id NULL) toplam araç: %d", toplam)
    if toplam == 0:
        log.info("Hiç tanımsız araç yok -- her şey Benzin/Dizel/Elektrik olarak dolu.")
        return

    gruplar = defaultdict(list)
    for sasi_no, motor_no in satirlar:
        if not motor_no or not motor_no.strip():
            harf = "(BOŞ -- motor no hiç girilmemiş)"
        else:
            harf = motor_no.strip()[0].upper()
        gruplar[harf].append((sasi_no, motor_no))

    log.info("")
    log.info("Motor no'nun ilk harfine göre dağılım:")
    for harf, kayitlar in sorted(gruplar.items(), key=lambda kv: -len(kv[1])):
        log.info("  %-40s : %d araç", harf, len(kayitlar))
        for sasi_no, motor_no in kayitlar[:ORNEK_SAYISI]:
            log.info("        örnek: sasi=%s motor_no=%r", sasi_no, motor_no)
        if len(kayitlar) > ORNEK_SAYISI:
            log.info("        ... ve %d tane daha", len(kayitlar) - ORNEK_SAYISI)

    log.info("")
    log.info(
        "NOT: G/D/E dışındaki bir harf (örn. yukarıda 'H' ya da başka bir "
        "harf çıktıysa) gerçekten yeni bir yakıt tipini (örn. Hibrit) "
        "temsil ediyor olabilir -- bu script sadece VERİYİ gösterir, "
        "yorumu sana/Claude'a bırakır."
    )


if __name__ == "__main__":
    calistir()

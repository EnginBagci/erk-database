"""
Ana ETL akışı: GetPurchaseInvoicesByDates'ten gelen kayıtları
carline -> spec -> renk -> spec_ocn_renk -> şasi -> fatura sırasıyla
upsert eder.

Kullanım:
    python -m src.etl 2026-08-01 2026-08-31

ETKİ HARİTASI -- bu dosya şu tablolara YAZAR (schema.sql'de bunları
değiştirirsen burayı da kontrol et):
    arac_tipleri, carline, model_yillari, dis_renkler, ic_renkler, ocn,
    spec, spec_ocn, spec_ocn_renk, bayiler, araclar, plakalar,
    gumruk_bilgileri, alis_faturalari

Bu dosya şunlara OKUMA/BAĞIMLILIK olarak dayanır (bunları değiştirirsen
burası bozulabilir):
    - db.upsert_and_get_id / db.row_exists / db.get_id_by (db.py)
    - api_client.get_client() ve DmsApiClient.get_purchase_invoices_by_dates
      (api_client.py)
    - schema.sql'deki tablo/kolon isimleri (SQL sorguları burada elle
      yazıldı, kolon adı değişirse burada da değiştirilmeli)

ÖĞRENME NOTU (genel akış): Bu script iki ana fonksiyondan oluşuyor:
    1. process_invoice_record(cur, r) -- TEK bir fatura kaydını alır,
       gerekli tüm lookup tablolarını (carline, renk, spec, vb.) sırayla
       upsert eder, en sonda araç ve faturayı ekler.
    2. run_range(start_date, end_date) -- API'den tarih aralığına göre
       kayıtları 28'er günlük parçalar halinde çeker ve her kaydı
       process_invoice_record'a tek tek gönderir.
"""
import datetime as dt
import logging
import sys

from . import config, db
from .api_client import get_client

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
log = logging.getLogger("etl")


def _parse_api_date(value):
    """API'den gelen tarih string'ini Python date nesnesine çevirir.
    Boş/None ise None döner (veritabanına NULL olarak yazılır).

    UYARI: API farklı bir tarih formatı göndermeye başlarsa (örn. saat
    dilimi eklerse) burası "Tarih parse edilemedi" uyarısı basar ve o
    alanı NULL bırakır -- veri kaybolmaz ama o tarih eksik kalır. Böyle bir
    uyarı görürsen (log'larda WARNING satırı) bu fonksiyona yeni bir format
    eklemen gerekir.
    """
    if not value:
        return None
    # Beklenen format: 2026-08-31T00:00:00.000 (veya sonunda Z olabilir)
    value = value.replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    log.warning("Tarih parse edilemedi, ham değer saklanamadı: %r", value)
    return None


def process_invoice_record(cur, r: dict) -> str:
    """Tek bir fatura kaydını işler. Dönüş: 'eklendi' | 'atlandi' (fatura zaten vardı).

    GERÇEK API YAPISI (2026-09-08'de canlı veriyle doğrulandı) özetteki gibi
    düz değil -- iç içe:
        r
        ├─ id, formalInvoiceNumber, waybillNumber, invoiceDate, waybillDate,
        │  totalBaseAmount, totalTaxAmount, totalInvoiceAmount, invoiceStatus,
        │  dealerID, dutyClaimDate/Number, dutyInvoiceDate/Number
        ├─ serviceAndDealerInfo: {code, name, dealer: {code, name}, ...}
        └─ invoiceDetail: {price, discountAmount, discountedAmount,
                            taxAmount, taxPercent, totalAmount,
                            item: {vinNumber, engineNumber, plateNumber,
                                   carLineType, modelNumber, dutyOffice,
                                   specOcnColorInteriorColor: {carlineCode,
                                       carlineName, specCode, ocnNumber,
                                       specOcnName, colorCode, colorName,
                                       interiorColorCode, interiorColorName,
                                       fullSpecCode, carLineTypeID}}}

    Not: üst seviyedeki totalDiscountAmount aslında indirimli NET fiyat
    (invoiceDetail.discountedAmount ile aynı), gerçek indirim tutarı ve KDV
    oranı sadece invoiceDetail içinde var (discountAmount, taxPercent) --
    o yüzden fiyat alanları invoiceDetail'den okunuyor, üst seviyeden değil.

    ADIM SIRASI ÖNEMLİ: Her adım bir öncekinin ürettiği id'yi kullanıyor
    (örn. spec, carline_id'ye ihtiyaç duyuyor). Adımların sırasını
    değiştirirsen (örn. spec'i carline'dan önce eklemeye çalışırsan)
    carline_id henüz yokken kullanılmaya çalışılır ve None gider -- hata
    vermez ama veri eksik/yanlış bağlanır. Sırayı bozma.
    """
    detail = r.get("invoiceDetail") or {}
    item = detail.get("item") or {}
    spec_info = item.get("specOcnColorInteriorColor") or {}
    dealer_info = r.get("serviceAndDealerInfo") or {}
    dealer = dealer_info.get("dealer") or {}

    # --- 1. araç tipi (arac_tipleri tablosu) ---
    # "Binek", "Ticari" gibi genel araç kategorisi. spec_info içindeki
    # carLineTypeID (sayısal kod) hyundai_tip_id olarak, item.carLineType
    # (okunabilir isim, örn. "Binek") adi olarak kaydediliyor.
    tip_id = None
    car_line_type_id = spec_info.get("carLineTypeID")
    if car_line_type_id:
        tip_id = db.upsert_and_get_id(
            cur,
            "arac_tipleri",
            ["hyundai_tip_id"],
            {
                "hyundai_tip_id": str(car_line_type_id),
                "adi": item.get("carLineType") or str(car_line_type_id),
            },
        )

    # --- 2. carline (carline tablosu) ---
    # Model ailesi (örn. "IONIQ6 (CE)", "i20 (BC3)"). Bir üstte bulduğumuz
    # tip_id'ye bağlanıyor.
    carline_kod = spec_info.get("carlineCode")
    carline_id = None
    if carline_kod:
        carline_id = db.upsert_and_get_id(
            cur,
            "carline",
            ["kod"],
            {"kod": carline_kod, "adi": spec_info.get("carlineName"), "tip_id": tip_id},
        )

    # --- 3. model yılı (model_yillari tablosu) ---
    # UYARI: bu endpoint'te "modelYear" alanı hep boş geliyor, gerçek model
    # yılı "modelNumber" alanında (örn. 2026). modelNumber yoksa modelYear'a
    # bak (ileride API bunu düzeltirse diye). Bu satırı "düzeltip" sadece
    # modelYear okursan araçların model yılı hep boş kalır.
    model_yil_id = None
    model_year = item.get("modelNumber") or item.get("modelYear")
    if model_year:
        model_yil_id = db.upsert_and_get_id(
            cur, "model_yillari", ["yil"], {"yil": int(model_year)}
        )

    # --- 4. spec (spec tablosu) ---
    # carline + model yılının birleşimi (örn. "IONIQ6 2026"). carline_id ve
    # model_yil_id'ye bağlı -- ikisi de yukarıda hesaplanmış olmalı.
    spec_id = None
    spec_kod = spec_info.get("specCode")
    if spec_kod:
        spec_id = db.upsert_and_get_id(
            cur,
            "spec",
            ["kod"],
            {"kod": spec_kod, "carline_id": carline_id, "model_yil_id": model_yil_id},
        )

    # --- 5. dış renk (dis_renkler tablosu) ---
    dis_renk_id = None
    color_code = spec_info.get("colorCode")
    if color_code:
        dis_renk_id = db.upsert_and_get_id(
            cur, "dis_renkler", ["kod"], {"kod": color_code, "adi": spec_info.get("colorName")}
        )

    # --- 6. iç renk (ic_renkler tablosu) ---
    ic_renk_id = None
    interior_color_code = spec_info.get("interiorColorCode")
    if interior_color_code:
        ic_renk_id = db.upsert_and_get_id(
            cur,
            "ic_renkler",
            ["kod"],
            {"kod": interior_color_code, "adi": spec_info.get("interiorColorName")},
        )

    # --- 7. ocn (ocn tablosu) ---
    # Donanım/paket kodu (örn. "G0KJ" = "Advance 125kW STD Range").
    # NOT: motor_id / vites_id / donanim / ecall_var_mi bu endpoint'te yok
    # (schema.sql'de bu kolonlar var ama burada hep NULL kalıyor).
    # İleride bir "teknik detay" endpoint'i eklenirse, o script bu ocn
    # kaydını update_cols ile güncelleyerek motor_id/vites_id'yi doldurmalı
    # -- yeni satır eklememeli (aynı ocn no'ya sahip olmalı).
    ocn_id = None
    ocn_no = spec_info.get("ocnNumber")
    if ocn_no:
        ocn_id = db.upsert_and_get_id(
            cur,
            "ocn",
            ["no"],
            {"no": ocn_no, "adi": spec_info.get("specOcnName"), "spec_id": spec_id},
        )

    # --- 8. spec_ocn (spec_ocn tablosu) ---
    # spec + ocn'in birleşimi (API'nin "fullSpecCode" dediği şey).
    # UYARI: spec_id VEYA ocn_id yoksa (API'de o alan boşsa) bu adım hiç
    # çalışmaz ve spec_ocn_id None kalır -- bir sonraki adımlar da (renk
    # bağlama, araç) spec_ocn_renk_id'siz devam eder. Bu normal bir durum,
    # hata değil, ama "neden bu aracın rengi/spec'i yok" diye sorarsan
    # cevap muhtemelen burada.
    spec_ocn_id = None
    full_spec_kodu = spec_info.get("fullSpecCode")
    if spec_id and ocn_id:
        spec_ocn_id = db.upsert_and_get_id(
            cur,
            "spec_ocn",
            ["spec_id", "ocn_id"],
            {"spec_id": spec_id, "ocn_id": ocn_id, "full_spec_kodu": full_spec_kodu},
        )

    # --- 9. spec_ocn_renk (spec_ocn_renk tablosu) ---
    # spec_ocn + dış renk + iç renk birleşimi -- bir aracın TAM konfigürasyonu
    # (model + donanım + renk kombinasyonu). araclar tablosu doğrudan buraya
    # bağlanıyor (bkz. adım 11).
    spec_ocn_renk_id = None
    if spec_ocn_id:
        spec_ocn_renk_id = db.upsert_and_get_id(
            cur,
            "spec_ocn_renk",
            ["spec_ocn_id", "dis_renk_id", "ic_renk_id"],
            {
                "spec_ocn_id": spec_ocn_id,
                "dis_renk_id": dis_renk_id,
                "ic_renk_id": ic_renk_id,
                "tam_adi": spec_info.get("specOcnName"),
            },
        )

    # --- 10. bayi (bayiler tablosu) ---
    # update_cols=["kodu", "adi"] KASITLI: bayi bilgisi değişirse (örn. isim
    # güncellenirse) her fatura işlendiğinde en güncel haliyle üzerine
    # yazılsın istiyoruz. Diğer lookup tablolarında (carline, renk vb.)
    # update_cols vermiyoruz çünkü onlar zaten değişmeyen sabit kodlar.
    bayi_id = None
    dealer_id = r.get("dealerID") or dealer_info.get("dealerId")
    if dealer_id:
        bayi_id = db.upsert_and_get_id(
            cur,
            "bayiler",
            ["hyundai_id"],
            {
                "hyundai_id": str(dealer_id),
                "kodu": dealer.get("code") or dealer_info.get("code"),
                "adi": (dealer.get("name") or dealer_info.get("name") or "").strip() or None,
            },
            update_cols=["kodu", "adi"],
        )

    # --- 11. araç (araclar tablosu) -- ŞASİ MERKEZ ---
    # Bu, tüm sistemin kalbi: şasi (VIN) numarası olmadan bir kaydı hiçbir
    # şeye bağlayamayız, o yüzden yoksa direkt atlıyoruz (aşağıya bak).
    sasi_no = item.get("vinNumber")
    if not sasi_no:
        log.warning("Şasi numarası (vinNumber) olmayan kayıt atlandı: fatura id=%s", r.get("id"))
        return "atlandi"

    arac_id = db.get_id_by(cur, "araclar", "sasi_no", sasi_no)
    if arac_id is None:
        cur.execute(
            """
            INSERT INTO araclar (sasi_no, motor_no, model_yili, spec_ocn_renk_id)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (sasi_no, item.get("engineNumber"), int(model_year) if model_year else None, spec_ocn_renk_id),
        )
        arac_id = cur.fetchone()[0]
        log.info("Yeni araç eklendi: sasi=%s", sasi_no)
    # NOT (KASITLI TASARIM): şasi zaten varsa araç kaydı GÜNCELLENMİYOR,
    # sadece faturası ekleniyor (adım 14). Yani bir aracın rengi/spec'i
    # ilk görüldüğü faturadaki haliyle sabit kalır. Bunu değiştirmek
    # istersen (örn. en son bilgiyle güncellemek) burada bir UPDATE
    # eklemen gerekir -- ama dikkat: bu, ileride "araç ilk ne olarak
    # alındı" bilgisini kaybetmene sebep olabilir.

    # --- 12. plaka (plakalar tablosu) ---
    # Aynı araca aynı plaka birden fazla kez eklenmesin diye önce kontrol
    # ediyoruz (SELECT). Script'i aynı tarih aralığı için tekrar
    # çalıştırdığında mükerrer plaka satırı OLUŞMAMASININ garantisi bu.
    plate = item.get("plateNumber")
    if plate:
        cur.execute(
            "SELECT 1 FROM plakalar WHERE arac_id = %s AND plaka = %s", (arac_id, plate)
        )
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO plakalar (arac_id, plaka, baslangic, aktif_mi)
                VALUES (%s, %s, %s, TRUE)
                """,
                (arac_id, plate, _parse_api_date(r.get("invoiceDate"))),
            )

    # --- 13. gümrük bilgisi (gumruk_bilgileri tablosu) ---
    # Sadece ithal araçlarda dolu geliyor (dutyClaimNumber/dutyInvoiceNumber
    # boşsa yerli üretim ya da bilgi eksik demektir, hiçbir şey yazılmaz).
    # "IS NOT DISTINCT FROM" kullanıyoruz (= yerine) çünkü talep_no/fatura_no
    # NULL olabilir -- normal SQL'de NULL = NULL yanlış (UNKNOWN) sonucu
    # verir, IS NOT DISTINCT FROM ise NULL'ları da doğru karşılaştırır.
    talep_no = r.get("dutyClaimNumber")
    gumruk_fatura_no = r.get("dutyInvoiceNumber")
    if talep_no or gumruk_fatura_no:
        cur.execute(
            """
            SELECT 1 FROM gumruk_bilgileri
            WHERE arac_id = %s AND talep_no IS NOT DISTINCT FROM %s
                  AND fatura_no IS NOT DISTINCT FROM %s
            """,
            (arac_id, talep_no, gumruk_fatura_no),
        )
        if not cur.fetchone():
            cur.execute(
                """
                INSERT INTO gumruk_bilgileri (
                    arac_id, talep_tarihi, talep_no, fatura_tarihi, fatura_no, gumruk_mudurlugu
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    arac_id,
                    _parse_api_date(r.get("dutyClaimDate")),
                    talep_no,
                    _parse_api_date(r.get("dutyInvoiceDate")),
                    gumruk_fatura_no,
                    item.get("dutyOffice"),
                ),
            )

    # --- 14. alış faturası (alis_faturalari tablosu) ---
    # BU FONKSİYONUN "ASIL İŞİ" BURADA BİTİYOR: yukarıdaki 1-13 adımların
    # hepsi aslında bu faturayı doğru bağlamak için gereken lookup/araç
    # kayıtlarını hazırlamaktı. Fatura zaten işlenmişse (hyundai_fatura_id
    # veritabanında varsa) hiçbir şey yapmadan çıkıyoruz -- bu, script'in
    # tekrar tekrar çalıştırılabilir (idempotent) olmasını sağlayan asıl
    # kontrol noktası.
    hyundai_fatura_id = r.get("id")
    if hyundai_fatura_id is None:
        log.warning("Fatura id'si olmayan kayıt (sasi=%s) atlandı.", sasi_no)
        return "atlandi"

    if db.row_exists(cur, "alis_faturalari", "hyundai_fatura_id", str(hyundai_fatura_id)):
        return "atlandi"

    # UYARI: Bu dört alanı üst seviyeden (r.get("totalBaseAmount") vb.)
    # DEĞİL, invoiceDetail'den okuyoruz -- üst seviyedeki totalDiscountAmount
    # yanıltıcı (bkz. fonksiyon docstring'i). Bunu "sadeleştireyim" diye üst
    # seviyeye geri çevirme, rakamlar yanlış çıkar.
    liste_fiyat = detail.get("price")
    indirim = detail.get("discountAmount")
    indirimli_fiyat = detail.get("discountedAmount")
    kdv_orani = detail.get("taxPercent")
    kdv_tutari = detail.get("taxAmount")
    toplam = detail.get("totalAmount")

    cur.execute(
        """
        INSERT INTO alis_faturalari (
            arac_id, bayi_id, hyundai_fatura_id, fatura_no, irsaliye_no,
            fatura_tarihi, irsaliye_tarihi, liste_fiyat, indirim,
            indirimli_fiyat, kdv_orani, kdv_tutari, toplam, durum
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            arac_id,
            bayi_id,
            str(hyundai_fatura_id),
            r.get("formalInvoiceNumber"),
            r.get("waybillNumber"),
            _parse_api_date(r.get("invoiceDate")),
            _parse_api_date(r.get("waybillDate")),
            liste_fiyat,
            indirim,
            indirimli_fiyat,
            kdv_orani,
            kdv_tutari,
            toplam,
            r.get("invoiceStatus"),
        ),
    )
    return "eklendi"


def run_range(start_date: dt.date, end_date: dt.date, chunk_days: int = 28):
    """[start_date, end_date] aralığını chunk_days'lik parçalara bölüp işler.

    NOT: DMS API'sinin bir istekte en fazla 28 günlük aralık kabul ettiği
    doğrulandı (daha geniş aralıkta 400 Bad Request dönüyor). Bu yüzden
    varsayılan 28 -- daha yükseğe çıkarma.

    HATA YÖNETİMİ (önemli): Bir parçanın API isteği başarısız olursa (bkz.
    "except Exception" bloğu) o parça atlanıp bir SONRAKİ parçaya geçilir --
    tüm çekim durmaz. Bu iyi bir şey (85 parçadan biri başarısız olsa bile
    kalanı çekilir) ama şu anlama da geliyor: script sonunda hata vermeden
    bitse bile aslında bir parça sessizce eksik kalmış olabilir. Bunu
    yakalamak için README'deki "aya göre kayıt sayısı" sorgusunu kullan --
    beklenmedik bir 0 varsa o parça başarısız olmuş demektir.
    """
    client = get_client()

    with db.get_conn() as conn:
        cur_date = start_date
        total_eklendi = 0
        total_atlandi = 0
        while cur_date <= end_date:
            chunk_end = min(cur_date + dt.timedelta(days=chunk_days - 1), end_date)
            log.info("Çekiliyor: %s -> %s", cur_date, chunk_end)

            try:
                records = client.get_purchase_invoices_by_dates(cur_date, chunk_end)
            except Exception:
                log.exception("API çağrısı başarısız: %s -> %s", cur_date, chunk_end)
                cur_date = chunk_end + dt.timedelta(days=1)
                continue

            log.info("  %d kayıt geldi", len(records))

            # NOT: Her parça (chunk) için TEK BİR conn.commit() yapılıyor
            # (parçadaki tüm kayıtlar işlendikten sonra). Yani bir parça
            # içinde 100 kayıttan 99'u başarılı 1'i hatalıysa, o 1 kayıt
            # atlanır (aşağıdaki "except Exception" ile) ama diğer 99'u
            # yine de commit edilir -- kayıt bazında da script dayanıklı.
            with conn.cursor() as cur:
                for r in records:
                    try:
                        sonuc = process_invoice_record(cur, r)
                        if sonuc == "eklendi":
                            total_eklendi += 1
                        else:
                            total_atlandi += 1
                    except Exception:
                        log.exception("Kayıt işlenemedi (fatura id=%s): devam ediliyor", r.get("id"))
                conn.commit()

            cur_date = chunk_end + dt.timedelta(days=1)

        log.info("Bitti. Eklenen fatura: %d, atlanan (zaten vardı/eksik): %d", total_eklendi, total_atlandi)


if __name__ == "__main__":
    # Komut satırından çalıştırıldığında (python -m src.etl BAŞLANGIÇ BİTİŞ)
    # bu blok devreye girer. Başka bir dosyadan "from src.etl import
    # run_range" ile import edilirse bu blok ÇALIŞMAZ -- sadece doğrudan
    # çalıştırıldığında çalışır.
    if len(sys.argv) != 3:
        print("Kullanım: python -m src.etl YYYY-AA-GG YYYY-AA-GG")
        sys.exit(1)

    start = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    end = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
    run_range(start, end)

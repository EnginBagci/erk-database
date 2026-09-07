"""
Ana ETL akışı: GetPurchaseInvoicesByDates'ten gelen kayıtları
carline -> spec -> renk -> spec_ocn_renk -> şasi -> fatura sırasıyla
upsert eder.

Kullanım:
    python -m src.etl 2026-08-01 2026-08-31
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
    """API'den gelen tarih string'ini date'e çevirir. Boş/None ise None döner."""
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
    """
    detail = r.get("invoiceDetail") or {}
    item = detail.get("item") or {}
    spec_info = item.get("specOcnColorInteriorColor") or {}
    dealer_info = r.get("serviceAndDealerInfo") or {}
    dealer = dealer_info.get("dealer") or {}

    # --- 1. araç tipi ---
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

    # --- 2. carline ---
    carline_kod = spec_info.get("carlineCode")
    carline_id = None
    if carline_kod:
        carline_id = db.upsert_and_get_id(
            cur,
            "carline",
            ["kod"],
            {"kod": carline_kod, "adi": spec_info.get("carlineName"), "tip_id": tip_id},
        )

    # --- 3. model yılı ---
    # NOT: bu endpoint'te "modelYear" alanı hep boş geliyor, gerçek model yılı
    # "modelNumber" alanında (örn. 2026). modelNumber yoksa modelYear'a bak.
    model_yil_id = None
    model_year = item.get("modelNumber") or item.get("modelYear")
    if model_year:
        model_yil_id = db.upsert_and_get_id(
            cur, "model_yillari", ["yil"], {"yil": int(model_year)}
        )

    # --- 4. spec ---
    spec_id = None
    spec_kod = spec_info.get("specCode")
    if spec_kod:
        spec_id = db.upsert_and_get_id(
            cur,
            "spec",
            ["kod"],
            {"kod": spec_kod, "carline_id": carline_id, "model_yil_id": model_yil_id},
        )

    # --- 5. dış renk ---
    dis_renk_id = None
    color_code = spec_info.get("colorCode")
    if color_code:
        dis_renk_id = db.upsert_and_get_id(
            cur, "dis_renkler", ["kod"], {"kod": color_code, "adi": spec_info.get("colorName")}
        )

    # --- 6. iç renk ---
    ic_renk_id = None
    interior_color_code = spec_info.get("interiorColorCode")
    if interior_color_code:
        ic_renk_id = db.upsert_and_get_id(
            cur,
            "ic_renkler",
            ["kod"],
            {"kod": interior_color_code, "adi": spec_info.get("interiorColorName")},
        )

    # --- 7. ocn ---
    # NOT: motor_id / vites_id / donanim / ecall_var_mi bu endpoint'te yok.
    # Servis/teknik detay endpoint'i eklendiğinde UPDATE ile doldurulacak.
    ocn_id = None
    ocn_no = spec_info.get("ocnNumber")
    if ocn_no:
        ocn_id = db.upsert_and_get_id(
            cur,
            "ocn",
            ["no"],
            {"no": ocn_no, "adi": spec_info.get("specOcnName"), "spec_id": spec_id},
        )

    # --- 8. spec_ocn ---
    spec_ocn_id = None
    full_spec_kodu = spec_info.get("fullSpecCode")
    if spec_id and ocn_id:
        spec_ocn_id = db.upsert_and_get_id(
            cur,
            "spec_ocn",
            ["spec_id", "ocn_id"],
            {"spec_id": spec_id, "ocn_id": ocn_id, "full_spec_kodu": full_spec_kodu},
        )

    # --- 9. spec_ocn_renk ---
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

    # --- 10. bayi ---
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

    # --- 11. araç (şasi merkez) ---
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
    # NOT: özet dosyasındaki mantığa göre şasi zaten varsa araç kaydı
    # güncellenmiyor, sadece faturası ekleniyor.

    # --- 12. plaka (varsa ve daha önce kaydedilmemişse) ---
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

    # --- 13. gümrük bilgisi (varsa ve daha önce kaydedilmemişse) ---
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

    # --- 14. alış faturası ---
    hyundai_fatura_id = r.get("id")
    if hyundai_fatura_id is None:
        log.warning("Fatura id'si olmayan kayıt (sasi=%s) atlandı.", sasi_no)
        return "atlandi"

    if db.row_exists(cur, "alis_faturalari", "hyundai_fatura_id", str(hyundai_fatura_id)):
        return "atlandi"

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
    if len(sys.argv) != 3:
        print("Kullanım: python -m src.etl YYYY-AA-GG YYYY-AA-GG")
        sys.exit(1)

    start = dt.datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    end = dt.datetime.strptime(sys.argv[2], "%Y-%m-%d").date()
    run_range(start, end)

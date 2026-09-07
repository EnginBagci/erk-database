"""PostgreSQL bağlantısı ve genel upsert yardımcıları.

ETKİ HARİTASI: Bu dosyadaki fonksiyonlar TÜM etl_*.py dosyaları tarafından
kullanılıyor (şu an sadece etl.py var, ileride etl_servis.py, etl_satis.py
gibi dosyalar da bunu kullanacak). Yani burada yapılan bir değişiklik
(özellikle upsert_and_get_id'nin davranışı) HER endpoint'in çekimini
etkiler -- tek bir endpoint için değil, genel olarak dikkatli test et.
"""
from contextlib import contextmanager

import psycopg2

from . import config


@contextmanager
def get_conn():
    """Veritabanına bağlanır ve bir "context manager" olarak döner.

    ÖĞRENME NOTU: "with db.get_conn() as conn:" şeklinde kullanılır. Blok
    bitince (hata olsa bile) bağlantı otomatik kapanır -- elle conn.close()
    çağırmaya gerek kalmaz, unutma riski de olmaz.
    """
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )
    # Windows + Türkçe yerel ayar bazen bağlantıyı WIN1254 client_encoding
    # ile açıyor (psql'de aynı sorunu gördük -- "Şeker Turuncu" gibi isimler
    # bozuk görünüyordu). Türkçe karakterlerin bozulmadan yazılıp
    # okunduğundan emin olmak için açıkça UTF8 zorluyoruz.
    # UYARI: Bu satırı kaldırırsan Türkçe karakterler yine sorunsuz
    # YAZILABİLİR (Postgres UTF8 tutuyor zaten) ama Python tarafında geri
    # okurken/psql ile kontrol ederken karışıklık çıkabilir. Silme.
    conn.set_client_encoding("UTF8")
    try:
        yield conn
    finally:
        conn.close()


def upsert_and_get_id(cur, table: str, conflict_cols: list[str], data: dict, update_cols: list[str] | None = None):
    """"Bu kayıt var mı? Yoksa ekle, varsa mevcut id'sini ver" mantığının
    tek merkezi hali. Tüm lookup tabloları (carline, spec, renkler, ocn,
    bayiler, vb.) bunun üzerinden ekleniyor -- her endpoint dosyasında bunu
    tekrar yazmıyoruz.

    Parametreler:
        table: hangi tabloya yazılacak (örn. "carline")
        conflict_cols: hangi kolon(lar) bu kaydı "aynı" yapıyor (örn. ["kod"])
            -- bu kolon(lar) üzerinde veritabanında UNIQUE kısıtlaması
            OLMAK ZORUNDA, yoksa "ON CONFLICT" hata verir. Yeni bir tablo
            eklerken schema.sql'de bunu unutma.
        data: yazılacak tüm kolon -> değer eşlemesi
        update_cols: çakışma (zaten var) durumunda hangi kolonların
            güncelleneceği. None ise çakışmada HİÇBİR ŞEY değiştirilmez
            (ilk yazılan değer kalıcı kalır) -- örneğin bayi adı güncellenmek
            isteniyorsa bu listeye eklenmeli (bkz. etl.py'deki bayi upsert'i).

    Dönüş: kaydın id'si (yeni eklendiyse yeni id, zaten varsa mevcut id).

    UYARI (dikkatli değiştir): Bu fonksiyon SQL'i dinamik olarak (f-string
    ile) kuruyor. table/conflict_cols/update_cols asla kullanıcı girdisinden
    gelmemeli (sadece bizim kodumuzdaki sabit isimler) -- yoksa SQL
    injection riski oluşur. data içindeki VALUES ise güvenli (parametreli
    sorgu, %s ile) geçiyor.
    """
    if not data:
        raise ValueError("data boş olamaz")

    columns = list(data.keys())
    values = [data[c] for c in columns]
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    conflict_list = ", ".join(conflict_cols)

    if update_cols:
        # Kayıt zaten varsa update_cols'taki kolonları yeni değerle güncelle.
        set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
        query = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_list}) DO UPDATE SET {set_clause} "
            f"RETURNING id"
        )
    else:
        # Kayıt zaten varsa dokunma, sadece id'sini bulmamız gerekecek
        # (aşağıdaki SELECT ile).
        query = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_list}) DO NOTHING "
            f"RETURNING id"
        )

    cur.execute(query, values)
    row = cur.fetchone()
    if row:
        return row[0]

    # Buraya geldiysek: ON CONFLICT DO NOTHING devreye girdi (kayıt zaten
    # vardı) ve INSERT id döndürmedi. O yüzden conflict_cols'a göre ayrı bir
    # SELECT ile mevcut kaydı buluyoruz.
    where_clause = " AND ".join(
        [f"{c} IS NULL" if data.get(c) is None and c in conflict_cols else f"{c} = %s" for c in conflict_cols]
    )
    where_values = [data[c] for c in conflict_cols if data.get(c) is not None]
    cur.execute(f"SELECT id FROM {table} WHERE {where_clause}", where_values)
    row = cur.fetchone()
    return row[0] if row else None


def row_exists(cur, table: str, column: str, value) -> bool:
    """Basit bir "bu değer bu kolonda var mı?" kontrolü. Örn. fatura zaten
    işlenmiş mi diye bakmak için kullanılıyor (etl.py'de hyundai_fatura_id)."""
    cur.execute(f"SELECT 1 FROM {table} WHERE {column} = %s", [value])
    return cur.fetchone() is not None


def get_id_by(cur, table: str, column: str, value):
    """Bir kolona göre id bulur, yoksa None döner. upsert_and_get_id'den
    farkı: burası hiçbir şey INSERT etmez, sadece arar (örn. şasi zaten
    var mı diye bakmak için -- araclar tablosunda yeni kayıt açıp
    açmayacağımıza bunun sonucuna göre karar veriyoruz)."""
    cur.execute(f"SELECT id FROM {table} WHERE {column} = %s", [value])
    row = cur.fetchone()
    return row[0] if row else None

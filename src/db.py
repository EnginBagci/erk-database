"""PostgreSQL bağlantısı ve genel upsert yardımcıları."""
from contextlib import contextmanager

import psycopg2

from . import config


@contextmanager
def get_conn():
    conn = psycopg2.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        dbname=config.DB_NAME,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
    )
    try:
        yield conn
    finally:
        conn.close()


def upsert_and_get_id(cur, table: str, conflict_cols: list[str], data: dict, update_cols: list[str] | None = None):
    """data içindeki kolonları table'a INSERT eder, conflict_cols üzerinde
    çakışma varsa (varsa) update_cols'u günceller, yoksa mevcut kaydı bulup
    id'sini döner. update_cols verilmezse çakışmada hiçbir şey değiştirmez.

    Not: data içindeki tüm değerler None olabilir; bu durumda ilgili kolonlar
    NULL olarak yazılır -- çağıran tarafta gerekliyse önceden filtrelenmeli.
    """
    if not data:
        raise ValueError("data boş olamaz")

    columns = list(data.keys())
    values = [data[c] for c in columns]
    placeholders = ", ".join(["%s"] * len(columns))
    col_list = ", ".join(columns)
    conflict_list = ", ".join(conflict_cols)

    if update_cols:
        set_clause = ", ".join([f"{c} = EXCLUDED.{c}" for c in update_cols])
        query = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_list}) DO UPDATE SET {set_clause} "
            f"RETURNING id"
        )
    else:
        query = (
            f"INSERT INTO {table} ({col_list}) VALUES ({placeholders}) "
            f"ON CONFLICT ({conflict_list}) DO NOTHING "
            f"RETURNING id"
        )

    cur.execute(query, values)
    row = cur.fetchone()
    if row:
        return row[0]

    # ON CONFLICT DO NOTHING id döndürmez -> mevcut kaydı conflict_cols ile bul
    where_clause = " AND ".join(
        [f"{c} IS NULL" if data.get(c) is None and c in conflict_cols else f"{c} = %s" for c in conflict_cols]
    )
    where_values = [data[c] for c in conflict_cols if data.get(c) is not None]
    cur.execute(f"SELECT id FROM {table} WHERE {where_clause}", where_values)
    row = cur.fetchone()
    return row[0] if row else None


def row_exists(cur, table: str, column: str, value) -> bool:
    cur.execute(f"SELECT 1 FROM {table} WHERE {column} = %s", [value])
    return cur.fetchone() is not None


def get_id_by(cur, table: str, column: str, value):
    cur.execute(f"SELECT id FROM {table} WHERE {column} = %s", [value])
    row = cur.fetchone()
    return row[0] if row else None

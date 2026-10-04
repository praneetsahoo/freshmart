"""
Component 3: ETL - Extract raw store files, Transform (clean), Load into MySQL.

Flow for each new file:
  1. skip it if etl_audit says it was already loaded      (idempotency)
  2. read CSV from storage (local or S3)                   (Extract)
  3. clean(): fix dates, names, prices, drop duplicates    (Transform)
  4. insert good rows into fact_sales + write audit row    (Load, one DB transaction)
  5. write bad rows to rejected/ with a reason

Run:  python src/etl.py
"""
import re

import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

import config
import storage

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"]


# ---------------------------------------------------------------- helpers
def normalize_name(name):
    """'  Banana-Dozen ' / 'BANANA DOZEN' -> 'banana dozen' (used to match products)."""
    name = str(name).lower().replace("-", " ").strip()
    return re.sub(r"\s+", " ", name)


def parse_dates(series):
    """Try each known format; anything that matches none stays NaT (rejected later)."""
    result = pd.Series(pd.NaT, index=series.index, dtype="datetime64[ns]")
    for fmt in DATE_FORMATS:
        parsed = pd.to_datetime(series, format=fmt, errors="coerce")
        result = result.fillna(parsed)
    return result


# ---------------------------------------------------------------- transform
def clean(df, products):
    """
    Input : raw DataFrame (all text) + product master DataFrame
    Output: (clean_df ready for fact_sales, rejected_df with a 'reason' column)
    Pure function - no DB or S3 - so it is easy to unit test.
    """
    df = df.copy()
    for col in df.columns:
        df[col] = df[col].astype(str).str.strip()

    # 1. duplicates inside the file (billing system exported a row twice)
    df = df.drop_duplicates(subset="transaction_id", keep="first")

    # 2. product_id: fill missing IDs by matching the cleaned product name
    name_to_id = {normalize_name(n): pid for pid, n in zip(products.product_id, products.product_name)}
    missing_id = df["product_id"].eq("")
    df.loc[missing_id, "product_id"] = df.loc[missing_id, "product_name"].map(normalize_name).map(name_to_id)
    df["product_id"] = df["product_id"].replace("", np.nan)

    # 3. dates in 3 different formats -> one real date
    df["sale_date"] = parse_dates(df["date"]).dt.date

    # 4. numbers
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce")
    df["unit_price"] = pd.to_numeric(df["unit_price"], errors="coerce")
    price_lookup = dict(zip(products.product_id, products.list_price.astype(float)))
    df["unit_price"] = df["unit_price"].fillna(df["product_id"].map(price_lookup))  # fill from master

    # 5. decide what is rejected (and why) - we never silently drop data
    known_products = set(products.product_id)
    reasons = pd.Series("", index=df.index)
    reasons[df["product_id"].isna() | ~df["product_id"].isin(known_products)] += "unknown_product;"
    reasons[df["sale_date"].isna()] += "bad_date;"
    reasons[df["quantity"].isna() | (df["quantity"] <= 0)] += "bad_quantity;"
    reasons[df["unit_price"].isna() | (df["unit_price"] <= 0)] += "bad_price;"
    reasons[df["transaction_id"].eq("")] += "missing_transaction_id;"

    bad = reasons != ""
    rejected = df[bad].assign(reason=reasons[bad])
    good = df[~bad].copy()

    good["quantity"] = good["quantity"].astype(int)
    good["amount"] = (good["quantity"] * good["unit_price"]).round(2)
    good = good[["transaction_id", "store_id", "product_id", "sale_date",
                 "quantity", "unit_price", "amount", "payment_mode"]]
    return good, rejected


# ---------------------------------------------------------------- load
def load_masters(engine):
    """Upsert store and product masters into the dimension tables."""
    stores = storage.read_csv("master/stores.csv")
    products = storage.read_csv("master/products.csv")
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO dim_store (store_id, city, region, store_manager)
            VALUES (:store_id, :city, :region, :store_manager)
            ON DUPLICATE KEY UPDATE city=VALUES(city), region=VALUES(region),
                                    store_manager=VALUES(store_manager)"""),
            stores.to_dict("records"))
        conn.execute(text("""
            INSERT INTO dim_product (product_id, product_name, category, list_price)
            VALUES (:product_id, :product_name, :category, :list_price)
            ON DUPLICATE KEY UPDATE product_name=VALUES(product_name),
                                    category=VALUES(category), list_price=VALUES(list_price)"""),
            products.to_dict("records"))
    return products


def already_loaded(engine, key):
    with engine.connect() as conn:
        return conn.execute(text("SELECT 1 FROM etl_audit WHERE file_name=:f"), {"f": key}).first() is not None


def process_file(engine, key, products):
    """Returns a small summary dict, or None if the file was already loaded."""
    if already_loaded(engine, key):
        return None

    raw = storage.read_csv(key)
    good, rejected = clean(raw, products)
    good["source_file"] = key

    # One transaction: either the rows AND the audit row are saved, or nothing is.
    with engine.begin() as conn:
        inserted = 0
        if len(good):
            result = conn.execute(text("""
                INSERT IGNORE INTO fact_sales
                  (transaction_id, store_id, product_id, sale_date, quantity,
                   unit_price, amount, payment_mode, source_file)
                VALUES (:transaction_id, :store_id, :product_id, :sale_date, :quantity,
                        :unit_price, :amount, :payment_mode, :source_file)"""),
                good.to_dict("records"))
            inserted = result.rowcount   # INSERT IGNORE skips cross-file duplicates
        conn.execute(text("""
            INSERT INTO etl_audit (file_name, rows_read, rows_loaded, rows_rejected)
            VALUES (:f, :r, :l, :j)"""),
            {"f": key, "r": len(raw), "l": inserted, "j": len(rejected)})

    if len(rejected):
        storage.write_csv(rejected, key.replace("raw/", "rejected/", 1))
    return {"file": key, "read": len(raw), "loaded": inserted, "rejected": len(rejected)}


def run():
    engine = create_engine(config.DB_URL, pool_pre_ping=True)
    products = load_masters(engine)
    files = storage.list_raw_files()
    totals = {"files": 0, "skipped": 0, "read": 0, "loaded": 0, "rejected": 0}

    for key in files:
        try:
            summary = process_file(engine, key, products)
        except Exception as exc:   # one bad file must not stop the whole run
            print(f"FAILED {key}: {exc}")
            continue
        if summary is None:
            totals["skipped"] += 1
            continue
        totals["files"] += 1
        for k in ("read", "loaded", "rejected"):
            totals[k] += summary[k]

    print(f"ETL done | storage={config.STORAGE} | new files={totals['files']} "
          f"skipped(already loaded)={totals['skipped']} | rows read={totals['read']:,} "
          f"loaded={totals['loaded']:,} rejected={totals['rejected']:,}")
    return engine


if __name__ == "__main__":
    import anomaly
    eng = run()
    anomaly.run(eng)

"""
Component 7: automated tests.  Run:  pytest -v
They cover the happy path, messy data, edge cases, and S3 access (mocked, no real AWS needed).
"""
import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import anomaly  # noqa: E402
import config   # noqa: E402
import etl      # noqa: E402
import storage  # noqa: E402

PRODUCTS = pd.DataFrame({
    "product_id": ["P001", "P002"],
    "product_name": ["Basmati Rice 5kg", "Banana Dozen"],
    "category": ["Grains", "Fruits"],
    "list_price": ["650", "60"],
})


def raw(rows):
    cols = ["transaction_id", "store_id", "date", "product_id", "product_name",
            "quantity", "unit_price", "payment_mode"]
    return pd.DataFrame(rows, columns=cols).astype(str)


# ---------------- clean() ----------------
def test_happy_path_row_is_loaded():
    good, bad = etl.clean(raw([["T1", "S001", "2026-09-30", "P001", "Basmati Rice 5kg", "2", "650", "UPI"]]), PRODUCTS)
    assert len(good) == 1 and len(bad) == 0
    assert good.iloc[0]["amount"] == 1300


def test_duplicates_removed():
    row = ["T1", "S001", "2026-09-30", "P001", "x", "1", "650", "UPI"]
    good, _ = etl.clean(raw([row, row]), PRODUCTS)
    assert len(good) == 1


def test_all_three_date_formats_parse_to_same_date():
    rows = [[f"T{i}", "S001", d, "P001", "x", "1", "650", "UPI"]
            for i, d in enumerate(["2026-09-30", "30/09/2026", "30-09-2026"])]
    good, bad = etl.clean(raw(rows), PRODUCTS)
    assert len(bad) == 0
    assert good["sale_date"].nunique() == 1


def test_missing_product_id_recovered_from_messy_name():
    good, bad = etl.clean(raw([["T1", "S001", "2026-09-30", "", "  BANANA-dozen ", "1", "60", "UPI"]]), PRODUCTS)
    assert len(bad) == 0
    assert good.iloc[0]["product_id"] == "P002"


def test_missing_price_filled_from_master():
    good, _ = etl.clean(raw([["T1", "S001", "2026-09-30", "P002", "x", "3", "", "UPI"]]), PRODUCTS)
    assert good.iloc[0]["unit_price"] == 60
    assert good.iloc[0]["amount"] == 180


@pytest.mark.parametrize("row, reason", [
    (["T1", "S001", "2026-09-30", "P001", "x", "", "650", "UPI"], "bad_quantity"),
    (["T1", "S001", "2026-09-30", "P001", "x", "-2", "650", "UPI"], "bad_quantity"),
    (["T1", "S001", "31/31/2026", "P001", "x", "1", "650", "UPI"], "bad_date"),
    (["T1", "S001", "2026-09-30", "", "Unknown Item", "1", "10", "UPI"], "unknown_product"),
])
def test_invalid_rows_are_rejected_with_reason(row, reason):
    good, bad = etl.clean(raw([row]), PRODUCTS)
    assert len(good) == 0
    assert reason in bad.iloc[0]["reason"]


def test_empty_file():
    good, bad = etl.clean(raw([]), PRODUCTS)
    assert len(good) == 0 and len(bad) == 0


# ---------------- anomaly ----------------
def daily_series(values, store="S001"):
    dates = pd.date_range("2026-09-01", periods=len(values)).date
    return pd.DataFrame({"store_id": store, "sale_date": dates, "revenue": values})


def test_spike_is_flagged_high():
    values = [100, 102, 98, 101, 99, 100, 103, 97, 100, 101, 300]
    flagged = anomaly.compute_anomalies(daily_series(values))
    assert len(flagged) == 1 and flagged.iloc[0]["direction"] == "HIGH"


def test_drop_is_flagged_low():
    values = [100, 102, 98, 101, 99, 100, 103, 97, 100, 101, 20]
    flagged = anomaly.compute_anomalies(daily_series(values))
    assert flagged.iloc[0]["direction"] == "LOW"


def test_normal_days_not_flagged():
    values = [100, 102, 98, 101, 99, 100, 103, 97, 100, 101, 102]
    assert anomaly.compute_anomalies(daily_series(values)).empty


def test_not_enough_history_not_flagged():
    assert anomaly.compute_anomalies(daily_series([100, 101, 500])).empty


def test_each_store_judged_against_itself():
    big = daily_series([1000] * 9 + [1010, 990, 1005], "S_BIG")
    small = daily_series([100] * 9 + [101, 99, 100], "S_SMALL")
    assert anomaly.compute_anomalies(pd.concat([big, small])).empty


# ---------------- S3 (mocked with moto - no real AWS account needed) ----------------
def test_s3_list_read_write(monkeypatch):
    moto = pytest.importorskip("moto")
    import boto3
    with moto.mock_aws():
        monkeypatch.setattr(config, "STORAGE", "s3")
        monkeypatch.setattr(config, "S3_BUCKET", "test-bucket")
        s3 = boto3.client("s3", region_name=config.AWS_REGION)
        s3.create_bucket(Bucket="test-bucket",
                         CreateBucketConfiguration={"LocationConstraint": config.AWS_REGION})
        s3.put_object(Bucket="test-bucket", Key="raw/2026-09-30/S001.csv",
                      Body=b"transaction_id,store_id\nT1,S001\n")

        assert storage.list_raw_files() == ["raw/2026-09-30/S001.csv"]
        df = storage.read_csv("raw/2026-09-30/S001.csv")
        assert df.iloc[0]["transaction_id"] == "T1"

        storage.write_csv(df, "rejected/2026-09-30/S001.csv")
        keys = [o["Key"] for o in s3.list_objects_v2(Bucket="test-bucket")["Contents"]]
        assert "rejected/2026-09-30/S001.csv" in keys

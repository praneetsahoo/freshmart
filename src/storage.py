"""
Storage layer: read/write files from LOCAL disk or AWS S3 with the same functions.

Key layout (identical locally and in S3):
  master/stores.csv, master/products.csv
  raw/<YYYY-MM-DD>/<store_id>.csv      <- landing zone, never modified
  rejected/<YYYY-MM-DD>/<store_id>.csv <- bad rows + reason
"""
import io
import os

import pandas as pd

import config


def _s3():
    import boto3  # imported only when S3 is used
    # No access keys in code: boto3 picks up the EC2 IAM role automatically
    return boto3.client("s3", region_name=config.AWS_REGION)


def list_raw_files():
    """Return all raw file keys like 'raw/2026-09-01/S001.csv', sorted."""
    if config.STORAGE == "s3":
        keys = []
        paginator = _s3().get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=config.S3_BUCKET, Prefix="raw/"):
            keys += [o["Key"] for o in page.get("Contents", []) if o["Key"].endswith(".csv")]
        return sorted(keys)

    base = config.LOCAL_DATA_DIR
    keys = []
    for root, _, files in os.walk(os.path.join(base, "raw")):
        for f in files:
            if f.endswith(".csv"):
                keys.append(os.path.relpath(os.path.join(root, f), base).replace(os.sep, "/"))
    return sorted(keys)


def read_csv(key):
    """Read a CSV as all-text columns (we clean types ourselves in the ETL)."""
    if config.STORAGE == "s3":
        obj = _s3().get_object(Bucket=config.S3_BUCKET, Key=key)
        return pd.read_csv(io.BytesIO(obj["Body"].read()), dtype=str, keep_default_na=False)
    return pd.read_csv(os.path.join(config.LOCAL_DATA_DIR, key), dtype=str, keep_default_na=False)


def write_csv(df, key):
    if config.STORAGE == "s3":
        _s3().put_object(Bucket=config.S3_BUCKET, Key=key, Body=df.to_csv(index=False).encode())
        return
    path = os.path.join(config.LOCAL_DATA_DIR, key)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    df.to_csv(path, index=False)


def upload_local_folder_to_s3(local_dir, bucket):
    """Helper used once on AWS: copy local data/ (masters + raw) into the bucket."""
    import boto3
    s3 = boto3.client("s3", region_name=config.AWS_REGION)
    count = 0
    for root, _, files in os.walk(local_dir):
        for f in files:
            if f.endswith(".csv") and "rejected" not in root:
                path = os.path.join(root, f)
                key = os.path.relpath(path, local_dir).replace(os.sep, "/")
                s3.upload_file(path, bucket, key)
                count += 1
    print(f"Uploaded {count} files to s3://{bucket}/")

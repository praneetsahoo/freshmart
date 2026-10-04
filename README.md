# FreshMart Store Performance Platform

Daily sales CSVs from every store → cleaned automatically → MySQL → management dashboard with anomaly alerts.

```
Store CSVs ─▶ S3 raw/ ─▶ EC2: Python ETL (Pandas) ─▶ RDS MySQL ─▶ Streamlit dashboard
                              │                       ▲
                              ├─▶ S3 rejected/        └── anomaly.py (z-score + 30% rule)
                              └─▶ etl_audit table
IAM role (no keys in code) · RDS private (only reachable from EC2) · DB secret in SSM Parameter Store
```

## Project layout
| Path | What it does |
|---|---|
| `src/generate_data.py` | Creates 30 days of deliberately messy test data |
| `src/config.py` | All settings from env vars; `STORAGE=local` or `s3` |
| `src/storage.py` | Same read/write functions for local disk and S3 |
| `src/etl.py` | Clean + load, idempotent (never loads a file twice) |
| `src/anomaly.py` | Flags store-days far from that store's normal |
| `src/init_db.py` | Creates tables from `sql/schema.sql` |
| `dashboard/app.py` | Streamlit + Matplotlib dashboard |
| `tests/` | 16 pytest cases incl. mocked S3 |
| `deploy/` | One-command AWS setup and teardown |

## Run locally
```bash
pip install -r requirements.txt
# MySQL running locally with user fm / fm_pass (or set DB_URL)
python src/init_db.py
python src/generate_data.py
python src/etl.py
streamlit run dashboard/app.py
pytest -v
```

## Deploy to AWS (AWS CloudShell, region ap-southeast-2)
```bash
git clone <this repo> && cd freshmart
export REPO_URL=<this repo's https URL>
export MY_IP=<your laptop IP from checkip.amazonaws.com>
bash deploy/setup_aws.sh      # ~10-15 min, prints the dashboard URL
bash deploy/teardown.sh       # delete everything afterwards
```

## Scale-up path
| Today (MVP) | At 100x |
|---|---|
| Pandas on EC2 | PySpark on AWS Glue / EMR |
| CSV in S3 | Parquet in S3, partitioned by date |
| RDS MySQL for reports | Athena / Redshift for analytics, RDS for serving |
| systemd timer at 02:00 | S3 event → Lambda / Step Functions |
| Streamlit on one EC2 | Load balancer + auto scaling, or QuickSight |

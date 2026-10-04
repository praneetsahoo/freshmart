"""
All settings in one place, read from environment variables.
The SAME code runs locally and on AWS - only these values change.

Local:  STORAGE=local  DB_URL=mysql+pymysql://fm:fm_pass@localhost/freshmart
AWS:    STORAGE=s3     S3_BUCKET=freshmart-data-xxxx
        DB_URL=mysql+pymysql://admin:<pw>@<rds-endpoint>:3306/freshmart
"""
import os

STORAGE = os.getenv("STORAGE", "local")            # "local" or "s3"
S3_BUCKET = os.getenv("S3_BUCKET", "")
AWS_REGION = os.getenv("AWS_REGION", "ap-southeast-2")
LOCAL_DATA_DIR = os.getenv(
    "LOCAL_DATA_DIR", os.path.join(os.path.dirname(__file__), "..", "data"))
DB_URL = os.getenv("DB_URL", "mysql+pymysql://fm:fm_pass@localhost/freshmart")

# anomaly settings
ANOMALY_WINDOW_DAYS = 14   # compare today with the previous 14 days
ANOMALY_MIN_HISTORY = 7    # need at least 7 days before we judge
ANOMALY_Z_THRESHOLD = 3.0  # |z| above this = statistically unusual
ANOMALY_MIN_PCT = 0.30     # AND at least 30% away from normal = big enough to matter

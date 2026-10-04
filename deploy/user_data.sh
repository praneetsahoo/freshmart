#!/bin/bash
# EC2 boot script: runs ONCE automatically when the server first starts.
# setup_aws.sh fills in the __PLACEHOLDERS__ before launching the instance.
# Progress log on the server: /var/log/freshmart-setup.log
exec > /var/log/freshmart-setup.log 2>&1
set -eux

REGION="__REGION__"
BUCKET="__BUCKET__"
REPO_URL="__REPO_URL__"

# 1. Software
dnf install -y git python3.11 python3.11-pip
git clone "$REPO_URL" /opt/freshmart
cd /opt/freshmart
python3.11 -m venv venv
./venv/bin/pip install --quiet -r requirements.txt

# 2. Settings. DB password comes from SSM Parameter Store (encrypted), never from code.
DB_URL=$(aws ssm get-parameter --name /freshmart/db_url --with-decryption \
          --query Parameter.Value --output text --region "$REGION")
cat > /opt/freshmart/.env <<EOF
STORAGE=s3
S3_BUCKET=$BUCKET
AWS_REGION=$REGION
DB_URL=$DB_URL
EOF
chmod 600 /opt/freshmart/.env
set -a; . /opt/freshmart/.env; set +a

# 3. Create tables on RDS
./venv/bin/python src/init_db.py

# 4. Demo data -> S3 (on hackathon day: upload the SME's files instead)
./venv/bin/python src/generate_data.py
./venv/bin/python -c "import sys; sys.path.insert(0,'src'); import storage; storage.upload_local_folder_to_s3('data', '$BUCKET')"
rm -rf data/raw   # prove the ETL really reads from S3, not local disk

# 5. First ETL run: S3 -> clean -> RDS
./venv/bin/python src/etl.py

# 6. Dashboard as a service (restarts automatically if it crashes or the server reboots)
cat > /etc/systemd/system/freshmart-dashboard.service <<EOF
[Unit]
Description=FreshMart Streamlit dashboard
After=network-online.target
[Service]
WorkingDirectory=/opt/freshmart
EnvironmentFile=/opt/freshmart/.env
ExecStart=/opt/freshmart/venv/bin/streamlit run dashboard/app.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
Restart=always
[Install]
WantedBy=multi-user.target
EOF

# 7. Nightly ETL at 02:00 server time (new store files arrive overnight)
cat > /etc/systemd/system/freshmart-etl.service <<EOF
[Unit]
Description=FreshMart nightly ETL
[Service]
Type=oneshot
WorkingDirectory=/opt/freshmart
EnvironmentFile=/opt/freshmart/.env
ExecStart=/opt/freshmart/venv/bin/python src/etl.py
EOF
cat > /etc/systemd/system/freshmart-etl.timer <<EOF
[Unit]
Description=Run FreshMart ETL nightly
[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true
[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now freshmart-dashboard.service freshmart-etl.timer
echo "FRESHMART SETUP COMPLETE"

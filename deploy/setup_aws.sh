#!/bin/bash
# =============================================================================
# FreshMart: one-command AWS deployment.  Run in AWS CloudShell (no installs).
#
#   export REPO_URL=https://github.com/<you>/freshmart.git   # public repo
#   export MY_IP=$(curl -s https://checkip.amazonaws.com)   # ONLY if run from your laptop
#   bash deploy/setup_aws.sh
#
# In CloudShell, MY_IP must be YOUR laptop's IP (open checkip.amazonaws.com in your
# browser), because CloudShell's own IP is not yours.
#
# Creates:  S3 bucket -> IAM role -> security groups -> RDS MySQL -> EC2 (ETL + dashboard)
# Time:     ~10-15 min (RDS creation is the slow part)
# Undo:     bash deploy/teardown.sh
# =============================================================================
set -euo pipefail

REGION="${REGION:-ap-southeast-2}"
NAME="freshmart"
DB_CLASS="${DB_CLASS:-db.t3.micro}"
EC2_TYPE="${EC2_TYPE:-t3.micro}"
: "${REPO_URL:?Set REPO_URL to your public GitHub repo URL}"
: "${MY_IP:?Set MY_IP to your laptop public IP (see checkip.amazonaws.com)}"
export AWS_DEFAULT_REGION="$REGION"

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="${NAME}-data-${ACCOUNT}"
STATE="$HOME/${NAME}-aws.env"
log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

# ---------------------------------------------------------------- 1. S3
log "1/6 S3 bucket $BUCKET (private, versioned, encrypted)"
aws s3api create-bucket --bucket "$BUCKET" \
  --create-bucket-configuration LocationConstraint="$REGION" >/dev/null 2>&1 || echo "bucket exists"
aws s3api put-public-access-block --bucket "$BUCKET" --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
aws s3api put-bucket-versioning --bucket "$BUCKET" --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket "$BUCKET" --server-side-encryption-configuration \
  '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'

# ---------------------------------------------------------------- 2. IAM
log "2/6 IAM role for EC2 (least privilege: only this bucket + its DB secret)"
aws iam create-role --role-name "${NAME}-ec2-role" --assume-role-policy-document '{
  "Version":"2012-10-17","Statement":[{"Effect":"Allow",
  "Principal":{"Service":"ec2.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null 2>&1 || echo "role exists"
aws iam put-role-policy --role-name "${NAME}-ec2-role" --policy-name "${NAME}-access" --policy-document "{
  \"Version\":\"2012-10-17\",\"Statement\":[
   {\"Effect\":\"Allow\",\"Action\":[\"s3:ListBucket\"],\"Resource\":\"arn:aws:s3:::${BUCKET}\"},
   {\"Effect\":\"Allow\",\"Action\":[\"s3:GetObject\",\"s3:PutObject\"],\"Resource\":\"arn:aws:s3:::${BUCKET}/*\"},
   {\"Effect\":\"Allow\",\"Action\":[\"ssm:GetParameter\"],
    \"Resource\":\"arn:aws:ssm:${REGION}:${ACCOUNT}:parameter/${NAME}/*\"}]}"
# Session Manager = browser shell into EC2 with no SSH keys / no port 22
aws iam attach-role-policy --role-name "${NAME}-ec2-role" \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore
aws iam create-instance-profile --instance-profile-name "${NAME}-ec2-profile" >/dev/null 2>&1 || true
aws iam add-role-to-instance-profile --instance-profile-name "${NAME}-ec2-profile" \
  --role-name "${NAME}-ec2-role" 2>/dev/null || true

# ---------------------------------------------------------------- 3. Network
log "3/6 Security groups (dashboard: your IP only; DB: app server only)"
VPC_ID=$(aws ec2 describe-vpcs --filters Name=isDefault,Values=true --query 'Vpcs[0].VpcId' --output text)
[ "$VPC_ID" = "None" ] && { echo "No default VPC in $REGION"; exit 1; }
sg() {  # get-or-create a security group, print its id
  local id
  id=$(aws ec2 describe-security-groups --filters Name=group-name,Values="$1" Name=vpc-id,Values="$VPC_ID" \
       --query 'SecurityGroups[0].GroupId' --output text)
  if [ "$id" = "None" ]; then
    id=$(aws ec2 create-security-group --group-name "$1" --description "$2" --vpc-id "$VPC_ID" \
         --query GroupId --output text)
  fi
  echo "$id"
}
APP_SG=$(sg "${NAME}-app-sg" "FreshMart dashboard server")
DB_SG=$(sg "${NAME}-db-sg" "FreshMart RDS - only reachable from app server")
aws ec2 authorize-security-group-ingress --group-id "$APP_SG" --protocol tcp --port 8501 \
  --cidr "${MY_IP}/32" >/dev/null 2>&1 || true
aws ec2 authorize-security-group-ingress --group-id "$DB_SG" --protocol tcp --port 3306 \
  --source-group "$APP_SG" >/dev/null 2>&1 || true

# ---------------------------------------------------------------- 4. RDS
log "4/6 RDS MySQL (private, encrypted) - takes 5-10 minutes"
if ! aws rds describe-db-instances --db-instance-identifier "${NAME}-db" >/dev/null 2>&1; then
  DB_PASS=$(openssl rand -base64 32 | tr -dc 'A-Za-z0-9' | head -c 20)
  aws rds create-db-instance --db-instance-identifier "${NAME}-db" --engine mysql \
    --db-instance-class "$DB_CLASS" --allocated-storage 20 \
    --master-username admin --master-user-password "$DB_PASS" \
    --vpc-security-group-ids "$DB_SG" --no-publicly-accessible --storage-encrypted \
    --backup-retention-period 1 --no-multi-az >/dev/null
  aws rds wait db-instance-available --db-instance-identifier "${NAME}-db"
  DB_HOST=$(aws rds describe-db-instances --db-instance-identifier "${NAME}-db" \
            --query 'DBInstances[0].Endpoint.Address' --output text)
  # Store the connection string encrypted in SSM Parameter Store
  aws ssm put-parameter --name "/${NAME}/db_url" --type SecureString --overwrite \
    --value "mysql+pymysql://admin:${DB_PASS}@${DB_HOST}:3306/freshmart?ssl_ca=/opt/freshmart/rds-ca.pem" >/dev/null
else
  echo "RDS already exists"
  aws rds wait db-instance-available --db-instance-identifier "${NAME}-db"
fi

# ---------------------------------------------------------------- 5. EC2
log "5/6 EC2 server (runs ETL + dashboard)"
AMI=$(aws ssm get-parameter --name /aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64 \
      --query Parameter.Value --output text)
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_DATA=$(mktemp)
sed -e "s|__REGION__|$REGION|g" -e "s|__BUCKET__|$BUCKET|g" -e "s|__REPO_URL__|$REPO_URL|g" \
  "$SCRIPT_DIR/user_data.sh" > "$USER_DATA"
sleep 10   # give the new IAM instance profile time to propagate
INSTANCE_ID=$(aws ec2 run-instances --image-id "$AMI" --instance-type "$EC2_TYPE" \
  --iam-instance-profile Name="${NAME}-ec2-profile" --security-group-ids "$APP_SG" \
  --user-data "file://$USER_DATA" --metadata-options HttpTokens=required \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=${NAME}-app}]" \
  --query 'Instances[0].InstanceId' --output text)
aws ec2 wait instance-running --instance-ids "$INSTANCE_ID"
PUBLIC_IP=$(aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' --output text)

# ---------------------------------------------------------------- 6. Save state
cat > "$STATE" <<EOF
REGION=$REGION
BUCKET=$BUCKET
APP_SG=$APP_SG
DB_SG=$DB_SG
INSTANCE_ID=$INSTANCE_ID
PUBLIC_IP=$PUBLIC_IP
EOF
log "6/6 Done"
echo "Dashboard:  http://${PUBLIC_IP}:8501   (ready in ~5 min while the server installs itself)"
echo "Server log: open EC2 console -> ${NAME}-app -> Connect -> Session Manager, then:"
echo "            sudo tail -f /var/log/freshmart-setup.log"
echo "Resource IDs saved to $STATE (used by teardown.sh)"

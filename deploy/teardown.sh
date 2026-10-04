#!/bin/bash
# Delete everything setup_aws.sh created, so nothing keeps costing money.
# Run in CloudShell:  bash deploy/teardown.sh
set -uo pipefail
NAME="freshmart"
STATE="$HOME/${NAME}-aws.env"
# shellcheck disable=SC1090
[ -f "$STATE" ] && . "$STATE"
REGION="${REGION:-ap-southeast-2}"
export AWS_DEFAULT_REGION="$REGION"
ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
BUCKET="${BUCKET:-${NAME}-data-${ACCOUNT}}"
echo "This will DELETE the FreshMart server, database, bucket and IAM role in $REGION."
read -r -p "Type 'delete' to continue: " ok
[ "$ok" = "delete" ] || { echo "Cancelled"; exit 0; }

IDS=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=${NAME}-app" \
      "Name=instance-state-name,Values=pending,running,stopped" \
      --query 'Reservations[].Instances[].InstanceId' --output text)
if [ -n "$IDS" ]; then
  echo "Terminating EC2 $IDS"; aws ec2 terminate-instances --instance-ids $IDS >/dev/null
  aws ec2 wait instance-terminated --instance-ids $IDS
fi

echo "Deleting RDS (5-10 min)"
aws rds delete-db-instance --db-instance-identifier "${NAME}-db" \
  --skip-final-snapshot --delete-automated-backups >/dev/null 2>&1 && \
  aws rds wait db-instance-deleted --db-instance-identifier "${NAME}-db"

for g in "${NAME}-db-sg" "${NAME}-app-sg"; do
  id=$(aws ec2 describe-security-groups --filters Name=group-name,Values="$g" \
       --query 'SecurityGroups[0].GroupId' --output text 2>/dev/null)
  [ "$id" != "None" ] && [ -n "$id" ] && aws ec2 delete-security-group --group-id "$id" && echo "Deleted $g"
done

aws ssm delete-parameters --names "/${NAME}/db_url" "/${NAME}/db_password" >/dev/null 2>&1

echo "Emptying and deleting bucket $BUCKET (including old versions)"
python3 - "$BUCKET" <<'EOF'
import sys, boto3
b = boto3.resource("s3").Bucket(sys.argv[1])
try:
    b.object_versions.delete(); b.delete(); print("bucket deleted")
except Exception as e:
    print("bucket:", e)
EOF

aws iam remove-role-from-instance-profile --instance-profile-name "${NAME}-ec2-profile" \
  --role-name "${NAME}-ec2-role" 2>/dev/null
aws iam delete-instance-profile --instance-profile-name "${NAME}-ec2-profile" 2>/dev/null
aws iam detach-role-policy --role-name "${NAME}-ec2-role" \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore 2>/dev/null
aws iam delete-role-policy --role-name "${NAME}-ec2-role" --policy-name "${NAME}-access" 2>/dev/null
aws iam delete-role --role-name "${NAME}-ec2-role" 2>/dev/null && echo "Deleted IAM role"
rm -f "$STATE"
echo "Teardown complete."

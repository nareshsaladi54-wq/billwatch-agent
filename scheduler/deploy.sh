#!/usr/bin/env bash
# Provisions the "runs in the background" piece: a tiny Lambda that calls
# invoke_agent_runtime, triggered nightly by an EventBridge Scheduler cron.
#
# Usage: ./deploy.sh [cron-expression]
#   Default cron: 11:00 UTC daily (07:00 America/New_York). Pass your own,
#   e.g. ./deploy.sh "cron(0 13 * * ? *)"
set -euo pipefail
cd "$(dirname "$0")"

REGION="${AWS_REGION:-us-east-1}"
ACCOUNT="$(aws sts get-caller-identity --query Account --output text)"
SCHEDULE_EXPR="${1:-cron(0 11 * * ? *)}"
PROMPT="${PROMPT:-Do your nightly check and tell me only what I need to act on.}"

FUNCTION_NAME="billwatch-nightly"
LAMBDA_ROLE_NAME="billwatch-nightly-lambda-role"
SCHEDULER_ROLE_NAME="billwatch-nightly-scheduler-role"
SCHEDULE_NAME="billwatch-nightly"

echo "==> Resolving the deployed Runtime ARN"
RUNTIME_ARN="$(cd .. && agentcore status --json | python3 -c '
import json, sys
data = json.load(sys.stdin)
for r in data.get("resources", []):
    if r.get("resourceType") == "agent":
        print(r["identifier"])
        break
')"
if [ -z "$RUNTIME_ARN" ]; then
  echo "Could not resolve the Runtime ARN from 'agentcore status'. Deploy the runtime first." >&2
  exit 1
fi
echo "    $RUNTIME_ARN"

echo "==> Lambda execution role"
if ! aws iam get-role --role-name "$LAMBDA_ROLE_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws iam create-role --role-name "$LAMBDA_ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }' >/dev/null
  aws iam attach-role-policy --role-name "$LAMBDA_ROLE_NAME" \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
fi
aws iam put-role-policy --role-name "$LAMBDA_ROLE_NAME" --policy-name invoke-agent-runtime \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{\"Effect\": \"Allow\", \"Action\": \"bedrock-agentcore:InvokeAgentRuntime\",
      \"Resource\": [\"$RUNTIME_ARN\", \"$RUNTIME_ARN/runtime-endpoint/*\"]}]
  }" >/dev/null
echo "    waiting for IAM propagation..."
sleep 8

echo "==> Lambda function (vendoring current boto3/botocore - Lambda's built-in one may predate this API)"
rm -rf /tmp/billwatch-nightly-build && mkdir -p /tmp/billwatch-nightly-build
pip3 install -q --platform manylinux2014_x86_64 --only-binary=:all: --python-version 3.13 \
  --target /tmp/billwatch-nightly-build boto3
cp lambda_function.py /tmp/billwatch-nightly-build/
(cd /tmp/billwatch-nightly-build && zip -q -r function.zip . -x "*.dist-info/*")

ENV_JSON="$(python3 -c '
import json, os, sys
print(json.dumps({"Variables": {
    "AGENT_RUNTIME_ARN": sys.argv[1],
    "QUALIFIER": "DEFAULT",
    "ACTOR_ID": "demo",
    "PROMPT": sys.argv[2],
}}))
' "$RUNTIME_ARN" "$PROMPT")"

LAMBDA_ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${LAMBDA_ROLE_NAME}"
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws lambda update-function-code --function-name "$FUNCTION_NAME" --region "$REGION" \
    --zip-file "fileb:///tmp/billwatch-nightly-build/function.zip" >/dev/null
  aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"
  aws lambda update-function-configuration --function-name "$FUNCTION_NAME" --region "$REGION" \
    --environment "$ENV_JSON" >/dev/null
else
  aws lambda create-function --function-name "$FUNCTION_NAME" --region "$REGION" \
    --runtime python3.13 --handler lambda_function.handler --role "$LAMBDA_ROLE_ARN" \
    --timeout 60 --memory-size 256 \
    --zip-file "fileb:///tmp/billwatch-nightly-build/function.zip" \
    --environment "$ENV_JSON" >/dev/null
fi
LAMBDA_ARN="arn:aws:lambda:${REGION}:${ACCOUNT}:function:${FUNCTION_NAME}"
echo "    $LAMBDA_ARN"

echo "==> EventBridge Scheduler execution role"
if ! aws iam get-role --role-name "$SCHEDULER_ROLE_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws iam create-role --role-name "$SCHEDULER_ROLE_NAME" \
    --assume-role-policy-document '{
      "Version": "2012-10-17",
      "Statement": [{"Effect": "Allow", "Principal": {"Service": "scheduler.amazonaws.com"}, "Action": "sts:AssumeRole"}]
    }' >/dev/null
  sleep 8
fi
aws iam put-role-policy --role-name "$SCHEDULER_ROLE_NAME" --policy-name invoke-lambda \
  --policy-document "{
    \"Version\": \"2012-10-17\",
    \"Statement\": [{\"Effect\": \"Allow\", \"Action\": \"lambda:InvokeFunction\", \"Resource\": \"$LAMBDA_ARN\"}]
  }" >/dev/null

echo "==> EventBridge Scheduler schedule ($SCHEDULE_EXPR)"
SCHEDULER_ROLE_ARN="arn:aws:iam::${ACCOUNT}:role/${SCHEDULER_ROLE_NAME}"
if aws scheduler get-schedule --name "$SCHEDULE_NAME" --region "$REGION" >/dev/null 2>&1; then
  aws scheduler update-schedule --name "$SCHEDULE_NAME" --region "$REGION" \
    --schedule-expression "$SCHEDULE_EXPR" \
    --flexible-time-window '{"Mode": "OFF"}' \
    --target "{\"Arn\": \"$LAMBDA_ARN\", \"RoleArn\": \"$SCHEDULER_ROLE_ARN\"}" >/dev/null
else
  aws scheduler create-schedule --name "$SCHEDULE_NAME" --region "$REGION" \
    --schedule-expression "$SCHEDULE_EXPR" \
    --flexible-time-window '{"Mode": "OFF"}' \
    --target "{\"Arn\": \"$LAMBDA_ARN\", \"RoleArn\": \"$SCHEDULER_ROLE_ARN\"}" >/dev/null
fi

echo
echo "Done. $SCHEDULE_NAME will invoke $FUNCTION_NAME on schedule '$SCHEDULE_EXPR'."
echo "Test it now:   aws lambda invoke --function-name $FUNCTION_NAME --region $REGION /tmp/out.json && cat /tmp/out.json"
echo "Tear down:     ./destroy.sh"

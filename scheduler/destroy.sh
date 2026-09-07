#!/usr/bin/env bash
# Tears down the nightly scheduler: EventBridge Scheduler schedule, both IAM
# roles, and the Lambda function. Does not touch the AgentCore Runtime
# itself - use ../destroy.sh for that.
set -euo pipefail
REGION="${AWS_REGION:-us-east-1}"

FUNCTION_NAME="billwatch-nightly"
LAMBDA_ROLE_NAME="billwatch-nightly-lambda-role"
SCHEDULER_ROLE_NAME="billwatch-nightly-scheduler-role"
SCHEDULE_NAME="billwatch-nightly"

echo "==> Deleting schedule"
aws scheduler delete-schedule --name "$SCHEDULE_NAME" --region "$REGION" 2>/dev/null || true

echo "==> Deleting Lambda function"
aws lambda delete-function --function-name "$FUNCTION_NAME" --region "$REGION" 2>/dev/null || true

echo "==> Deleting IAM roles"
for role in "$LAMBDA_ROLE_NAME" "$SCHEDULER_ROLE_NAME"; do
  for policy in $(aws iam list-role-policies --role-name "$role" --region "$REGION" --query "PolicyNames[]" --output text 2>/dev/null || true); do
    aws iam delete-role-policy --role-name "$role" --policy-name "$policy" --region "$REGION" 2>/dev/null || true
  done
  for arn in $(aws iam list-attached-role-policies --role-name "$role" --region "$REGION" --query "AttachedPolicies[].PolicyArn" --output text 2>/dev/null || true); do
    aws iam detach-role-policy --role-name "$role" --policy-arn "$arn" --region "$REGION" 2>/dev/null || true
  done
  aws iam delete-role --role-name "$role" --region "$REGION" 2>/dev/null || true
done

echo "Done."

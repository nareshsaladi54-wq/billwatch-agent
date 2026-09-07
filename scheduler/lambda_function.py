"""Nightly trigger for the billwatch AgentCore Runtime.

Invoked by an EventBridge Scheduler cron. The agent is stateless per call -
durable state lives in AgentCore Memory and the seed/data files - so this
Lambda's only job is: call invoke_agent_runtime with tonight's check, and
log the result. Swap the final print() for SES/SNS to actually notify a
human; logging is the honest baseline until that's wired up.
"""
import json
import os
import uuid

import boto3

RUNTIME_ARN = os.environ["AGENT_RUNTIME_ARN"]
PROMPT = os.environ.get("PROMPT", "Do your nightly check and tell me only what I need to act on.")
ACTOR_ID = os.environ.get("ACTOR_ID", "demo")

client = boto3.client("bedrock-agentcore", region_name=os.environ.get("AWS_REGION", "us-east-1"))


def handler(event, context):
    session_id = uuid.uuid4().hex + uuid.uuid4().hex  # runtimeSessionId must be >= 33 chars
    response = client.invoke_agent_runtime(
        agentRuntimeArn=RUNTIME_ARN,
        qualifier=os.environ.get("QUALIFIER", "DEFAULT"),
        runtimeSessionId=session_id,
        payload=json.dumps({"prompt": PROMPT, "actor_id": ACTOR_ID}),
    )
    body = json.loads(response["response"].read())
    print(json.dumps(body))
    return body

import json
import os
import secrets
import time
import uuid

import boto3
from botocore.config import Config

# Initialize the Bedrock AgentCore client
client = boto3.client(
    "bedrock-agentcore",
    region_name=os.environ["AWS_REGION"],
    config=Config(connect_timeout=5, read_timeout=30),
)

# Build an X-Ray trace header that forces sampling (Sampled=1).
def _sampled_trace_id() -> str:
    """Build an X-Ray trace header that forces sampling (Sampled=1)."""
    epoch = format(int(time.time()), "x")
    root = secrets.token_hex(12)
    parent = secrets.token_hex(8)
    return f"Root=1-{epoch}-{root};Parent={parent};Sampled=1"

# Lambda handler -> This is to invoke the AgentCore Runtime.
def lambda_handler(event, context):
    user_input = event.get("message", "What is the capital of Canada?")

    # Reuse the session_id from the request to maintain conversation history.
    # If not provided, generate a new one (starts a fresh conversation thread).
    session_id = event.get("session_id") or str(uuid.uuid4())

    # actor_id identifies the user across sessions for long-term memory.
    # The client should send a stable user identifier (e.g. a user ID or email).
    actor_id = event.get("actor_id", "default-actor")

    payload = json.dumps({
        "message": user_input,
        "session_id": session_id,
        "actor_id": actor_id,
    })

    # Lambda often propagates Sampled=0, which suppresses AgentCore spans.
    # See: https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-troubleshooting.html#troubleshoot-runtime-lambda-missing-spans
    lambda_trace = os.environ.get("_X_AMZN_TRACE_ID", "not set")
    trace_id = _sampled_trace_id()
    print(f"Lambda _X_AMZN_TRACE_ID: {lambda_trace}")
    print(f"AgentCore traceId (Sampled=1): {trace_id}")
    print(f"Invoking AgentCore with payload: {payload} & session_id: {session_id}")

    response = client.invoke_agent_runtime(
        agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:850652371396:runtime/simple_langchain_agent-Qgc53c8gbf",
        runtimeSessionId=session_id,
        payload=payload,
        qualifier="DEFAULT", # This is the endpoint name in the AgentCore Runtime. Go to the AgentCore Runtime console to see the endpoint name.
        traceId=trace_id,
    )
    response_body = response["response"].read()
    print("================================================")
    print(f"response_body: {response_body}")

    response_data = json.loads(response_body)
    print(f"response_data: {response_data}")

    return {
        "statusCode": 200,
        "headers": {
            "Content-type": "application/json",
            "Access-Control-Allow-Origin": "*",
        },
        "body": json.dumps(
            {
                "result": response_data,
                "session_id": session_id,
            }
        ),
    }

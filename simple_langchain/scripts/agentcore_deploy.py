"""
Deploy (or redeploy) the agent to AgentCore Runtime.

First-time deploy:
    uv run python scripts/agentcore_deploy.py --create

Redeploy after pushing a new image:
    uv run python scripts/agentcore_deploy.py

Deployment state (AGENT_RUNTIME_ID, AGENT_RUNTIME_ARN) is stored in
agentcore.cfg at the project root — separate from .env which is the
agent's runtime config (AGENTCORE_MEMORY_ID etc.).
"""

import argparse
import configparser
import os
import sys

import boto3
from dotenv import load_dotenv

# .env provides AGENTCORE_MEMORY_ID for --create
load_dotenv()

PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
CFG_FILE = os.path.join(os.path.dirname(__file__), "agentcore_deploy.cfg")

REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
ACCOUNT_ID = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
ECR_URI = f"{ACCOUNT_ID}.dkr.ecr.{REGION}.amazonaws.com/rw/simple_langchain_agent:latest"

RUNTIME_NAME = "simple_langchain_agent"
ROLE_ARN = os.environ.get(
    "AGENT_RUNTIME_ROLE_ARN",
    f"arn:aws:iam::{ACCOUNT_ID}:role/service-role/AmazonBedrockAgentCoreRuntimeDefaultServiceRole-uhxfs",
)
MEMORY_ID = os.environ.get("AGENTCORE_MEMORY_ID", "")

CP = boto3.client("bedrock-agentcore-control", region_name=REGION)


# ── agentcore.cfg helpers ────────────────────────────────────────────────────

def read_cfg() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    cfg.read(CFG_FILE)
    return cfg


def write_cfg(runtime_id: str, runtime_arn: str) -> None:
    cfg = read_cfg()
    if "runtime" not in cfg:
        cfg["runtime"] = {}
    cfg["runtime"]["agent_runtime_id"] = runtime_id
    cfg["runtime"]["agent_runtime_arn"] = runtime_arn
    with open(CFG_FILE, "w") as f:
        cfg.write(f)
    print(f"Saved deployment state to {CFG_FILE}")


def get_runtime_id_from_cfg() -> str | None:
    cfg = read_cfg()
    return cfg.get("runtime", "agent_runtime_id", fallback=None)


# ── wait helpers ─────────────────────────────────────────────────────────────

def wait_ready(runtime_id: str, label: str = "runtime"):
    import time
    print(f"Waiting for {label} to become READY", end="", flush=True)
    while True:
        r = CP.get_agent_runtime(agentRuntimeId=runtime_id)
        status = r["status"]
        if status == "READY":
            print(" ✓")
            return r
        if "FAILED" in status:
            print(f"\nERROR: {label} entered {status}: {r.get('failureReason')}")
            sys.exit(1)
        print(".", end="", flush=True)
        time.sleep(5)


def wait_endpoint_ready(runtime_id: str, endpoint_name: str = "DEFAULT"):
    import time
    print(f"Waiting for endpoint '{endpoint_name}' to become READY", end="", flush=True)
    while True:
        r = CP.get_agent_runtime_endpoint(agentRuntimeId=runtime_id, endpointName=endpoint_name)
        status = r["status"]
        if status == "READY":
            print(" ✓")
            return r
        if "FAILED" in status:
            print(f"\nERROR: endpoint entered {status}: {r.get('failureReason')}")
            sys.exit(1)
        print(".", end="", flush=True)
        time.sleep(5)


# ── deploy actions ───────────────────────────────────────────────────────────

def create():
    if not MEMORY_ID:
        print("ERROR: AGENTCORE_MEMORY_ID must be set in .env before deploying")
        sys.exit(1)

    print(f"Creating runtime '{RUNTIME_NAME}' with image:\n  {ECR_URI}\n")

    resp = CP.create_agent_runtime(
        agentRuntimeName=RUNTIME_NAME,
        agentRuntimeArtifact={
            "containerConfiguration": {"containerUri": ECR_URI}
        },
        roleArn=ROLE_ARN,
        networkConfiguration={"networkMode": "PUBLIC"},
        environmentVariables={"AGENTCORE_MEMORY_ID": MEMORY_ID},
    )
    runtime_id = resp["agentRuntimeId"]
    runtime_arn = resp["agentRuntimeArn"]
    print(f"Runtime ID : {runtime_id}")
    print(f"Runtime ARN: {runtime_arn}\n")

    wait_ready(runtime_id, "runtime")

    print("Creating DEFAULT endpoint...")
    CP.create_agent_runtime_endpoint(
        agentRuntimeId=runtime_id,
        name="DEFAULT",
    )
    wait_endpoint_ready(runtime_id, "DEFAULT")

    write_cfg(runtime_id, runtime_arn)
    print(f"\nDeploy complete.")
    print(f"Update your Lambda with:\n  AGENT_RUNTIME_ARN = {runtime_arn}")


def redeploy(runtime_id: str):
    if not MEMORY_ID:
        print("ERROR: AGENTCORE_MEMORY_ID must be set in .env before deploying")
        sys.exit(1)

    print(f"Redeploying runtime '{runtime_id}' with image:\n  {ECR_URI}\n")

    # update_agent_runtime requires roleArn + networkConfiguration — read from current config
    current = CP.get_agent_runtime(agentRuntimeId=runtime_id)

    CP.update_agent_runtime(
        agentRuntimeId=runtime_id,
        agentRuntimeArtifact={
            "containerConfiguration": {"containerUri": ECR_URI}
        },
        roleArn=current["roleArn"],
        networkConfiguration=current["networkConfiguration"],
        environmentVariables={"AGENTCORE_MEMORY_ID": MEMORY_ID},
    )
    wait_ready(runtime_id, "runtime")
    print(f"\nRedeploy complete. Runtime '{runtime_id}' is READY with the new image.")


# ── entrypoint ───────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Deploy agent to AgentCore Runtime")
    parser.add_argument("--create", action="store_true", help="First-time creation (creates runtime + endpoint)")
    args = parser.parse_args()

    if args.create:
        create()
    else:
        # Prefer agentcore.cfg, fall back to listing by name
        runtime_id = get_runtime_id_from_cfg()
        if not runtime_id:
            runtimes = CP.list_agent_runtimes().get("agentRuntimes", [])
            matches = [r for r in runtimes if r["agentRuntimeName"] == RUNTIME_NAME]
            if not matches:
                print("No existing runtime found. Run with --create for first-time deploy.")
                sys.exit(1)
            runtime_id = matches[0]["agentRuntimeId"]
            print(f"Found runtime by name: {runtime_id}")
        redeploy(runtime_id)


if __name__ == "__main__":
    main()

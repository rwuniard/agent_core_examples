# Simple LangChain Agent

A minimal example of a conversational AI agent built with LangChain and Amazon Bedrock (Nova Pro), demonstrating how to wrap an LLM in a clean Python class using `create_agent`.

## Purpose

This project shows how to:

- Connect LangChain to Amazon Bedrock using `ChatBedrockConverse`
- Create a reusable agent class without Pydantic overhead
- Invoke the agent with a user message and retrieve the response

## Prerequisites

- Python 3.13+
- [uv](https://docs.astral.sh/uv/) installed
- Docker installed
- AWS credentials configured (`aws configure` or SSO login)
- Amazon Bedrock model access enabled for `amazon.nova-pro-v1` in `us-east-1`

## Setup

Install dependencies:

```bash
uv sync
```

## Running Locally (without Docker)

**Interactive mode** — chat with the agent in a loop; type `exit` to quit:

```bash
uv run main.py
```

**Local AgentCore server** — runs the agent behind the same HTTP interface AgentCore uses in the cloud, without needing `agentcore create`/`configure`:

```bash
uv run agent.py
```

This starts a local server on `http://localhost:8080` with `/invocations` and `/ping` routes (provided by `BedrockAgentCoreApp.run()`). In another terminal, send a test request:

```bash
./scripts/test_local.sh
```

or manually:

```bash
curl -X POST http://localhost:8080/invocations -H "Content-Type: application/json" -d '{"message": "What is the capital of France?"}'
```

## Docker

### Build locally

Builds a multi-platform image (`linux/amd64` and `linux/arm64`) tagged with both `latest` and the current git commit SHA:

```bash
./scripts/build_docker_local.sh
```

### Run locally

Starts the agent server in Docker on `http://localhost:8080`, passing your AWS credentials from the `rwuniard` profile:

```bash
./scripts/run_docker.sh
```

Then test it:

```bash
./scripts/test_local.sh
```

### Build and push to ECR

Builds a `linux/arm64` image and pushes it directly to ECR (does not load into local Docker). Requires ECR repository `rw/simple_langchain_agent` to exist in your account:

```bash
./scripts/build_push_ecr.sh
```

This script:
1. Resolves your AWS account ID via `sts get-caller-identity`
2. Authenticates Docker with ECR
3. Builds and pushes the image tagged `latest` and the current git commit SHA

## AWS Credentials

This project uses your local AWS credentials — no API key is needed. Authentication follows the standard AWS credential chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file (via `aws configure`)
3. IAM role (if running on EC2/ECS/Lambda)

Verify your credentials are configured:

```bash
aws sts get-caller-identity
```

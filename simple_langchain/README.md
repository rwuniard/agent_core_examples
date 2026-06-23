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
- AWS credentials configured (`aws configure` or SSO login)
- Amazon Bedrock model access enabled for `amazon.nova-pro-v1` in `us-east-1`

## Setup

Install dependencies:

```bash
uv sync
```

## Running

**Single query** — runs the agent with a hardcoded question and prints the response:

```bash
uv run agent.py
```

**Interactive mode** — chat with the agent in a loop; type `exit` to quit:

```bash
uv run main.py
```

## AWS Credentials

This project uses your local AWS credentials — no API key is needed. Authentication follows the standard AWS credential chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file (via `aws configure`)
3. IAM role (if running on EC2/ECS/Lambda)

Verify your credentials are configured:

```bash
aws sts get-caller-identity
```

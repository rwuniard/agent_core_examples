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

### Multi-stage build

The Dockerfile uses a **multi-stage build** to keep the final production image as small as possible:

- **`builder` stage** — installs `uv` and resolves all Python dependencies into a `.venv`. This stage is only used during the build and is discarded afterwards. It is never shipped.
- **Runtime stage** — starts from a clean `python:3.13-slim` base and copies only the pre-built `.venv` and `agent.py` from the builder. No build tools (`uv`, `pip` cache, etc.) are included.

This removes ~80-100MB of build-time tooling from the final image.

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

## Observability (OpenTelemetry + X-Ray)

The Docker image uses [AWS Distro for OpenTelemetry (ADOT)](https://aws-otel.github.io/) for zero-code-change auto-instrumentation. The `opentelemetry-instrument` launcher automatically traces LangChain chains and Bedrock API calls at startup — no changes to `agent.py` needed.

See the [AWS CloudWatch AgentCore observability docs](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AgentCore-GettingStarted.html) for full details.

### How it works

The Dockerfile starts the agent with:
```
opentelemetry-instrument python agent.py
```

ADOT auto-detects installed libraries (LangChain, botocore) and instruments them automatically.

### AgentCore Runtime

When deployed to AgentCore Runtime, **no additional OTEL configuration is required**. The runtime automatically injects all necessary environment variables at deploy time, including:

| Variable | Description |
|---|---|
| `OTEL_PYTHON_DISTRO` / `OTEL_PYTHON_CONFIGURATOR` | ADOT SDK wiring |
| `OTEL_RESOURCE_ATTRIBUTES` | Service name, log group, and endpoint ARN |
| `OTEL_EXPORTER_OTLP_LOGS_HEADERS` | CloudWatch log group and stream routing |
| `OTEL_EXPORTER_OTLP_PROTOCOL` / `OTEL_TRACES_EXPORTER` | Export format |

These are set dynamically by AgentCore and should **not** be hardcoded in the Dockerfile — some contain runtime-specific values (agent ID, endpoint ARN) that only exist after deployment.

Before deploying, enable CloudWatch Transaction Search in the [CloudWatch console](https://console.aws.amazon.com/cloudwatch) under **Application Signals (APM) → Transaction search**.

### Local Docker

Telemetry is **disabled** by default when running locally (`OTEL_SDK_DISABLED=true` in `run_docker.sh`) since there is no collector listening. The agent runs normally without any tracing errors.

To test the full telemetry pipeline locally, run an ADOT collector alongside the agent:

```bash
docker run --rm -p 4317:4317 \
  -v ~/.aws:/root/.aws:ro \
  public.ecr.aws/aws-observability/aws-otel-collector:latest
```

Then in `scripts/run_docker.sh`, replace `-e OTEL_SDK_DISABLED=true` with:

```
-e OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://localhost:4317
```

### Plain ECS / Fargate (non-AgentCore)

If running outside AgentCore on plain ECS, add an ADOT sidecar to your task definition and configure the OTEL env vars manually — see [AWS docs](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/observability-configure.html#observability-configure-3p).

### Environment variables set in Dockerfile

Only static values are set in the Dockerfile. All runtime-specific OTEL variables are injected automatically by AgentCore.

| Variable | Value | Description |
|---|---|---|
| `OTEL_SERVICE_NAME` | `simple-langchain-agent` | Service name shown in traces |

`OTEL_PROPAGATORS` is intentionally not set in the Dockerfile — AgentCore injects it automatically at deploy time. Setting it in the image would cause a startup error if the corresponding propagator package entry point isn't resolvable in that environment.

## AWS Credentials

This project uses your local AWS credentials — no API key is needed. Authentication follows the standard AWS credential chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file (via `aws configure`)
3. IAM role (if running on EC2/ECS/Lambda)

Verify your credentials are configured:

```bash
aws sts get-caller-identity
```

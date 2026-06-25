# Simple LangChain Agent

A minimal example of a conversational AI agent built with LangChain and Amazon Bedrock (Nova Pro), demonstrating how to wrap an LLM in a clean Python class using `create_agent`.

## Purpose

This project shows how to:

- Connect LangChain to Amazon Bedrock using `ChatBedrockConverse`
- Create a reusable agent class without Pydantic overhead
- Invoke the agent with a user message and retrieve the response

## Architecture

```
User (Postman / curl)
        │
        │  POST { "message": "..." }
        ▼
  API Gateway (REST API)
        │
        │  invokes
        ▼
  Lambda Function (boto3)
        │
        │  invoke_agent_runtime()
        ▼
  AgentCore Runtime
        │
        │  LangChain + ChatBedrockConverse
        ▼
  Amazon Bedrock (Nova Pro)
```

- **API Gateway** exposes a public HTTPS endpoint and forwards POST requests to Lambda
- **Lambda** receives the request and calls the AgentCore runtime using `boto3`. It requires an IAM role with permission to invoke the AgentCore agent
- **AgentCore Runtime** runs the containerized agent (this image), processes the message through LangChain and Bedrock, and returns the response
- **AgentCore Memory** stores conversation history per `actor_id` / `session_id` combination, persisting state across container restarts and sessions

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

## Deploying to AgentCore Runtime

### Redeploy after a code change

After pushing a new image to ECR, update the running runtime:

```bash
# 1. Push the new image
./scripts/build_push_ecr.sh

# 2. Roll out the new image to AgentCore Runtime
uv run python scripts/deploy.py
```

The script reads the runtime ID from `scripts/agentcore_deploy.cfg` and falls back to looking up the runtime by name. The DEFAULT endpoint ARN stays the same across redeploys — no Lambda reconfiguration needed.

### First-time deploy (without the agentcore CLI)

If you need to create the runtime from scratch without using the `agentcore` CLI, run:

```bash
uv run python scripts/deploy.py --create
```

Requires `AGENTCORE_MEMORY_ID` to be set in `.env` and the ECR image to already be pushed. Saves the new runtime ID and ARN to `scripts/agentcore_deploy.cfg`.

### What deploy does under the hood

```
build_push_ecr.sh              deploy.py (redeploy)
       │                               │
       ▼                               ▼
ECR image :latest      update_agent_runtime(containerUri=ECR:latest)
                                       │
                                       ▼
                           AgentCore pulls new image
                           spins up new container
                           waits for READY (~1-2 min)
                                       │
                                       ▼
                           DEFAULT endpoint stays live
                           (zero-downtime swap)
```

### Checking runtime status

```bash
aws bedrock-agentcore-control get-agent-runtime \
  --agent-runtime-id <AGENT_RUNTIME_ID> \
  --region us-east-1
```

### Configuration files

| File | Purpose |
|---|---|
| `.env` | Agent runtime config — `AGENTCORE_MEMORY_ID` (loaded by `agent.py`) |
| `scripts/agentcore_deploy.cfg` | Deployment state — written by `--create`, read by redeploy |

**`.env` keys used by deploy:**

| Variable | Description |
|---|---|
| `AGENTCORE_MEMORY_ID` | Required for `--create` — passed to the runtime as an env var |
| `AGENT_RUNTIME_ROLE_ARN` | Optional — IAM role for the runtime (defaults to the service default role) |

**`agentcore_deploy.cfg` keys (written automatically):**

| Key | Description |
|---|---|
| `agent_runtime_id` | Runtime ID — used by redeploy to target the right runtime |
| `agent_runtime_arn` | Runtime ARN — needed in Lambda for `invoke_agent_runtime` |

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

## Memory

The agent uses `AgentCoreMemorySaver` from `langgraph-checkpoint-aws` as its LangGraph checkpointer. This persists full conversation state (messages, graph execution state) to AgentCore Memory — surviving container restarts and cold starts.

### How conversation identity works

Every request carries two identifiers:

| Field | Meaning | Example |
|---|---|---|
| `actor_id` | Who is talking — a stable user identifier | `user-ron-456` |
| `session_id` | Which conversation — reuse to continue, new UUID to start fresh | `session-abc-123` |

The same `actor_id` + same `session_id` = resumes the existing conversation thread.
The same `actor_id` + new `session_id` = new conversation, but long-term memory (preferences, facts) is shared across sessions.

### Request body

All three fields can be sent from the client:

```json
{
  "message": "What did I tell you my name was?",
  "session_id": "session-abc-123",
  "actor_id": "user-ron-456"
}
```

- **`session_id`** — if omitted, Lambda generates a new UUID (fresh conversation)
- **`actor_id`** — if omitted, defaults to `"default-actor"`

### Required setup

1. Create an **AgentCore Memory** resource in the AWS console
2. Set the `AGENTCORE_MEMORY_ID` environment variable in both the AgentCore Runtime and Lambda configurations
3. Add the following minimum IAM policy statement to the AgentCore Runtime role (e.g. `AmazonBedrockAgentCoreRuntimeExecutionPolicy_*`):

```json
{
  "Sid": "AgentCoreMemoryAccess",
  "Effect": "Allow",
  "Action": [
    "bedrock-agentcore:CreateEvent",
    "bedrock-agentcore:ListEvents",
    "bedrock-agentcore:DeleteEvent"
  ],
  "Resource": "arn:aws:bedrock-agentcore:<region>:<account-id>:memory/<memory-id>"
}
```

`DeleteEvent` is only exercised if you call `delete_thread()` to clear a session. If you later add long-term memory strategies, also add `bedrock-agentcore:RetrieveMemories` to the same statement.

> **Avoid `BedrockAgentCoreFullAccess`** — it grants `bedrock-agentcore:*` on all resources in your account, which is far broader than needed.

## Lambda Function

The `lambda_function/lambda_function.py` file contains the Lambda handler that sits between API Gateway and AgentCore Runtime.

**What it does:**

- Reads `message`, `session_id`, and `actor_id` from the API Gateway event
- Reuses `session_id` if provided, or generates a new UUID for a fresh conversation
- Constructs a forced-sampling X-Ray trace ID (`Sampled=1`) — this is necessary because Lambda propagates `Sampled=0` by default, which suppresses AgentCore spans in CloudWatch
- Calls `boto3` `invoke_agent_runtime()` with the AgentCore runtime ARN, session ID, and payload
- Returns the agent response with CORS headers

**Key configuration in `lambda_function.py`:**

- `agentRuntimeArn` — update this to your AgentCore runtime ARN after deployment
- `qualifier` — the endpoint name in AgentCore Runtime (defaults to `DEFAULT`); find it in the AgentCore Runtime console

**Required environment variables (set in Lambda console):**

| Variable | Description |
|---|---|
| `AWS_REGION` | Region where AgentCore is deployed (e.g. `us-east-1`) |
| `AGENTCORE_MEMORY_ID` | ID of the AgentCore Memory resource |

## API Gateway Setup

### Lambda IAM Role

Before creating the Lambda function, ensure its execution role has permission to invoke the AgentCore agent:

```json
{
  "Effect": "Allow",
  "Action": "bedrock-agentcore:InvokeAgentRuntime",
  "Resource": "arn:aws:bedrock-agentcore:<region>:<account-id>:runtime/<agent-id>"
}
```

### Create the API

1. Go to **API Gateway** in the AWS Console
2. Click **Create API** → select **REST API** → **New API**
3. Enter an API name and click **Create API**

### Create a resource and method

4. Click **Create resource** → enter a resource name (e.g. `/chat`) → enable CORS if needed → click **Create resource**
5. With the resource selected, click **Create method**
   - Method type: **POST**
   - Integration type: **Lambda function**
   - Select your Lambda function
   - Click **Create method**

### Deploy

6. Click **Deploy API** → select **\*New Stage\*** → enter a stage name (e.g. `prod`) → click **Deploy**
7. Navigate to the **POST** method → copy the **Invoke URL**

### Test

Use the Invoke URL in Postman or curl:

```bash
curl -X POST <invoke-url> \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of Canada?", "session_id": "session-abc-123", "actor_id": "user-ron-456"}'
```

Or in Postman: create a **POST** request to the Invoke URL with the JSON body above. Save `session_id` as a Postman variable and reuse it across requests to maintain the same conversation thread.

## AWS Credentials

This project uses your local AWS credentials — no API key is needed. Authentication follows the standard AWS credential chain:

1. Environment variables (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
2. `~/.aws/credentials` file (via `aws configure`)
3. IAM role (if running on EC2/ECS/Lambda)

Verify your credentials are configured:

```bash
aws sts get-caller-identity
```

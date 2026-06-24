FROM python:3.13-slim AS builder

WORKDIR /app

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./

# Install dependencies into .venv, no cache
RUN uv sync --no-dev --no-cache


FROM python:3.13-slim

WORKDIR /app

# Copy only the built venv and agent from the builder stage
COPY --from=builder /app/.venv /app/.venv
COPY agent.py ./

RUN useradd --create-home appuser
USER appuser

# OpenTelemetry configuration
# AgentCore Runtime automatically injects the OTLP collector endpoint and OTEL env vars.
# When running outside AgentCore (e.g. plain ECS), set OTEL_EXPORTER_OTLP_TRACES_ENDPOINT
# to point to your ADOT collector (e.g. http://localhost:4317 for a sidecar).
ENV OTEL_SERVICE_NAME=simple-langchain-agent

# Add venv to PATH so opentelemetry-instrument and python are found directly
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8080

CMD ["opentelemetry-instrument", "python", "agent.py"]

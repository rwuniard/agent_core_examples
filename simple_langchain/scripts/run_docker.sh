docker run -p 8080:8080 \
  -e AWS_ACCESS_KEY_ID=$(aws configure get aws_access_key_id --profile rwuniard) \
  -e AWS_SECRET_ACCESS_KEY=$(aws configure get aws_secret_access_key --profile rwuniard) \
  -e AWS_SESSION_TOKEN=$(aws configure get aws_session_token --profile rwuniard) \
  -e AWS_DEFAULT_REGION=us-east-1 \
  -e OTEL_SDK_DISABLED=true \
  simple-langchain-agent:latest

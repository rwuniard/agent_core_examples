docker buildx build --platform linux/amd64,linux/arm64 \
-t simple-langchain-agent:$(git rev-parse --short HEAD) \
-t simple-langchain-agent:latest \
--load ..

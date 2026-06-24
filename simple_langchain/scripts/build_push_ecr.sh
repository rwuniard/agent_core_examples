export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_URI=$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/rw/simple_langchain_agent
echo "ECR_URI: $ECR_URI"
# login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
echo "Logged in to ECR"
# build the image and push it to ECR. It doesn't load to the local docker desktop.
echo "Building the image"
docker buildx build --platform linux/arm64 \
  -t $ECR_URI:latest \
  -t $ECR_URI:$(git rev-parse --short HEAD) \
  --push ..
echo "Pushed the Simple Langchain Agent image to ECR"

#!/bin/bash
set -e

PROJECT_ID="enterprise-rag-2026"
REGION="us-central1"
REPO_NAME="rag-platform-repo"
IMAGE_NAME="rag-api"
IMAGE_TAG="latest"
FULL_IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPO_NAME}/${IMAGE_NAME}:${IMAGE_TAG}"
CLOUD_RUN_SERVICE="rag-platform-service"

# 1. Provision Infrastructure
echo -e "\n=== 1. Provisioning Infrastructure (Terraform) ==="
# Dynamically navigate to the terraform directory relative to this script
cd "$(dirname "$0")/../terraform"
terraform apply -auto-approve

# 2. Build and Push Docker Image
echo -e "\n=== 2. Building & Pushing Docker Image ==="
# Navigate to the repository root
cd ../..
# Authenticate local Docker to Google Artifact Registry
gcloud auth configure-docker ${REGION}-docker.pkg.dev --quiet
docker build -t $FULL_IMAGE_URL -f Dockerfile .
docker push $FULL_IMAGE_URL

# 3. Deploy Application Code
echo -e "\n=== 3. Deploying Code to Cloud Run ==="
gcloud run deploy $CLOUD_RUN_SERVICE \
  --image $FULL_IMAGE_URL \
  --region $REGION \
  --project $PROJECT_ID \
  --quiet

echo -e "\n[SUCCESS] Enterprise Stack deployed successfully!"
# Fetch and print the live URL
gcloud run services describe $CLOUD_RUN_SERVICE --platform managed --region $REGION --format 'value(status.url)'
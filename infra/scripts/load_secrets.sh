#!/bin/bash
# Fails the script immediately if any command errors out
set -e 

PROJECT_ID="enterprise-rag-2026"

echo -e "\n=== Secret Manager Uploader ==="
echo "Reading keys from .env file..."

# Dynamically resolve the path to the .env file at the project root
# (dirname "$0" is infra/scripts -> ../.. goes up to the project root)
ENV_PATH="$(dirname "$0")/../../.env"

if [ ! -f "$ENV_PATH" ]; then
    echo "Error: .env file not found at $ENV_PATH"
    exit 1
fi

# Automatically export variables from your local .env file
set -a
source "$ENV_PATH"
set +a

# Validate that the keys actually exist in the .env file
if [ -z "$API_KEY" ] || [ -z "$LLM_API_KEY" ]; then
    echo "Error: API_KEY or LLM_API_KEY is missing from your .env file."
    exit 1
fi

echo "Pushing API_KEY to RAG_API_KEY in Secret Manager..."
echo -n "$API_KEY" | gcloud secrets versions add RAG_API_KEY --data-file=- --project=$PROJECT_ID

echo "Pushing LLM_API_KEY to LLM_API_KEY in Secret Manager..."
echo -n "$LLM_API_KEY" | gcloud secrets versions add LLM_API_KEY --data-file=- --project=$PROJECT_ID

echo -e "\n[SUCCESS] Secrets successfully pushed to Google Cloud."
#!/bin/bash
# Fails the script immediately if any command errors out
set -e 

PROJECT_ID="enterprise-rag-2026"
SECRET_NAME="RAG_API_KEY"

echo -e "\n=== Secret Manager Uploader ==="
echo "Enter the API Key you want to secure for the RAG API:"
# -s hides the input from the terminal screen
read -s API_KEY

if [ -z "$API_KEY" ]; then
    echo "Error: API Key cannot be empty."
    exit 1
fi

# Pipes the key directly into GCP Secret Manager
echo -n "$API_KEY" | gcloud secrets versions add $SECRET_NAME --data-file=- --project=$PROJECT_ID

echo -e "\n[SUCCESS] Secret $SECRET_NAME successfully pushed to Google Cloud."
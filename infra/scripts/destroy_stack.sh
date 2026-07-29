#!/bin/bash
# Temporarily disable 'set -e' so the script doesn't instantly exit on the first Terraform error
set +e 

echo -e "\n=== TEARING DOWN RAG PLATFORM ==="
echo "Destroying all GCP resources to protect your developer credits..."

cd "$(dirname "$0")/../terraform"

# Try to destroy. If it succeeds, great. If it fails, run the fallback block.
if terraform destroy -auto-approve; then
    echo -e "\n[SUCCESS] Infrastructure destroyed. Active billing halted."
else
    echo -e "\n⚠️ GCP eventual consistency lock detected."
    echo "⏳ Waiting 60 seconds for Google to release VPC IPs..."
    sleep 60
    echo "🔄 Retrying teardown..."
    
    # Re-enable strict error handling for the final attempt
    set -e 
    terraform destroy -auto-approve
    echo -e "\n[SUCCESS] Infrastructure destroyed. Active billing halted."
fi
## Create State Bucket
gcloud storage buckets create gs://enterprise-rag-2026-tf-state --location=us-central1
gcloud storage buckets update gs://enterprise-rag-2026-tf-state --versioning

## Enable IAM Credentials API
gcloud services enable iamcredentials.googleapis.com

## Create Workload Identity Pool
gcloud iam workload-identity-pools create github-actions-pool \
  --project="enterprise-rag-2026" \
  --location="global" \
  --display-name="GitHub Actions Pool"

## Create OIDC Provider
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --project="enterprise-rag-2026" \
  --location="global" \
  --workload-identity-pool="github-actions-pool" \
  --display-name="GitHub Actions Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --attribute-condition="assertion.repository == '<YOUR_GITHUB_USERNAME>/enterprise-document-intelligence-rag'" \
  --issuer-uri="https://token.actions.githubusercontent.com"

## Create Terraform Service Account
gcloud iam service-accounts create tf-runner \
  --project="enterprise-rag-2026" \
  --display-name="Terraform CI/CD Runner"

## Grant Terraform Necessary Permissions
# Manage APIs and Quotas
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/serviceusage.serviceUsageAdmin"

# Manage Cloud SQL
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/cloudsql.admin"

# Manage Secret Manager
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/secretmanager.admin"

# Manage Cloud Run and VPC Connectors
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/compute.admin"

# Manage IAM (Terraform needs this to assign runtime roles to Cloud Run)
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectIamAdmin"

# Manage the Terraform State Bucket
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

## Establish Trust Binding
gcloud projects describe enterprise-rag-2026 --format="value(projectNumber)"
# Copy GCP Project Number From Above Command Into:
gcloud iam service-accounts add-iam-policy-binding tf-runner@enterprise-rag-2026.iam.gserviceaccount.com \
  --project="enterprise-rag-2026" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<YOUR_PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/<YOUR_GITHUB_USERNAME>/enterprise-document-intelligence-rag"

## Break the Terraform Dependency Loop
# Provisions APIs and the empty Secret Manager vault first so the secrets loader can run
cd "$(dirname "$0")/../terraform"
terraform apply -target="google_project_service.enabled_apis" -target="google_secret_manager_secret.api_key_secret" -auto-approve
cd ../..


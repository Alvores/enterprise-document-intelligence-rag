## Create State Bucket
gcloud storage buckets create gs://enterprise-rag-2026-tf-state --location=us-central1
gcloud storage buckets update gs://enterprise-rag-2026-tf-state --versioning

## Create Artifact Registry
gcloud artifacts repositories create rag-platform-repo \
  --project="enterprise-rag-2026" \
  --repository-format=docker \
  --location=us-central1 \
  --description="Secure private container registry"

## Enable IAM Credentials API
gcloud services enable iamcredentials.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
gcloud services enable cloudbilling.googleapis.com
gcloud services enable billingbudgets.googleapis.com

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

## Create Docker Publisher Service Account
gcloud iam service-accounts create docker-publisher \
  --project="enterprise-rag-2026" \
  --display-name="Docker CI/CD Publisher"

# Grant ONLY Artifact Registry Writer
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:docker-publisher@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Bind to the Workload Identity Pool
gcloud iam service-accounts add-iam-policy-binding docker-publisher@enterprise-rag-2026.iam.gserviceaccount.com \
  --project="enterprise-rag-2026" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<YOUR_PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/<YOUR_GITHUB_USERNAME>/enterprise-document-intelligence-rag"

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

# Manage Cloud Run Services explicitly
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/run.admin"

# Manage Service Accounts (reading/modifying runtime identities)
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountAdmin"

# Manage Security Policies & IAM Bindings (attaching accessor roles to Secret Manager)
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/iam.securityAdmin"

# Manage Project IAM Policies
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/resourcemanager.projectIamAdmin"

# Manage the Terraform State Bucket
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

# Manage VPC Peering for Cloud SQL
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/servicenetworking.networksAdmin"

# Manage Artifact Registry Pushes
gcloud projects add-iam-policy-binding enterprise-rag-2026 \
  --member="serviceAccount:tf-runner@enterprise-rag-2026.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

## Establish Trust Binding
gcloud projects describe enterprise-rag-2026 --format="value(projectNumber)"
# Copy GCP Project Number From Above Command Into:
gcloud iam service-accounts add-iam-policy-binding tf-runner@enterprise-rag-2026.iam.gserviceaccount.com \
  --project="enterprise-rag-2026" \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/<YOUR_PROJECT_NUMBER>/locations/global/workloadIdentityPools/github-actions-pool/attribute.repository/<YOUR_GITHUB_USERNAME>/enterprise-document-intelligence-rag"

## Create a $5/month safety budget
gcloud beta billing budgets create \
  --billing-account="<YOUR_BILLING_ACCOUNT_ID>" \
  --display-name="RAG Project Budget" \
  --budget-amount=8.00USD \
  --threshold-rule=percent=0.5 \
  --threshold-rule=percent=0.9 \
  --threshold-rule=percent=1.0

## Create Permanent Secret Vaults
gcloud secrets create RAG_API_KEY --replication-policy="automatic" --project="enterprise-rag-2026" || true
gcloud secrets create LLM_API_KEY --replication-policy="automatic" --project="enterprise-rag-2026" || true
# Enable essential GCP APIs required for the Enterprise RAG Platform
resource "google_project_service" "enabled_apis" {
  for_each = toset([
    "run.googleapis.com",               # Cloud Run
    "sqladmin.googleapis.com",          # Cloud SQL
    "secretmanager.googleapis.com",     # Secret Manager
    "artifactregistry.googleapis.com",  # Artifact Registry
    "vpcaccess.googleapis.com",         # Serverless VPC Access
    "servicenetworking.googleapis.com", # Private Service Connect (for Cloud SQL)
    "iam.googleapis.com"                # Identity & Access Management
  ])

  project = var.project_id
  service = each.key

  # Prevents Terraform from accidentally disabling APIs and breaking the project on destroy
  disable_on_destroy = false
}
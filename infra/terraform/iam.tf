# The dedicated identity for the Cloud Run application
resource "google_service_account" "rag_api_sa" {
  account_id   = "rag-api-runtime"
  display_name = "RAG API Runtime Service Account"
  project      = var.project_id
}

# Grant read access to the dynamically generated database URL
resource "google_secret_manager_secret_iam_member" "db_secret_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.db_url_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_api_sa.email}"
}

# Grant read access to the master API key
resource "google_secret_manager_secret_iam_member" "api_key_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.api_key_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_api_sa.email}"
}

# Allow the container to securely connect to Cloud SQL
resource "google_project_iam_member" "cloudsql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.rag_api_sa.email}"
}

# Grant read access to the LLM Key
resource "google_secret_manager_secret_iam_member" "llm_key_access" {
  project   = var.project_id
  secret_id = google_secret_manager_secret.llm_api_key_secret.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_api_sa.email}"
}
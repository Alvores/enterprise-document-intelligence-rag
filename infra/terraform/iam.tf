# Project metadata used to construct the Google-managed Pub/Sub service agent email
data "google_project" "current" {
  project_id = var.project_id
}

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
  secret_id = "RAG_API_KEY"
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
  secret_id = "LLM_API_KEY"
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.rag_api_sa.email}"
}

# Grant the Cloud Run runtime least-privilege access to the staging bucket
resource "google_storage_bucket_iam_member" "rag_api_staging_access" {
  bucket = google_storage_bucket.staging_bucket.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.rag_api_sa.email}"
}

# Grant the Cloud Run runtime permission to publish ingestion events
resource "google_pubsub_topic_iam_member" "rag_api_publisher" {
  project = var.project_id
  topic   = google_pubsub_topic.ingestion_events.name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.rag_api_sa.email}"
}

# Google-managed Pub/Sub service agent: allows minting OIDC tokens for the push subscription
resource "google_service_account_iam_member" "pubsub_oidc_token_creator" {
  service_account_id = google_service_account.rag_api_sa.name
  role               = "roles/iam.serviceAccountTokenCreator"
  member             = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on         = [google_project_service.enabled_apis]
}

# Google-managed Pub/Sub service agent: allows publishing poison-pill messages to the DLQ
resource "google_pubsub_topic_iam_member" "pubsub_dlq_publisher" {
  project    = var.project_id
  topic      = google_pubsub_topic.ingestion_dlq.name
  role       = "roles/pubsub.publisher"
  member     = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on = [google_project_service.enabled_apis]
}

# Google-managed Pub/Sub service agent: allows redelivering DLQ'd messages on the worker sub
resource "google_pubsub_subscription_iam_member" "pubsub_worker_dlq_subscriber" {
  project      = var.project_id
  subscription = google_pubsub_subscription.ingestion_worker_sub.name
  role         = "roles/pubsub.subscriber"
  member       = "serviceAccount:service-${data.google_project.current.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
  depends_on   = [google_project_service.enabled_apis]
}
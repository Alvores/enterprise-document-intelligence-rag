# 1. GCS Staging Bucket for Raw Uploaded PDFs
resource "google_storage_bucket" "staging_bucket" {
  name                        = "${var.project_id}-staging-docs"
  location                    = var.region
  project                     = var.project_id
  storage_class               = "STANDARD"
  uniform_bucket_level_access = true
  force_destroy               = true

  lifecycle_rule {
    condition {
      age = 7
    }
    action {
      type = "Delete"
    }
  }

  depends_on = [google_project_service.enabled_apis]
}

# 2. Primary Pub/Sub Topic for Document Ingestion Events
resource "google_pubsub_topic" "ingestion_events" {
  name                       = "${local.resource_prefix}-ingestion-events"
  project                    = var.project_id
  message_retention_duration = "600s"

  depends_on = [google_project_service.enabled_apis]
}

# 3. Dead-Letter Queue (DLQ) Topic & Pull Subscription for Poison-Pill Messages
resource "google_pubsub_topic" "ingestion_dlq" {
  name    = "${local.resource_prefix}-ingestion-dlq"
  project = var.project_id

  depends_on = [google_project_service.enabled_apis]
}

resource "google_pubsub_subscription" "ingestion_dlq_sub" {
  name                       = "${local.resource_prefix}-ingestion-dlq-sub"
  topic                      = google_pubsub_topic.ingestion_dlq.id
  project                    = var.project_id
  message_retention_duration = "604800s" # 7 days (matches GCS staging lifecycle)
}

# 4. Worker Push Subscription Delivering Events to Cloud Run
resource "google_pubsub_subscription" "ingestion_worker_sub" {
  name                       = "${local.resource_prefix}-ingestion-worker-sub"
  topic                      = google_pubsub_topic.ingestion_events.id
  project                    = var.project_id
  ack_deadline_seconds       = 180
  message_retention_duration = "600s"

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.rag_api_service.uri}/documents/worker"

    oidc_token {
      service_account_email = google_service_account.rag_api_sa.email
      audience              = local.worker_oidc_audience
    }
  }

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "600s"
  }

  dead_letter_policy {
    dead_letter_topic     = google_pubsub_topic.ingestion_dlq.id
    max_delivery_attempts = 5
  }

  depends_on = [
    google_service_account_iam_member.pubsub_oidc_token_creator,
    google_pubsub_topic_iam_member.pubsub_dlq_publisher
  ]
}
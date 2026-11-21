resource "google_cloud_run_v2_service" "rag_api_service" {
  name     = "${local.resource_prefix}-service"
  location = var.region
  project  = var.project_id

  # Ensure APIs and network bridges are ready before deployment
  depends_on = [
    google_project_service.enabled_apis,
    google_service_networking_connection.private_vpc_connection,
    google_secret_manager_secret_version.db_url_version,
    google_secret_manager_secret_iam_member.db_secret_access,
    google_secret_manager_secret_iam_member.api_key_access,
    google_storage_bucket_iam_member.rag_api_staging_access,
    google_pubsub_topic_iam_member.rag_api_publisher
  ]
  template {
    service_account = google_service_account.rag_api_sa.email

    containers {
      # Uses a standard Google placeholder image for the initial Terraform build.
      # CI/CD pipeline (or deploy.sh script) will overwrite later.
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        startup_cpu_boost = true

        limits = {
          cpu    = "2"
          memory = "4096Mi"
        }
      }

      # Mounts the database connection string from Secret Manager
      env {
        name = "DATABASE_URL"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.db_url_secret.secret_id
            version = "latest"
          }
        }
      }

      # Mounts the API key from Secret Manager
      env {
        name = "API_KEY"
        value_source {
          secret_key_ref {
            secret  = "RAG_API_KEY"
            version = "latest"
          }
        }
      }

      # Point directly to the baked local directory path
      env {
        name  = "EMBEDDING_MODEL"
        value = "/app/models/bge-small-en-v1.5"
      }

      env {
        name  = "RERANKER_MODEL"
        value = "/app/models/bge-reranker-base"
      }

      env {
        name  = "EMBEDDING_TOKENIZER_ID"
        value = "/app/models/bge-small-en-v1.5"
      }

      env {
        name  = "LLM_TOKENIZER_ID"
        value = "/app/models/qwen3-8b-tokenizer"
      }

      env {
        name  = "HF_HUB_OFFLINE"
        value = "1"
      }

      env {
        name  = "TRANSFORMERS_OFFLINE"
        value = "1"
      }

      env {
        name  = "ENABLE_TELEMETRY"
        value = "false"
      }

      # LLM to use for RAG retrieval
      env {
        name  = "LLM_MODEL"
        value = "gemini-3.5-flash-lite"
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "LLM_API_KEY"
            version = "latest"
          }
        }
      }

      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }

      env {
        name  = "GCS_BUCKET_NAME"
        value = google_storage_bucket.staging_bucket.name
      }

      env {
        name  = "PUBSUB_TOPIC_ID"
        value = google_pubsub_topic.ingestion_events.name
      }

      env {
        name  = "STORAGE_BACKEND"
        value = "gcp"
      }

      env {
        name  = "WORKER_OIDC_AUDIENCE"
        value = local.worker_oidc_audience
      }

    }

    # Direct VPC Egress: Routes outbound traffic securely into your private network
    vpc_access {
      network_interfaces {
        network    = google_compute_network.vpc_network.id
        subnetwork = google_compute_subnetwork.serverless_subnet.id
      }
      egress = "PRIVATE_RANGES_ONLY"
    }
  }

  # Tells Terraform not to revert the Docker image back to the placeholder if you run apply later
  lifecycle {
    ignore_changes = [
      template[0].containers[0].image
    ]
  }
}

# Allow public unauthenticated access to the Cloud Run URL 
# (Security is handled explicitly by the FastAPI API_KEY header validation)
resource "google_cloud_run_v2_service_iam_member" "public_access" {
  project  = google_cloud_run_v2_service.rag_api_service.project
  location = google_cloud_run_v2_service.rag_api_service.location
  name     = google_cloud_run_v2_service.rag_api_service.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
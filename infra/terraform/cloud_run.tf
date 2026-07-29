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
    google_secret_manager_secret_iam_member.api_key_access
  ]

  template {
    service_account = google_service_account.rag_api_sa.email

    containers {
      # Uses a standard Google placeholder image for the initial Terraform build.
      # CI/CD pipeline (or deploy.sh script) will overwrite later.
      image = "us-docker.pkg.dev/cloudrun/container/hello"

      resources {
        limits = {
          cpu    = "2"
          memory = "2048Mi"
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
            secret  = google_secret_manager_secret.api_key_secret.secret_id
            version = "latest"
          }
        }
      }

      # Add the embedding model directly as a plaintext environment variable
      env {
        name  = "EMBEDDING_MODEL"
        value = "BAAI/bge-small-en-v1.5"
      }

      # LLM to use for RAG retrieval
      env {
        name  = "LLM_MODEL"
        value = "gemini-3.6-flash"
      }

      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.llm_api_key_secret.secret_id
            version = "latest"
          }
        }
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
# Container for the dynamic Postgres connection string
resource "google_secret_manager_secret" "db_url_secret" {
  secret_id = "DATABASE_URL"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled_apis]
}

# Automatically injects the calculated private connection string into the secret
resource "google_secret_manager_secret_version" "db_url_version" {
  secret = google_secret_manager_secret.db_url_secret.id

  # Constructs standard connection string utilizing the generated random password
  secret_data = "postgresql://${google_sql_user.db_user.name}:${random_password.db_password.result}@${google_sql_database_instance.postgres_instance.private_ip_address}/${google_sql_database.rag_db.name}"
}

# Container for your system's master API security key
resource "google_secret_manager_secret" "api_key_secret" {
  secret_id = "RAG_API_KEY"
  project   = var.project_id

  replication {
    auto {}
  }

  depends_on = [google_project_service.enabled_apis]
}

# Secret container for the external LLM API key
resource "google_secret_manager_secret" "llm_api_key_secret" {
  secret_id = "LLM_API_KEY"
  project   = var.project_id

  replication {
    auto {}
  }
}
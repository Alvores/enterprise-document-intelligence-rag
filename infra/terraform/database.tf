# 1. The Cloud SQL PostgreSQL Instance
resource "google_sql_database_instance" "postgres_instance" {
  name             = "rag-postgres-db"
  database_version = "POSTGRES_16"
  region           = var.region
  project          = var.project_id

  # Build the network bridge before building the database
  depends_on = [google_service_networking_connection.private_vpc_connection]

  # Allows for 'terraform destroy'
  deletion_protection = false

  settings {
    tier = "db-f1-micro"

    ip_configuration {
      ipv4_enabled    = false # Zero-Trust: No public internet access
      private_network = google_compute_network.vpc_network.id
    }
  }
}

# 2. The Actual Database inside the Instance
resource "google_sql_database" "rag_db" {
  name     = "ragdb"
  instance = google_sql_database_instance.postgres_instance.name
}

# 3. Secure Random Password Generation
resource "random_password" "db_password" {
  length  = 16
  special = false # Avoid URL parsing errors in the DATABASE_URL connection string
}

# 4. The Database User
resource "google_sql_user" "db_user" {
  name     = "postgres"
  instance = google_sql_database_instance.postgres_instance.name
  password = random_password.db_password.result
}
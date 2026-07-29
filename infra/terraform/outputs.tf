output "cloud_run_url" {
  description = "The public URL of the deployed RAG API"
  value       = google_cloud_run_v2_service.rag_api_service.uri
}

output "database_private_ip" {
  description = "The internal IP address of the Postgres instance"
  value       = google_sql_database_instance.postgres_instance.private_ip_address
}

output "artifact_registry_url" {
  description = "The URI for pushing Docker images"
  value       = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.rag_repository.repository_id}"
}
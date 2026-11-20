output "cloud_run_url" {
  description = "The public URL of the deployed RAG API"
  value       = google_cloud_run_v2_service.rag_api_service.uri
}

output "database_private_ip" {
  description = "The internal IP address of the Postgres instance"
  value       = google_sql_database_instance.postgres_instance.private_ip_address
}

output "staging_bucket_name" {
  description = "The GCS bucket used to stage uploaded PDFs"
  value       = google_storage_bucket.staging_bucket.name
}

output "ingestion_topic_name" {
  description = "The Pub/Sub topic that carries ingestion events"
  value       = google_pubsub_topic.ingestion_events.name
}

output "ingestion_dlq_topic_name" {
  description = "The Pub/Sub dead-letter topic for failed ingestion events"
  value       = google_pubsub_topic.ingestion_dlq.name
}
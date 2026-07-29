resource "google_artifact_registry_repository" "rag_repository" {
  location      = var.region
  repository_id = "${local.resource_prefix}-repo"
  description   = "Secure private container registry for the Enterprise RAG API"
  format        = "DOCKER"
  project       = var.project_id

  labels = local.common_labels

  # Ensures APIs are fully active before trying to build the repository
  depends_on = [google_project_service.enabled_apis]
}
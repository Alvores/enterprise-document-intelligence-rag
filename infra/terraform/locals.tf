locals {
  resource_prefix      = "rag-platform"
  worker_oidc_audience = "${local.resource_prefix}-worker"

  # Standardized tags applied to all manageable cloud resources
  common_labels = {
    environment = "development"
    managed_by  = "terraform"
    project     = "enterprise-document-intelligence"
  }
}
terraform {
  required_version = ">= 1.5.0"

  # Store the Terraform state file securely in Google Cloud Storage
  backend "gcs" {
    bucket = "enterprise-rag-2026-tf-state"
    prefix = "terraform/state"
  }

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.30"
    }
  }
}
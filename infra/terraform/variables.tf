variable "project_id" {
  type        = string
  description = "The Google Cloud Project ID"
}

variable "region" {
  type        = string
  description = "The primary Google Cloud region for deployment"
  default     = "us-central1"
}
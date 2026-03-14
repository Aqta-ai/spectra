variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run services"
  type        = string
  default     = "europe-west1"
}

variable "backend_image" {
  description = "Backend container image (built by deploy.sh or Cloud Build)"
  type        = string
  default     = "europe-west1-docker.pkg.dev/PROJECT_ID/cloud-run-source-deploy/spectra-backend:latest"
}

variable "frontend_image" {
  description = "Frontend container image (built by deploy.sh or Cloud Build)"
  type        = string
  default     = "europe-west1-docker.pkg.dev/PROJECT_ID/cloud-run-source-deploy/spectra-frontend:latest"
}

variable "frontend_domain" {
  description = "Frontend Cloud Run domain for CORS (without https://)"
  type        = string
  default     = ""
}

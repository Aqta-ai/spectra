output "backend_url" {
  description = "Backend Cloud Run URL"
  value       = google_cloud_run_v2_service.backend.uri
}

output "frontend_url" {
  description = "Frontend Cloud Run URL"
  value       = google_cloud_run_v2_service.frontend.uri
}

output "backend_ws_url" {
  description = "WebSocket URL for the frontend to connect to"
  value       = "${replace(google_cloud_run_v2_service.backend.uri, "https://", "wss://")}/ws"
}

output "service_account" {
  description = "Backend service account email"
  value       = google_service_account.backend.email
}

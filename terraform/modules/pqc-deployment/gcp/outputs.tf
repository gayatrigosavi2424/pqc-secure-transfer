# GCP module outputs
output "network_id" {
  description = "ID of the VPC network"
  value       = google_compute_network.main.id
}

output "network_name" {
  description = "Name of the VPC network"
  value       = google_compute_network.main.name
}

output "subnet_id" {
  description = "ID of the subnet"
  value       = google_compute_subnetwork.main.id
}

output "subnet_name" {
  description = "Name of the subnet"
  value       = google_compute_subnetwork.main.name
}

output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_service.main.name
}

output "service_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_service.main.status[0].url
}

output "service_endpoint" {
  description = "Service endpoint URL"
  value       = var.enable_load_balancer && var.enable_ssl ? "https://${google_compute_global_address.main[0].address}" : var.enable_load_balancer ? "http://${google_compute_global_address.main[0].address}" : google_cloud_run_service.main.status[0].url
}

output "monitoring_endpoint" {
  description = "Monitoring endpoint URL"
  value       = "${google_cloud_run_service.main.status[0].url}/metrics"
}

output "service_account_email" {
  description = "Email of the service account"
  value       = google_service_account.cloud_run.email
}

output "load_balancer_ip" {
  description = "IP address of the load balancer"
  value       = var.enable_load_balancer ? google_compute_global_address.main[0].address : null
}

output "vpc_connector_name" {
  description = "Name of the VPC connector"
  value       = var.enable_vpc_connector ? google_vpc_access_connector.main[0].name : null
}

output "storage_bucket_name" {
  description = "Name of the storage bucket"
  value       = google_storage_bucket.main.name
}

output "storage_bucket_url" {
  description = "URL of the storage bucket"
  value       = google_storage_bucket.main.url
}

output "logs_bucket_name" {
  description = "Name of the logs bucket"
  value       = var.enable_centralized_logging ? google_storage_bucket.logs[0].name : null
}

output "log_sink_name" {
  description = "Name of the log sink"
  value       = var.enable_centralized_logging ? google_logging_log_sink.main[0].name : null
}
# GCP Cloud Run module for PQC Secure Transfer
terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
  }
}

# Data sources
data "google_project" "current" {}

# Enable required APIs
resource "google_project_service" "cloud_run_api" {
  service = "run.googleapis.com"
}

resource "google_project_service" "cloud_resource_manager_api" {
  service = "cloudresourcemanager.googleapis.com"
}

resource "google_project_service" "compute_api" {
  service = "compute.googleapis.com"
}

resource "google_project_service" "logging_api" {
  service = "logging.googleapis.com"
}

resource "google_project_service" "monitoring_api" {
  service = "monitoring.googleapis.com"
}

# VPC Network
resource "google_compute_network" "main" {
  name                    = "${var.name_prefix}-vpc"
  auto_create_subnetworks = false
  routing_mode           = "REGIONAL"
}

resource "google_compute_subnetwork" "main" {
  name          = "${var.name_prefix}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.main.id

  secondary_ip_range {
    range_name    = "services-range"
    ip_cidr_range = var.services_cidr
  }

  secondary_ip_range {
    range_name    = "pod-ranges"
    ip_cidr_range = var.pod_cidr
  }
}

# Cloud NAT for outbound connectivity
resource "google_compute_router" "main" {
  count = var.enable_nat_gateway ? 1 : 0

  name    = "${var.name_prefix}-router"
  region  = var.region
  network = google_compute_network.main.id
}

resource "google_compute_router_nat" "main" {
  count = var.enable_nat_gateway ? 1 : 0

  name                               = "${var.name_prefix}-nat"
  router                            = google_compute_router.main[0].name
  region                            = var.region
  nat_ip_allocate_option            = "AUTO_ONLY"
  source_subnetwork_ip_ranges_to_nat = "ALL_SUBNETWORKS_ALL_IP_RANGES"

  log_config {
    enable = true
    filter = "ERRORS_ONLY"
  }
}

# Firewall rules
resource "google_compute_firewall" "allow_health_check" {
  name    = "${var.name_prefix}-allow-health-check"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = [var.container_port]
  }

  source_ranges = ["130.211.0.0/22", "35.191.0.0/16"]
  target_tags   = ["${var.name_prefix}-service"]
}

resource "google_compute_firewall" "allow_internal" {
  name    = "${var.name_prefix}-allow-internal"
  network = google_compute_network.main.name

  allow {
    protocol = "tcp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "udp"
    ports    = ["0-65535"]
  }

  allow {
    protocol = "icmp"
  }

  source_ranges = [var.subnet_cidr]
  target_tags   = ["${var.name_prefix}-service"]
}

# Service Account for Cloud Run
resource "google_service_account" "cloud_run" {
  account_id   = "${var.name_prefix}-cloud-run"
  display_name = "PQC Secure Transfer Cloud Run Service Account"
  description  = "Service account for PQC Secure Transfer Cloud Run service"
}

# IAM bindings for the service account
resource "google_project_iam_member" "cloud_run_logging" {
  project = data.google_project.current.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_project_iam_member" "cloud_run_monitoring" {
  project = data.google_project.current.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

resource "google_project_iam_member" "cloud_run_trace" {
  project = data.google_project.current.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Secret Manager access
resource "google_project_iam_member" "cloud_run_secret_accessor" {
  project = data.google_project.current.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Storage access for file transfers
resource "google_project_iam_member" "cloud_run_storage" {
  project = data.google_project.current.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.cloud_run.email}"
}

# Cloud Run Service
resource "google_cloud_run_service" "main" {
  name     = "${var.name_prefix}-service"
  location = var.region

  template {
    metadata {
      annotations = {
        "autoscaling.knative.dev/minScale"         = var.min_instances
        "autoscaling.knative.dev/maxScale"         = var.max_instances
        "run.googleapis.com/cpu-throttling"        = "false"
        "run.googleapis.com/execution-environment" = "gen2"
        "run.googleapis.com/vpc-access-connector"  = var.enable_vpc_connector ? google_vpc_access_connector.main[0].name : null
      }
      labels = var.labels
    }

    spec {
      container_concurrency = var.container_concurrency
      timeout_seconds      = var.timeout_seconds
      service_account_name = google_service_account.cloud_run.email

      containers {
        image = "${var.image_repository}:${var.image_tag}"

        ports {
          container_port = var.container_port
        }

        resources {
          limits = {
            cpu    = var.cpu_limit
            memory = var.memory_limit
          }
        }

        # Environment variables
        dynamic "env" {
          for_each = var.environment_variables
          content {
            name  = env.key
            value = env.value
          }
        }

        # Secrets from Secret Manager
        dynamic "env" {
          for_each = var.secrets
          content {
            name = env.key
            value_from {
              secret_key_ref {
                name = env.value
                key  = "latest"
              }
            }
          }
        }

        # Startup probe
        startup_probe {
          http_get {
            path = "/health"
            port = var.container_port
          }
          initial_delay_seconds = 10
          timeout_seconds      = 5
          period_seconds       = 10
          failure_threshold    = 3
        }

        # Liveness probe
        liveness_probe {
          http_get {
            path = "/health"
            port = var.container_port
          }
          initial_delay_seconds = 30
          timeout_seconds      = 5
          period_seconds       = 30
          failure_threshold    = 3
        }
      }
    }
  }

  traffic {
    percent         = 100
    latest_revision = true
  }

  depends_on = [
    google_project_service.cloud_run_api,
    google_project_iam_member.cloud_run_logging,
    google_project_iam_member.cloud_run_monitoring
  ]

  lifecycle {
    ignore_changes = [
      template[0].metadata[0].annotations["run.googleapis.com/operation-id"],
    ]
  }
}

# VPC Connector for private network access
resource "google_vpc_access_connector" "main" {
  count = var.enable_vpc_connector ? 1 : 0

  name          = "${var.name_prefix}-connector"
  region        = var.region
  ip_cidr_range = var.connector_cidr
  network       = google_compute_network.main.name

  min_throughput = var.connector_min_throughput
  max_throughput = var.connector_max_throughput

  depends_on = [google_project_service.compute_api]
}

# Cloud Run IAM policy for public access (if enabled)
resource "google_cloud_run_service_iam_member" "public_access" {
  count = var.allow_public_access ? 1 : 0

  service  = google_cloud_run_service.main.name
  location = google_cloud_run_service.main.location
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# Load Balancer (if enabled)
resource "google_compute_global_address" "main" {
  count = var.enable_load_balancer ? 1 : 0

  name = "${var.name_prefix}-lb-ip"
}

resource "google_compute_managed_ssl_certificate" "main" {
  count = var.enable_load_balancer && var.enable_ssl ? 1 : 0

  name = "${var.name_prefix}-ssl-cert"

  managed {
    domains = var.ssl_domains
  }
}

resource "google_compute_backend_service" "main" {
  count = var.enable_load_balancer ? 1 : 0

  name        = "${var.name_prefix}-backend"
  protocol    = "HTTP"
  timeout_sec = 30

  backend {
    group = google_compute_region_network_endpoint_group.main[0].id
  }

  health_checks = [google_compute_health_check.main[0].id]

  log_config {
    enable      = true
    sample_rate = 1.0
  }
}

resource "google_compute_region_network_endpoint_group" "main" {
  count = var.enable_load_balancer ? 1 : 0

  name                  = "${var.name_prefix}-neg"
  network_endpoint_type = "SERVERLESS"
  region                = var.region

  cloud_run {
    service = google_cloud_run_service.main.name
  }
}

resource "google_compute_health_check" "main" {
  count = var.enable_load_balancer ? 1 : 0

  name = "${var.name_prefix}-health-check"

  http_health_check {
    port         = var.container_port
    request_path = "/health"
  }

  check_interval_sec  = 30
  timeout_sec         = 5
  healthy_threshold   = 2
  unhealthy_threshold = 3
}

resource "google_compute_url_map" "main" {
  count = var.enable_load_balancer ? 1 : 0

  name            = "${var.name_prefix}-url-map"
  default_service = google_compute_backend_service.main[0].id
}

resource "google_compute_target_https_proxy" "main" {
  count = var.enable_load_balancer && var.enable_ssl ? 1 : 0

  name             = "${var.name_prefix}-https-proxy"
  url_map          = google_compute_url_map.main[0].id
  ssl_certificates = [google_compute_managed_ssl_certificate.main[0].id]
}

resource "google_compute_target_http_proxy" "main" {
  count = var.enable_load_balancer && !var.enable_ssl ? 1 : 0

  name    = "${var.name_prefix}-http-proxy"
  url_map = google_compute_url_map.main[0].id
}

resource "google_compute_global_forwarding_rule" "https" {
  count = var.enable_load_balancer && var.enable_ssl ? 1 : 0

  name       = "${var.name_prefix}-https-forwarding-rule"
  target     = google_compute_target_https_proxy.main[0].id
  port_range = "443"
  ip_address = google_compute_global_address.main[0].address
}

resource "google_compute_global_forwarding_rule" "http" {
  count = var.enable_load_balancer && !var.enable_ssl ? 1 : 0

  name       = "${var.name_prefix}-http-forwarding-rule"
  target     = google_compute_target_http_proxy.main[0].id
  port_range = "80"
  ip_address = google_compute_global_address.main[0].address
}

# Cloud Storage bucket for file transfers
resource "google_storage_bucket" "main" {
  name     = "${var.name_prefix}-${random_id.bucket_suffix.hex}"
  location = var.region

  uniform_bucket_level_access = true
  force_destroy              = var.environment != "prod"

  versioning {
    enabled = var.environment == "prod"
  }

  lifecycle_rule {
    condition {
      age = var.storage_retention_days
    }
    action {
      type = "Delete"
    }
  }

  encryption {
    default_kms_key_name = var.kms_key_name
  }

  labels = var.labels
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# Monitoring and Logging
resource "google_logging_log_sink" "main" {
  count = var.enable_centralized_logging ? 1 : 0

  name        = "${var.name_prefix}-log-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.logs[0].name}"

  filter = "resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${google_cloud_run_service.main.name}\""

  unique_writer_identity = true
}

resource "google_storage_bucket" "logs" {
  count = var.enable_centralized_logging ? 1 : 0

  name     = "${var.name_prefix}-logs-${random_id.logs_bucket_suffix[0].hex}"
  location = var.region

  uniform_bucket_level_access = true
  force_destroy              = var.environment != "prod"

  lifecycle_rule {
    condition {
      age = var.log_retention_days
    }
    action {
      type = "Delete"
    }
  }

  labels = var.labels
}

resource "random_id" "logs_bucket_suffix" {
  count = var.enable_centralized_logging ? 1 : 0

  byte_length = 4
}

resource "google_storage_bucket_iam_member" "log_sink_writer" {
  count = var.enable_centralized_logging ? 1 : 0

  bucket = google_storage_bucket.logs[0].name
  role   = "roles/storage.objectCreator"
  member = google_logging_log_sink.main[0].writer_identity
}
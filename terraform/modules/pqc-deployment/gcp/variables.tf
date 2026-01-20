# GCP module variables
variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
}

variable "environment" {
  description = "Environment name (dev/staging/prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "labels" {
  description = "Labels to apply to all resources"
  type        = map(string)
  default     = {}
}

# Networking
variable "subnet_cidr" {
  description = "CIDR block for the subnet"
  type        = string
  default     = "10.0.0.0/24"
}

variable "services_cidr" {
  description = "CIDR block for services"
  type        = string
  default     = "10.1.0.0/24"
}

variable "pod_cidr" {
  description = "CIDR block for pods"
  type        = string
  default     = "10.2.0.0/24"
}

variable "enable_nat_gateway" {
  description = "Enable Cloud NAT for outbound connectivity"
  type        = bool
  default     = true
}

# VPC Connector
variable "enable_vpc_connector" {
  description = "Enable VPC connector for private network access"
  type        = bool
  default     = false
}

variable "connector_cidr" {
  description = "CIDR block for VPC connector"
  type        = string
  default     = "10.8.0.0/28"
}

variable "connector_min_throughput" {
  description = "Minimum throughput for VPC connector"
  type        = number
  default     = 200
}

variable "connector_max_throughput" {
  description = "Maximum throughput for VPC connector"
  type        = number
  default     = 1000
}

# Container Configuration
variable "image_repository" {
  description = "Docker image repository"
  type        = string
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "container_port" {
  description = "Port exposed by the container"
  type        = number
  default     = 8765
}

# Cloud Run Configuration
variable "cpu_limit" {
  description = "CPU limit for the container"
  type        = string
  default     = "2000m"
}

variable "memory_limit" {
  description = "Memory limit for the container"
  type        = string
  default     = "2Gi"
}

variable "container_concurrency" {
  description = "Maximum number of concurrent requests per container"
  type        = number
  default     = 100
}

variable "timeout_seconds" {
  description = "Request timeout in seconds"
  type        = number
  default     = 300
}

# Auto Scaling
variable "min_instances" {
  description = "Minimum number of instances"
  type        = number
  default     = 1
}

variable "max_instances" {
  description = "Maximum number of instances"
  type        = number
  default     = 10
}

# Access Control
variable "allow_public_access" {
  description = "Allow public access to the service"
  type        = bool
  default     = true
}

# Load Balancer
variable "enable_load_balancer" {
  description = "Enable load balancer"
  type        = bool
  default     = false
}

variable "enable_ssl" {
  description = "Enable SSL/TLS"
  type        = bool
  default     = false
}

variable "ssl_domains" {
  description = "Domains for SSL certificate"
  type        = list(string)
  default     = []
}

# Environment Variables and Secrets
variable "environment_variables" {
  description = "Environment variables for the container"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets for the container (name -> secret_name)"
  type        = map(string)
  default     = {}
}

# Storage
variable "storage_retention_days" {
  description = "Storage retention in days"
  type        = number
  default     = 30
}

variable "kms_key_name" {
  description = "KMS key name for encryption"
  type        = string
  default     = null
}

# Logging
variable "enable_centralized_logging" {
  description = "Enable centralized logging"
  type        = bool
  default     = true
}

variable "log_retention_days" {
  description = "Log retention in days"
  type        = number
  default     = 30
}
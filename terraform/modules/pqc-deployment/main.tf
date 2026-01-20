# Main Terraform configuration for PQC Secure Transfer deployment
terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    google = {
      source  = "hashicorp/google"
      version = "~> 4.0"
    }
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

# Variables
variable "environment" {
  description = "Environment name (dev/staging/prod)"
  type        = string
  validation {
    condition     = contains(["dev", "staging", "prod"], var.environment)
    error_message = "Environment must be dev, staging, or prod."
  }
}

variable "cloud_provider" {
  description = "Cloud provider (aws/gcp/azure)"
  type        = string
  validation {
    condition     = contains(["aws", "gcp", "azure"], var.cloud_provider)
    error_message = "Cloud provider must be aws, gcp, or azure."
  }
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "pqc-secure-transfer"
}

variable "region" {
  description = "Cloud provider region"
  type        = string
  default     = "us-west-2"
}

variable "instance_count" {
  description = "Number of container instances"
  type        = number
  default     = 2
}

variable "instance_size" {
  description = "Container instance size"
  type        = string
  default     = "medium"
}

variable "enable_autoscaling" {
  description = "Enable auto-scaling"
  type        = bool
  default     = true
}

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

variable "pqc_algorithm" {
  description = "PQC algorithm to use"
  type        = string
  default     = "Kyber768"
}

variable "image_repository" {
  description = "Docker image repository"
  type        = string
  default     = "pqc-secure-transfer"
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "latest"
}

variable "custom_env_vars" {
  description = "Custom environment variables"
  type        = map(string)
  default     = {}
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

# Cloud-specific deployments
module "aws_deployment" {
  count  = var.cloud_provider == "aws" ? 1 : 0
  source = "./aws"

  name_prefix    = "${var.name_prefix}-${var.environment}"
  environment    = var.environment
  instance_count = var.instance_count
  
  # Container configuration
  image_repository = var.image_repository
  image_tag       = var.image_tag
  
  # Scaling configuration
  enable_autoscaling = var.enable_autoscaling
  min_instances     = var.min_instances
  max_instances     = var.max_instances
  
  # Environment variables
  environment_variables = merge(
    {
      ENVIRONMENT   = var.environment
      PQC_ALGORITHM = var.pqc_algorithm
    },
    var.custom_env_vars
  )
  
  tags = merge(
    {
      Environment = var.environment
      Application = "pqc-secure-transfer"
      CloudProvider = "aws"
    },
    var.tags
  )
}

module "gcp_deployment" {
  count  = var.cloud_provider == "gcp" ? 1 : 0
  source = "./gcp"

  name_prefix = "${var.name_prefix}-${var.environment}"
  environment = var.environment
  region      = var.region
  
  # Container configuration
  image_repository = var.image_repository
  image_tag       = var.image_tag
  
  # Scaling configuration
  min_instances = var.min_instances
  max_instances = var.max_instances
  
  # Environment variables
  environment_variables = merge(
    {
      ENVIRONMENT   = var.environment
      PQC_ALGORITHM = var.pqc_algorithm
    },
    var.custom_env_vars
  )
  
  labels = merge(
    {
      environment = var.environment
      application = "pqc-secure-transfer"
      cloud-provider = "gcp"
    },
    var.tags
  )
}

module "azure_deployment" {
  count  = var.cloud_provider == "azure" ? 1 : 0
  source = "./azure"

  name_prefix = "${var.name_prefix}-${var.environment}"
  environment = var.environment
  location    = var.region
  
  # Container configuration
  image_repository = var.image_repository
  image_tag       = var.image_tag
  
  # Scaling configuration
  enable_autoscaling = var.enable_autoscaling
  min_instances     = var.min_instances
  max_instances     = var.max_instances
  
  # Environment variables
  environment_variables = merge(
    {
      ENVIRONMENT   = var.environment
      PQC_ALGORITHM = var.pqc_algorithm
    },
    var.custom_env_vars
  )
  
  tags = merge(
    {
      Environment = var.environment
      Application = "pqc-secure-transfer"
      CloudProvider = "azure"
    },
    var.tags
  )
}

# Outputs
output "service_endpoint" {
  description = "Service endpoint URL"
  value = var.cloud_provider == "aws" ? (
    length(module.aws_deployment) > 0 ? module.aws_deployment[0].service_endpoint : null
  ) : var.cloud_provider == "gcp" ? (
    length(module.gcp_deployment) > 0 ? module.gcp_deployment[0].service_endpoint : null
  ) : var.cloud_provider == "azure" ? (
    length(module.azure_deployment) > 0 ? module.azure_deployment[0].service_endpoint : null
  ) : null
}

output "monitoring_endpoint" {
  description = "Monitoring endpoint URL"
  value = var.cloud_provider == "aws" ? (
    length(module.aws_deployment) > 0 ? module.aws_deployment[0].monitoring_endpoint : null
  ) : var.cloud_provider == "gcp" ? (
    length(module.gcp_deployment) > 0 ? module.gcp_deployment[0].monitoring_endpoint : null
  ) : var.cloud_provider == "azure" ? (
    length(module.azure_deployment) > 0 ? module.azure_deployment[0].monitoring_endpoint : null
  ) : null
}

# Additional outputs for each cloud provider
output "aws_outputs" {
  description = "AWS-specific outputs"
  value = var.cloud_provider == "aws" && length(module.aws_deployment) > 0 ? {
    vpc_id                = module.aws_deployment[0].vpc_id
    ecs_cluster_name      = module.aws_deployment[0].ecs_cluster_name
    load_balancer_dns_name = module.aws_deployment[0].load_balancer_dns_name
  } : null
}

output "gcp_outputs" {
  description = "GCP-specific outputs"
  value = var.cloud_provider == "gcp" && length(module.gcp_deployment) > 0 ? {
    network_name      = module.gcp_deployment[0].network_name
    service_name      = module.gcp_deployment[0].service_name
    service_url       = module.gcp_deployment[0].service_url
  } : null
}

output "azure_outputs" {
  description = "Azure-specific outputs"
  value = var.cloud_provider == "azure" && length(module.azure_deployment) > 0 ? {
    resource_group_name    = module.azure_deployment[0].resource_group_name
    container_group_name   = module.azure_deployment[0].container_group_name
    container_group_fqdn   = module.azure_deployment[0].container_group_fqdn
  } : null
}
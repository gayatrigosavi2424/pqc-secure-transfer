# Development environment Terraform configuration
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
  
  # Configure remote state storage
  backend "s3" {
    # These values should be provided via backend config file or CLI
    # bucket = "pqc-terraform-state-dev"
    # key    = "dev/terraform.tfstate"
    # region = "us-west-2"
  }
}

# Configure providers
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = "dev"
      Project     = "pqc-secure-transfer"
      ManagedBy   = "terraform"
    }
  }
}

provider "google" {
  project = var.gcp_project_id
  region  = var.gcp_region
}

provider "azurerm" {
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
    
    key_vault {
      purge_soft_delete_on_destroy    = true
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Local values for development environment
locals {
  environment = "dev"
  
  # Development-specific configuration
  dev_config = {
    instance_count     = 1
    min_instances     = 1
    max_instances     = 3
    enable_autoscaling = false
    enable_ssl        = false
    
    # Resource sizing for development
    aws_task_cpu      = 512
    aws_task_memory   = 1024
    gcp_cpu_limit     = "1000m"
    gcp_memory_limit  = "2Gi"
    azure_cpu_limit   = 1
    azure_memory_limit = 2
  }
  
  # Common environment variables for all cloud providers
  common_env_vars = {
    ENVIRONMENT     = local.environment
    LOG_LEVEL      = "DEBUG"
    PQC_ALGORITHM  = var.pqc_algorithm
    DEBUG          = "true"
  }
  
  # Common tags
  common_tags = {
    Environment = local.environment
    Project     = "pqc-secure-transfer"
    ManagedBy   = "terraform"
    CostCenter  = "development"
  }
}

# Deploy to the specified cloud provider
module "pqc_deployment" {
  source = "../../modules/pqc-deployment"
  
  # Basic configuration
  environment      = local.environment
  cloud_provider   = var.cloud_provider
  name_prefix      = var.name_prefix
  region          = var.region
  
  # Container configuration
  image_repository = var.image_repository
  image_tag       = var.image_tag
  
  # Scaling configuration
  instance_count     = local.dev_config.instance_count
  enable_autoscaling = local.dev_config.enable_autoscaling
  min_instances     = local.dev_config.min_instances
  max_instances     = local.dev_config.max_instances
  
  # PQC configuration
  pqc_algorithm = var.pqc_algorithm
  
  # Environment variables
  custom_env_vars = merge(local.common_env_vars, var.custom_env_vars)
  
  # Tags
  tags = merge(local.common_tags, var.additional_tags)
}

# Outputs
output "service_endpoint" {
  description = "Service endpoint URL"
  value       = module.pqc_deployment.service_endpoint
}

output "monitoring_endpoint" {
  description = "Monitoring endpoint URL"
  value       = module.pqc_deployment.monitoring_endpoint
}

output "deployment_info" {
  description = "Deployment information"
  value = {
    environment     = local.environment
    cloud_provider  = var.cloud_provider
    region         = var.region
    service_endpoint = module.pqc_deployment.service_endpoint
    
    # Cloud-specific outputs
    aws_outputs   = module.pqc_deployment.aws_outputs
    gcp_outputs   = module.pqc_deployment.gcp_outputs
    azure_outputs = module.pqc_deployment.azure_outputs
  }
  
  sensitive = false
}
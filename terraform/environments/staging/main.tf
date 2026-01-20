# Staging environment Terraform configuration
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
    # bucket = "pqc-terraform-state-staging"
    # key    = "staging/terraform.tfstate"
    # region = "us-west-2"
  }
}

# Configure providers
provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = "staging"
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
      purge_soft_delete_on_destroy    = false
      recover_soft_deleted_key_vaults = true
    }
  }
}

# Local values for staging environment
locals {
  environment = "staging"
  
  # Staging-specific configuration
  staging_config = {
    instance_count     = 2
    min_instances     = 2
    max_instances     = 10
    enable_autoscaling = true
    enable_ssl        = true
    
    # Resource sizing for staging
    aws_task_cpu      = 1024
    aws_task_memory   = 2048
    gcp_cpu_limit     = "2000m"
    gcp_memory_limit  = "4Gi"
    azure_cpu_limit   = 2
    azure_memory_limit = 4
  }
  
  # Common environment variables for all cloud providers
  common_env_vars = {
    ENVIRONMENT     = local.environment
    LOG_LEVEL      = "INFO"
    PQC_ALGORITHM  = var.pqc_algorithm
    ENABLE_METRICS = "true"
  }
  
  # Common tags
  common_tags = {
    Environment = local.environment
    Project     = "pqc-secure-transfer"
    ManagedBy   = "terraform"
    CostCenter  = "staging"
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
  instance_count     = local.staging_config.instance_count
  enable_autoscaling = local.staging_config.enable_autoscaling
  min_instances     = local.staging_config.min_instances
  max_instances     = local.staging_config.max_instances
  
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
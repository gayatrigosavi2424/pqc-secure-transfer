# Shared networking configurations and security groups
locals {
  # Common CIDR blocks for consistent networking across cloud providers
  vpc_cidrs = {
    dev     = "10.0.0.0/16"
    staging = "10.1.0.0/16"
    prod    = "10.2.0.0/16"
  }
  
  public_subnet_cidrs = {
    dev     = ["10.0.1.0/24", "10.0.2.0/24"]
    staging = ["10.1.1.0/24", "10.1.2.0/24"]
    prod    = ["10.2.1.0/24", "10.2.2.0/24"]
  }
  
  private_subnet_cidrs = {
    dev     = ["10.0.10.0/24", "10.0.20.0/24"]
    staging = ["10.1.10.0/24", "10.1.20.0/24"]
    prod    = ["10.2.10.0/24", "10.2.20.0/24"]
  }
  
  # Common security group rules
  security_rules = {
    # Allow HTTP traffic
    http = {
      port        = 80
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTP traffic"
    }
    
    # Allow HTTPS traffic
    https = {
      port        = 443
      protocol    = "tcp"
      cidr_blocks = ["0.0.0.0/0"]
      description = "HTTPS traffic"
    }
    
    # Allow PQC service traffic
    pqc_service = {
      port        = 8765
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/8"]
      description = "PQC Secure Transfer service"
    }
    
    # Allow health check traffic
    health_check = {
      port        = 8765
      protocol    = "tcp"
      cidr_blocks = ["130.211.0.0/22", "35.191.0.0/16", "168.63.129.16/32"]
      description = "Health check traffic from load balancers"
    }
    
    # Allow monitoring traffic
    monitoring = {
      port        = 9090
      protocol    = "tcp"
      cidr_blocks = ["10.0.0.0/8"]
      description = "Prometheus monitoring"
    }
  }
  
  # Common tags for all resources
  common_tags = {
    Project     = "pqc-secure-transfer"
    ManagedBy   = "terraform"
    Component   = "networking"
  }
}

# Output networking configurations for use by cloud-specific modules
output "vpc_cidr" {
  description = "VPC CIDR block for the environment"
  value       = local.vpc_cidrs[var.environment]
}

output "public_subnet_cidrs" {
  description = "Public subnet CIDR blocks for the environment"
  value       = local.public_subnet_cidrs[var.environment]
}

output "private_subnet_cidrs" {
  description = "Private subnet CIDR blocks for the environment"
  value       = local.private_subnet_cidrs[var.environment]
}

output "security_rules" {
  description = "Common security rules"
  value       = local.security_rules
}

output "common_tags" {
  description = "Common tags for all resources"
  value       = local.common_tags
}

# Variables for the shared module
variable "environment" {
  description = "Environment name (dev/staging/prod)"
  type        = string
}
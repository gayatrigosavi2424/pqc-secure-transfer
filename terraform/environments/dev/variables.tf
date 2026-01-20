# Development environment variables
variable "cloud_provider" {
  description = "Cloud provider to deploy to (aws/gcp/azure)"
  type        = string
  default     = "aws"
  
  validation {
    condition     = contains(["aws", "gcp", "azure"], var.cloud_provider)
    error_message = "Cloud provider must be aws, gcp, or azure."
  }
}

variable "region" {
  description = "Cloud provider region"
  type        = string
  default     = "us-west-2"
}

variable "name_prefix" {
  description = "Prefix for resource names"
  type        = string
  default     = "pqc-dev"
}

# AWS-specific variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

# GCP-specific variables
variable "gcp_project_id" {
  description = "GCP project ID"
  type        = string
  default     = ""
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

# Container configuration
variable "image_repository" {
  description = "Docker image repository"
  type        = string
  default     = "pqc-secure-transfer"
}

variable "image_tag" {
  description = "Docker image tag"
  type        = string
  default     = "dev"
}

# PQC configuration
variable "pqc_algorithm" {
  description = "PQC algorithm to use"
  type        = string
  default     = "Kyber768"
  
  validation {
    condition     = contains(["Kyber512", "Kyber768", "Kyber1024"], var.pqc_algorithm)
    error_message = "PQC algorithm must be Kyber512, Kyber768, or Kyber1024."
  }
}

# Environment variables
variable "custom_env_vars" {
  description = "Custom environment variables"
  type        = map(string)
  default     = {}
}

# Tags
variable "additional_tags" {
  description = "Additional tags to apply to resources"
  type        = map(string)
  default     = {}
}
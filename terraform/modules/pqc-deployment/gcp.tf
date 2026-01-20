# GCP-specific resources for PQC Secure Transfer
module "gcp_deployment" {
  count  = var.cloud_provider == "gcp" ? 1 : 0
  source = "./gcp"

  environment      = var.environment
  instance_count   = var.instance_count
  instance_size    = var.instance_size
  enable_autoscaling = var.enable_autoscaling
  pqc_algorithm    = var.pqc_algorithm
}
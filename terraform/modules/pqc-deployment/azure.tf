# Azure-specific resources for PQC Secure Transfer
module "azure_deployment" {
  count  = var.cloud_provider == "azure" ? 1 : 0
  source = "./azure"

  environment      = var.environment
  instance_count   = var.instance_count
  instance_size    = var.instance_size
  enable_autoscaling = var.enable_autoscaling
  pqc_algorithm    = var.pqc_algorithm
}
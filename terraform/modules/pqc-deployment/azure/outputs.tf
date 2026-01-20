# Azure module outputs
output "resource_group_name" {
  description = "Name of the resource group"
  value       = azurerm_resource_group.main.name
}

output "resource_group_id" {
  description = "ID of the resource group"
  value       = azurerm_resource_group.main.id
}

output "vnet_id" {
  description = "ID of the virtual network"
  value       = azurerm_virtual_network.main.id
}

output "vnet_name" {
  description = "Name of the virtual network"
  value       = azurerm_virtual_network.main.name
}

output "public_subnet_id" {
  description = "ID of the public subnet"
  value       = azurerm_subnet.public.id
}

output "private_subnet_id" {
  description = "ID of the private subnet"
  value       = azurerm_subnet.private.id
}

output "container_group_id" {
  description = "ID of the main container group"
  value       = azurerm_container_group.main.id
}

output "container_group_name" {
  description = "Name of the main container group"
  value       = azurerm_container_group.main.name
}

output "container_group_ip" {
  description = "IP address of the main container group"
  value       = azurerm_container_group.main.ip_address
}

output "container_group_fqdn" {
  description = "FQDN of the main container group"
  value       = azurerm_container_group.main.fqdn
}

output "service_endpoint" {
  description = "Service endpoint URL"
  value       = var.enable_application_gateway ? "http://${azurerm_public_ip.main[0].ip_address}" : "http://${azurerm_container_group.main.fqdn}:${var.container_port}"
}

output "monitoring_endpoint" {
  description = "Monitoring endpoint URL"
  value       = var.enable_application_gateway ? "http://${azurerm_public_ip.main[0].ip_address}/metrics" : "http://${azurerm_container_group.main.fqdn}:${var.container_port}/metrics"
}

output "application_gateway_id" {
  description = "ID of the application gateway"
  value       = var.enable_application_gateway ? azurerm_application_gateway.main[0].id : null
}

output "application_gateway_public_ip" {
  description = "Public IP of the application gateway"
  value       = var.enable_application_gateway ? azurerm_public_ip.main[0].ip_address : null
}

output "user_assigned_identity_id" {
  description = "ID of the user assigned identity"
  value       = azurerm_user_assigned_identity.main.id
}

output "user_assigned_identity_principal_id" {
  description = "Principal ID of the user assigned identity"
  value       = azurerm_user_assigned_identity.main.principal_id
}

output "key_vault_id" {
  description = "ID of the key vault"
  value       = azurerm_key_vault.main.id
}

output "key_vault_uri" {
  description = "URI of the key vault"
  value       = azurerm_key_vault.main.vault_uri
}

output "storage_account_id" {
  description = "ID of the storage account"
  value       = azurerm_storage_account.main.id
}

output "storage_account_name" {
  description = "Name of the storage account"
  value       = azurerm_storage_account.main.name
}

output "storage_container_name" {
  description = "Name of the storage container"
  value       = azurerm_storage_container.main.name
}

output "log_analytics_workspace_id" {
  description = "ID of the log analytics workspace"
  value       = azurerm_log_analytics_workspace.main.id
}

output "log_analytics_workspace_name" {
  description = "Name of the log analytics workspace"
  value       = azurerm_log_analytics_workspace.main.name
}

output "scaled_container_groups" {
  description = "Information about scaled container groups"
  value = var.enable_autoscaling ? [
    for i, cg in azurerm_container_group.scaled : {
      id   = cg.id
      name = cg.name
      ip   = cg.ip_address
      fqdn = cg.fqdn
    }
  ] : []
}
# Azure Container Instances module for PQC Secure Transfer
terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

# Data sources
data "azurerm_client_config" "current" {}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = "${var.name_prefix}-rg"
  location = var.location

  tags = var.tags
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.name_prefix}-vnet"
  address_space       = [var.vnet_cidr]
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = var.tags
}

resource "azurerm_subnet" "public" {
  name                 = "${var.name_prefix}-public-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.public_subnet_cidr]
}

resource "azurerm_subnet" "private" {
  name                 = "${var.name_prefix}-private-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = [var.private_subnet_cidr]

  delegation {
    name = "container-instances"
    service_delegation {
      name    = "Microsoft.ContainerInstance/containerGroups"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# Network Security Groups
resource "azurerm_network_security_group" "public" {
  name                = "${var.name_prefix}-public-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "HTTP"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "80"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  security_rule {
    name                       = "HTTPS"
    priority                   = 1002
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "443"
    source_address_prefix      = "*"
    destination_address_prefix = "*"
  }

  tags = var.tags
}

resource "azurerm_network_security_group" "private" {
  name                = "${var.name_prefix}-private-nsg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  security_rule {
    name                       = "PQC-Service"
    priority                   = 1001
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = tostring(var.container_port)
    source_address_prefix      = var.public_subnet_cidr
    destination_address_prefix = "*"
  }

  tags = var.tags
}

resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = azurerm_subnet.public.id
  network_security_group_id = azurerm_network_security_group.public.id
}

resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = azurerm_subnet.private.id
  network_security_group_id = azurerm_network_security_group.private.id
}

# Public IP for Application Gateway
resource "azurerm_public_ip" "main" {
  count = var.enable_application_gateway ? 1 : 0

  name                = "${var.name_prefix}-pip"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  allocation_method   = "Static"
  sku                 = "Standard"

  tags = var.tags
}

# Application Gateway
resource "azurerm_application_gateway" "main" {
  count = var.enable_application_gateway ? 1 : 0

  name                = "${var.name_prefix}-appgw"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  sku {
    name     = var.app_gateway_sku_name
    tier     = var.app_gateway_sku_tier
    capacity = var.app_gateway_capacity
  }

  gateway_ip_configuration {
    name      = "gateway-ip-configuration"
    subnet_id = azurerm_subnet.public.id
  }

  frontend_port {
    name = "frontend-port-80"
    port = 80
  }

  frontend_port {
    name = "frontend-port-443"
    port = 443
  }

  frontend_ip_configuration {
    name                 = "frontend-ip-configuration"
    public_ip_address_id = azurerm_public_ip.main[0].id
  }

  backend_address_pool {
    name = "backend-pool"
  }

  backend_http_settings {
    name                  = "backend-http-settings"
    cookie_based_affinity = "Disabled"
    path                  = "/"
    port                  = var.container_port
    protocol              = "Http"
    request_timeout       = 60

    probe_name = "health-probe"
  }

  probe {
    name                = "health-probe"
    protocol            = "Http"
    path                = "/health"
    host                = "127.0.0.1"
    interval            = 30
    timeout             = 30
    unhealthy_threshold = 3
  }

  http_listener {
    name                           = "http-listener"
    frontend_ip_configuration_name = "frontend-ip-configuration"
    frontend_port_name             = "frontend-port-80"
    protocol                       = "Http"
  }

  request_routing_rule {
    name                       = "routing-rule"
    rule_type                  = "Basic"
    http_listener_name         = "http-listener"
    backend_address_pool_name  = "backend-pool"
    backend_http_settings_name = "backend-http-settings"
    priority                   = 1
  }

  tags = var.tags
}

# User Assigned Identity for Container Instances
resource "azurerm_user_assigned_identity" "main" {
  name                = "${var.name_prefix}-identity"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location

  tags = var.tags
}

# Key Vault for secrets
resource "azurerm_key_vault" "main" {
  name                = "${var.name_prefix}-kv-${random_string.kv_suffix.result}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  tenant_id           = data.azurerm_client_config.current.tenant_id
  sku_name            = "standard"

  purge_protection_enabled   = var.environment == "prod"
  soft_delete_retention_days = var.environment == "prod" ? 90 : 7

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id

    key_permissions = [
      "Create", "Delete", "Get", "List", "Update", "Import", "Backup", "Restore"
    ]

    secret_permissions = [
      "Set", "Get", "Delete", "List", "Purge", "Recover"
    ]
  }

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = azurerm_user_assigned_identity.main.principal_id

    secret_permissions = [
      "Get", "List"
    ]
  }

  tags = var.tags
}

resource "random_string" "kv_suffix" {
  length  = 4
  special = false
  upper   = false
}

# Storage Account for file transfers
resource "azurerm_storage_account" "main" {
  name                     = "${replace(var.name_prefix, "-", "")}st${random_string.storage_suffix.result}"
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = var.environment == "prod" ? "GRS" : "LRS"
  
  min_tls_version                = "TLS1_2"
  allow_nested_items_to_be_public = false

  blob_properties {
    delete_retention_policy {
      days = var.storage_retention_days
    }
    versioning_enabled = var.environment == "prod"
  }

  tags = var.tags
}

resource "random_string" "storage_suffix" {
  length  = 4
  special = false
  upper   = false
}

resource "azurerm_storage_container" "main" {
  name                  = "pqc-transfers"
  storage_account_name  = azurerm_storage_account.main.name
  container_access_type = "private"
}

# Role assignment for storage access
resource "azurerm_role_assignment" "storage_blob_data_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_user_assigned_identity.main.principal_id
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "main" {
  name                = "${var.name_prefix}-law"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = var.log_retention_days

  tags = var.tags
}

# Container Group
resource "azurerm_container_group" "main" {
  name                = "${var.name_prefix}-cg"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  ip_address_type     = var.enable_application_gateway ? "Private" : "Public"
  dns_name_label      = var.enable_application_gateway ? null : "${var.name_prefix}-${random_string.dns_suffix.result}"
  os_type             = "Linux"
  restart_policy      = "Always"
  subnet_ids          = var.enable_application_gateway ? [azurerm_subnet.private.id] : null

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }

  container {
    name   = "pqc-secure-transfer"
    image  = "${var.image_repository}:${var.image_tag}"
    cpu    = var.cpu_limit
    memory = var.memory_limit

    ports {
      port     = var.container_port
      protocol = "TCP"
    }

    # Environment variables
    dynamic "environment_variables" {
      for_each = var.environment_variables
      content {
        name  = environment_variables.key
        value = environment_variables.value
      }
    }

    # Secure environment variables from Key Vault
    dynamic "secure_environment_variables" {
      for_each = var.secrets
      content {
        name  = secure_environment_variables.key
        value = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.main.vault_uri}secrets/${secure_environment_variables.value}/)"
      }
    }

    liveness_probe {
      http_get {
        path   = "/health"
        port   = var.container_port
        scheme = "Http"
      }
      initial_delay_seconds = 30
      period_seconds        = 30
      failure_threshold     = 3
      timeout_seconds       = 5
    }

    readiness_probe {
      http_get {
        path   = "/ready"
        port   = var.container_port
        scheme = "Http"
      }
      initial_delay_seconds = 10
      period_seconds        = 10
      failure_threshold     = 3
      timeout_seconds       = 5
    }

    volume {
      name                 = "logs"
      mount_path           = "/var/log"
      read_only            = false
      empty_dir            = {}
    }
  }

  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.main.workspace_id
      workspace_key = azurerm_log_analytics_workspace.main.primary_shared_key
    }
  }

  tags = var.tags

  depends_on = [
    azurerm_role_assignment.storage_blob_data_contributor
  ]
}

resource "random_string" "dns_suffix" {
  length  = 8
  special = false
  upper   = false
}

# Application Gateway Backend Pool Association
resource "azurerm_network_interface_application_gateway_backend_address_pool_association" "main" {
  count = var.enable_application_gateway ? 1 : 0

  network_interface_id    = azurerm_container_group.main.network_interface_ids[0]
  ip_configuration_name   = "default"
  backend_address_pool_id = azurerm_application_gateway.main[0].backend_address_pool[0].id
}

# Auto Scaling (using Azure Container Instances doesn't support native auto-scaling, 
# but we can implement it using Azure Functions or Logic Apps)
# For now, we'll create multiple container groups if scaling is needed

resource "azurerm_container_group" "scaled" {
  count = var.enable_autoscaling ? var.max_instances - 1 : 0

  name                = "${var.name_prefix}-cg-${count.index + 2}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  ip_address_type     = var.enable_application_gateway ? "Private" : "Public"
  dns_name_label      = var.enable_application_gateway ? null : "${var.name_prefix}-${count.index + 2}-${random_string.dns_suffix.result}"
  os_type             = "Linux"
  restart_policy      = "Always"
  subnet_ids          = var.enable_application_gateway ? [azurerm_subnet.private.id] : null

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.main.id]
  }

  container {
    name   = "pqc-secure-transfer"
    image  = "${var.image_repository}:${var.image_tag}"
    cpu    = var.cpu_limit
    memory = var.memory_limit

    ports {
      port     = var.container_port
      protocol = "TCP"
    }

    # Environment variables
    dynamic "environment_variables" {
      for_each = var.environment_variables
      content {
        name  = environment_variables.key
        value = environment_variables.value
      }
    }

    # Secure environment variables from Key Vault
    dynamic "secure_environment_variables" {
      for_each = var.secrets
      content {
        name  = secure_environment_variables.key
        value = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault.main.vault_uri}secrets/${secure_environment_variables.value}/)"
      }
    }

    liveness_probe {
      http_get {
        path   = "/health"
        port   = var.container_port
        scheme = "Http"
      }
      initial_delay_seconds = 30
      period_seconds        = 30
      failure_threshold     = 3
      timeout_seconds       = 5
    }

    readiness_probe {
      http_get {
        path   = "/ready"
        port   = var.container_port
        scheme = "Http"
      }
      initial_delay_seconds = 10
      period_seconds        = 10
      failure_threshold     = 3
      timeout_seconds       = 5
    }

    volume {
      name                 = "logs"
      mount_path           = "/var/log"
      read_only            = false
      empty_dir            = {}
    }
  }

  diagnostics {
    log_analytics {
      workspace_id  = azurerm_log_analytics_workspace.main.workspace_id
      workspace_key = azurerm_log_analytics_workspace.main.primary_shared_key
    }
  }

  tags = var.tags

  depends_on = [
    azurerm_role_assignment.storage_blob_data_contributor
  ]
}
locals {
  tags = {
    project     = "crepro"
    environment = "dev"
    managed_by  = "terraform"
  }
}

# Unique suffix for globally-unique Azure names (Key Vault, Storage, ACR, Service Bus).
resource "random_string" "suffix" {
  length  = 6
  special = false
  upper   = false
}

resource "azurerm_resource_group" "dev" {
  name     = var.resource_group_name
  location = var.location
  tags     = local.tags
}

# --- Networking: private PostgreSQL + a VNet-integrated Container Apps environment ---

resource "azurerm_virtual_network" "dev" {
  name                = "vnet-crepro-dev"
  resource_group_name = azurerm_resource_group.dev.name
  location            = azurerm_resource_group.dev.location
  address_space       = ["10.20.0.0/16"]
  tags                = local.tags
}

resource "azurerm_subnet" "postgres" {
  name                 = "snet-postgres"
  resource_group_name  = azurerm_resource_group.dev.name
  virtual_network_name = azurerm_virtual_network.dev.name
  address_prefixes     = ["10.20.1.0/24"]
  # Azure attaches this automatically to a Postgres Flexible Server's
  # delegated subnet; declared explicitly so Terraform doesn't see drift and
  # try to remove it.
  service_endpoints = ["Microsoft.Storage"]

  delegation {
    name = "postgres-delegation"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# Sized /23 per Azure's Container Apps VNet-integration guidance (needs headroom
# for scale-out infrastructure, not just one IP per app).
resource "azurerm_subnet" "container_apps" {
  name                 = "snet-container-apps"
  resource_group_name  = azurerm_resource_group.dev.name
  virtual_network_name = azurerm_virtual_network.dev.name
  address_prefixes     = ["10.20.2.0/23"]

  delegation {
    name = "container-apps-delegation"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_private_dns_zone" "postgres" {
  name                = "privatelink.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.dev.name
  tags                = local.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "vnet-link-postgres"
  resource_group_name   = azurerm_resource_group.dev.name
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.dev.id
  tags                  = local.tags
}

# --- Key Vault ---

data "azurerm_client_config" "current" {}

resource "azurerm_key_vault" "dev" {
  name                       = "kv-crepro-dev-${random_string.suffix.result}"
  resource_group_name        = azurerm_resource_group.dev.name
  location                   = azurerm_resource_group.dev.location
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  rbac_authorization_enabled = true
  purge_protection_enabled   = false
  soft_delete_retention_days = 7
  tags                       = local.tags
}

# Grants whichever identity runs `terraform apply` (the GitHub Actions service
# principal in CI, the operator locally) permission to write the secrets below
# in the same apply, without a standing broad Key Vault role.
resource "azurerm_role_assignment" "kv_secrets_officer_deployer" {
  scope                = azurerm_key_vault.dev.id
  role_definition_name = "Key Vault Secrets Officer"
  principal_id         = data.azurerm_client_config.current.object_id
}

# --- PostgreSQL Flexible Server (private, VNet-integrated) ---

resource "azurerm_postgresql_flexible_server" "dev" {
  name                          = "psql-crepro-dev-${random_string.suffix.result}"
  resource_group_name           = azurerm_resource_group.dev.name
  location                      = azurerm_resource_group.dev.location
  version                       = "16"
  delegated_subnet_id           = azurerm_subnet.postgres.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres.id
  public_network_access_enabled = false
  administrator_login           = var.postgres_admin_login
  administrator_password        = var.postgres_admin_password
  storage_mb                    = 32768
  sku_name                      = "B_Standard_B1ms"
  # Azure picked this zone at create time since none was requested; pinned
  # explicitly so Terraform doesn't see drift and try to unset it.
  zone = "1"
  tags = local.tags

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres]
}

resource "azurerm_postgresql_flexible_server_database" "crepro" {
  name      = "crepro"
  server_id = azurerm_postgresql_flexible_server.dev.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

resource "azurerm_key_vault_secret" "postgres_admin_password" {
  name         = "postgres-admin-password"
  value        = var.postgres_admin_password
  key_vault_id = azurerm_key_vault.dev.id
  depends_on   = [azurerm_role_assignment.kv_secrets_officer_deployer]
}

resource "azurerm_key_vault_secret" "postgres_database_url" {
  name = "postgres-database-url"
  # Matches crepro_common.config.Settings' CREPRO_DATABASE_URL shape.
  value        = "postgresql://${var.postgres_admin_login}:${var.postgres_admin_password}@${azurerm_postgresql_flexible_server.dev.fqdn}:5432/${azurerm_postgresql_flexible_server_database.crepro.name}"
  key_vault_id = azurerm_key_vault.dev.id
  depends_on   = [azurerm_role_assignment.kv_secrets_officer_deployer]
}

# --- Storage (documents, blobs referenced by the document service) ---

resource "azurerm_storage_account" "dev" {
  name                     = "stcreprodev${random_string.suffix.result}"
  resource_group_name      = azurerm_resource_group.dev.name
  location                 = azurerm_resource_group.dev.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  min_tls_version          = "TLS1_2"
  tags                     = local.tags
}

resource "azurerm_storage_container" "documents" {
  name                  = "documents"
  storage_account_id    = azurerm_storage_account.dev.id
  container_access_type = "private"
}

# --- Container Registry ---

resource "azurerm_container_registry" "dev" {
  name                = "acrcreprodev${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.dev.name
  location            = azurerm_resource_group.dev.location
  sku                 = "Basic"
  admin_enabled       = false
  tags                = local.tags
}

# --- Container Apps environment (no apps yet: Day 14 deploys the services) ---

resource "azurerm_log_analytics_workspace" "dev" {
  name                = "log-crepro-dev-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.dev.name
  location            = azurerm_resource_group.dev.location
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = local.tags
}

resource "azurerm_container_app_environment" "dev" {
  name                       = "cae-crepro-dev"
  resource_group_name        = azurerm_resource_group.dev.name
  location                   = azurerm_resource_group.dev.location
  log_analytics_workspace_id = azurerm_log_analytics_workspace.dev.id
  infrastructure_subnet_id   = azurerm_subnet.container_apps.id
  tags                       = local.tags
}

# --- Service Bus (ADR-013): Standard namespace, erp-events topic only for now ---
# Subscriptions (e.g. the ERP adapter's) are added when that consumer exists, Day 11.

resource "azurerm_servicebus_namespace" "dev" {
  name                = "sb-crepro-dev-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.dev.name
  location            = azurerm_resource_group.dev.location
  sku                 = "Standard"
  tags                = local.tags
}

resource "azurerm_servicebus_topic" "erp_events" {
  name         = "erp-events"
  namespace_id = azurerm_servicebus_namespace.dev.id
}

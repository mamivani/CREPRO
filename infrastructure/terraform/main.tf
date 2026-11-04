# Azure deployment configuration using Terraform
# Infrastructure as Code for Day 14 deployment

terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

# Variables
variable "subscription_id" {
  description = "Azure subscription ID"
  type        = string
}

variable "resource_group_name" {
  description = "Azure resource group name"
  type        = string
  default     = "crepro-dev-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "eastus"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "container_registry_name" {
  description = "Container registry name"
  type        = string
  default     = "creprobuilddev"
}

variable "app_environment_name" {
  description = "Container App Environment name"
  type        = string
  default     = "crepro-dev-env"
}

variable "postgres_server_name" {
  description = "PostgreSQL server name"
  type        = string
  default     = "crepro-db-dev"
}

variable "erp_password" {
  description = "ERP API password"
  type        = string
  sensitive   = true
}

variable "postgres_password" {
  description = "PostgreSQL admin password"
  type        = string
  sensitive   = true
}

# Data source for current Azure account
data "azurerm_client_config" "current" {}

# Resource Group
resource "azurerm_resource_group" "crepro" {
  name     = var.resource_group_name
  location = var.location

  tags = {
    environment = var.environment
    project     = "CREPRO"
  }
}

# Log Analytics Workspace
resource "azurerm_log_analytics_workspace" "crepro" {
  name                = "crepro-logs-dev"
  location            = var.location
  resource_group_name = azurerm_resource_group.crepro.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = {
    environment = var.environment
  }
}

# Application Insights
resource "azurerm_application_insights" "crepro" {
  name                = "crepro-insights-dev"
  location            = var.location
  resource_group_name = azurerm_resource_group.crepro.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.crepro.id

  tags = {
    environment = var.environment
  }
}

# Container Registry
resource "azurerm_container_registry" "crepro" {
  name                = var.container_registry_name
  resource_group_name = azurerm_resource_group.crepro.name
  location            = var.location
  sku                 = "Standard"
  admin_enabled       = true

  tags = {
    environment = var.environment
  }
}

# PostgreSQL Server (Flexible Server)
resource "azurerm_postgresql_flexible_server" "crepro" {
  name                   = var.postgres_server_name
  resource_group_name    = azurerm_resource_group.crepro.name
  location               = var.location
  version                = "14"
  administrator_login    = "pgadmin"
  administrator_password = var.postgres_password
  storage_mb             = 32768
  sku_name               = "B_Standard_B2s"

  tags = {
    environment = var.environment
  }
}

# PostgreSQL Database
resource "azurerm_postgresql_flexible_server_database" "crepro" {
  name            = "crepro"
  server_id       = azurerm_postgresql_flexible_server.crepro.id
  charset         = "UTF8"
  collation       = "en_US.utf8"
}

# Container App Environment
resource "azurerm_container_app_environment" "crepro" {
  name                       = var.app_environment_name
  location                   = var.location
  resource_group_name        = azurerm_resource_group.crepro.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.crepro.id

  tags = {
    environment = var.environment
  }

  depends_on = [azurerm_log_analytics_workspace.crepro]
}

# Outputs
output "container_registry_url" {
  value       = azurerm_container_registry.crepro.login_server
  description = "Container registry URL"
}

output "database_host" {
  value       = azurerm_postgresql_flexible_server.crepro.fqdn
  description = "PostgreSQL server FQDN"
}

output "app_environment_id" {
  value       = azurerm_container_app_environment.crepro.id
  description = "Container App Environment ID"
}

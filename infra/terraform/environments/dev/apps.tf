# --- Day 14 Phase 3: service Container Apps, reconciliation jobs, Dapr components ---
# Everything here is gated on var.deploy_services so the foundation can be applied before images exist.

locals {
  deploy = var.deploy_services ? 1 : 0

  # service name -> container port (matches services/*/Dockerfile EXPOSE)
  services = {
    identity    = 8001
    tenant      = 8002
    property    = 8003
    lease       = 8004
    reservation = 8005
    payment     = 8006
    document    = 8007
    utility     = 8008
    maintenance = 8009
    reporting   = 8010
    erp_adapter = 8011
  }

  # Apps that publish or subscribe to erp-events (Dapr scopes on the pub/sub component).
  dapr_scopes = ["property", "erp-adapter"]
}

# --- Identity: one user-assigned identity pulls images from ACR and reads Key Vault ---

resource "azurerm_user_assigned_identity" "apps" {
  count               = local.deploy
  name                = "id-crepro-apps-dev"
  resource_group_name = azurerm_resource_group.dev.name
  location            = azurerm_resource_group.dev.location
  tags                = local.tags
}

resource "azurerm_role_assignment" "apps_acr_pull" {
  count                = local.deploy
  scope                = azurerm_container_registry.dev.id
  role_definition_name = "AcrPull"
  principal_id         = azurerm_user_assigned_identity.apps[0].principal_id
}

resource "azurerm_role_assignment" "apps_kv_secrets_user" {
  count                = local.deploy
  scope                = azurerm_key_vault.dev.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.apps[0].principal_id
}

# --- Secrets consumed by the apps (Key Vault is the only source; apps reference by secret id) ---

resource "azurerm_servicebus_namespace_authorization_rule" "apps" {
  count        = local.deploy
  name         = "crepro-apps"
  namespace_id = azurerm_servicebus_namespace.dev.id
  listen       = true
  send         = true
  manage       = true
}

resource "azurerm_key_vault_secret" "servicebus_connection_string" {
  count        = local.deploy
  name         = "servicebus-connection-string"
  value        = azurerm_servicebus_namespace_authorization_rule.apps[0].primary_connection_string
  key_vault_id = azurerm_key_vault.dev.id
  depends_on   = [azurerm_role_assignment.kv_secrets_officer_deployer]
}

resource "azurerm_storage_container" "dlq" {
  count                 = local.deploy
  name                  = "dlq-state"
  storage_account_id    = azurerm_storage_account.dev.id
  container_access_type = "private"
}

resource "azurerm_key_vault_secret" "storage_account_key" {
  count        = local.deploy
  name         = "storage-account-key"
  value        = azurerm_storage_account.dev.primary_access_key
  key_vault_id = azurerm_key_vault.dev.id
  depends_on   = [azurerm_role_assignment.kv_secrets_officer_deployer]
}

resource "azurerm_key_vault_secret" "erp_password" {
  count        = local.deploy
  name         = "erp-password"
  value        = var.erp_password
  key_vault_id = azurerm_key_vault.dev.id
  depends_on   = [azurerm_role_assignment.kv_secrets_officer_deployer]
}

# --- Dapr components on the shared Container Apps environment ---

resource "azurerm_container_app_environment_dapr_component" "pubsub" {
  count                        = local.deploy
  name                         = "pubsub"
  container_app_environment_id = azurerm_container_app_environment.dev.id
  component_type               = "pubsub.azure.servicebus.topics"
  version                      = "v1"
  scopes                       = local.dapr_scopes

  metadata {
    name        = "connectionString"
    secret_name = "servicebus-connection-string"
  }

  secret {
    name  = "servicebus-connection-string"
    value = azurerm_servicebus_namespace_authorization_rule.apps[0].primary_connection_string
  }
}

# DLQ store used by erp_adapter's DaprDLQRepo (push.py via DAPR_STATE_STORE=dlq-store).
resource "azurerm_container_app_environment_dapr_component" "dlq_store" {
  count                        = local.deploy
  name                         = "dlq-store"
  container_app_environment_id = azurerm_container_app_environment.dev.id
  component_type               = "state.azure.blobstorage"
  version                      = "v1"
  scopes                       = ["erp-adapter"]

  metadata {
    name  = "accountName"
    value = azurerm_storage_account.dev.name
  }

  metadata {
    name  = "containerName"
    value = azurerm_storage_container.dlq[0].name
  }

  metadata {
    name        = "accountKey"
    secret_name = "storage-account-key"
  }

  secret {
    name  = "storage-account-key"
    value = azurerm_storage_account.dev.primary_access_key
  }
}

# --- Service Container Apps (11 services, one app each) ---

resource "azurerm_container_app" "service" {
  for_each = var.deploy_services ? local.services : {}

  name                         = "ca-crepro-${replace(each.key, "_", "-")}"
  resource_group_name          = azurerm_resource_group.dev.name
  container_app_environment_id = azurerm_container_app_environment.dev.id
  revision_mode                = "Single"
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps[0].id]
  }

  registry {
    server   = azurerm_container_registry.dev.login_server
    identity = azurerm_user_assigned_identity.apps[0].id
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.postgres_database_url.versionless_id
    identity            = azurerm_user_assigned_identity.apps[0].id
  }

  secret {
    name                = "appinsights-connection-string"
    key_vault_secret_id = azurerm_key_vault_secret.appinsights_connection_string[0].versionless_id
    identity            = azurerm_user_assigned_identity.apps[0].id
  }

  dynamic "secret" {
    for_each = each.key == "erp_adapter" ? [1] : []
    content {
      name                = "erp-password"
      key_vault_secret_id = azurerm_key_vault_secret.erp_password[0].versionless_id
      identity            = azurerm_user_assigned_identity.apps[0].id
    }
  }

  dapr {
    app_id       = replace(each.key, "_", "-")
    app_port     = each.value
    app_protocol = "http"
  }

  ingress {
    external_enabled = var.services_external_ingress
    target_port      = each.value
    transport        = "http"

    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }

  template {
    min_replicas = 1
    max_replicas = 2

    container {
      name   = each.key
      image  = "${azurerm_container_registry.dev.login_server}/crepro-${replace(each.key, "_", "-")}:${var.image_tag}"
      cpu    = 0.25
      memory = "0.5Gi"

      env {
        name  = "CREPRO_ENVIRONMENT"
        value = "dev"
      }

      env {
        name        = "CREPRO_DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name        = "APPLICATIONINSIGHTS_CONNECTION_STRING"
        secret_name = "appinsights-connection-string"
      }

      dynamic "env" {
        for_each = each.key == "erp_adapter" ? [1] : []
        content {
          name  = "ERP_BASE_URL"
          value = var.erp_base_url
        }
      }

      dynamic "env" {
        for_each = each.key == "erp_adapter" ? [1] : []
        content {
          name  = "ERP_USERNAME"
          value = var.erp_username
        }
      }

      dynamic "env" {
        for_each = each.key == "erp_adapter" ? [1] : []
        content {
          name        = "ERP_PASSWORD"
          secret_name = "erp-password"
        }
      }

      dynamic "env" {
        for_each = each.key == "erp_adapter" ? [1] : []
        content {
          name  = "DAPR_STATE_STORE"
          value = "dlq-store"
        }
      }

      liveness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = each.value
      }

      readiness_probe {
        transport = "HTTP"
        path      = "/health"
        port      = each.value
      }
    }
  }

  lifecycle {
    precondition {
      condition     = each.key != "erp_adapter" || (var.erp_base_url != "" && var.erp_password != "")
      error_message = "erp_base_url and erp_password must be set when deploy_services is true (the ERP adapter would otherwise silently fall back to mocks)."
    }
    precondition {
      condition     = var.dev_tenant_id != ""
      error_message = "dev_tenant_id must be set when deploy_services is true (the reconciliation jobs need TENANT_ID)."
    }
  }

  depends_on = [
    azurerm_role_assignment.apps_acr_pull,
    azurerm_role_assignment.apps_kv_secrets_user,
    azurerm_container_app_environment_dapr_component.pubsub,
    azurerm_container_app_environment_dapr_component.dlq_store,
    azurerm_key_vault_secret.erp_password,
  ]
}

# --- Reconciliation jobs (ADR: Container Apps Jobs on cron, no HTTP ingress) ---
# Jobs do not run a Dapr sidecar, so DaprDLQRepo cannot reach dlq-store from here;
# DLQ replay is a known gap, see DAY14_DEPLOYMENT_GUIDE.md.

locals {
  reconciliation_jobs = {
    incremental = { mode = "INCREMENTAL", cron = "*/15 * * * *" }
    full        = { mode = "FULL", cron = "0 2 * * *" }
  }
}

resource "azurerm_container_app_job" "reconciliation" {
  for_each = var.deploy_services ? local.reconciliation_jobs : {}

  name                         = "job-crepro-recon-${each.key}"
  resource_group_name          = azurerm_resource_group.dev.name
  location                     = azurerm_resource_group.dev.location
  container_app_environment_id = azurerm_container_app_environment.dev.id
  replica_timeout_in_seconds   = 1800
  replica_retry_limit          = 1
  tags                         = local.tags

  identity {
    type         = "UserAssigned"
    identity_ids = [azurerm_user_assigned_identity.apps[0].id]
  }

  registry {
    server   = azurerm_container_registry.dev.login_server
    identity = azurerm_user_assigned_identity.apps[0].id
  }

  schedule_trigger_config {
    cron_expression          = each.value.cron
    parallelism              = 1
    replica_completion_count = 1
  }

  secret {
    name                = "database-url"
    key_vault_secret_id = azurerm_key_vault_secret.postgres_database_url.versionless_id
    identity            = azurerm_user_assigned_identity.apps[0].id
  }

  secret {
    name                = "erp-password"
    key_vault_secret_id = azurerm_key_vault_secret.erp_password[0].versionless_id
    identity            = azurerm_user_assigned_identity.apps[0].id
  }

  template {
    container {
      name    = "erp-reconciliation"
      image   = "${azurerm_container_registry.dev.login_server}/crepro-erp-reconciliation:${var.image_tag}"
      command = ["python", "-m", "crepro_erp_reconciliation.main"]
      cpu     = 0.25
      memory  = "0.5Gi"

      env {
        name  = "RECONCILIATION_MODE"
        value = each.value.mode
      }

      env {
        name  = "TENANT_ID"
        value = var.dev_tenant_id
      }

      env {
        name  = "ERP_BASE_URL"
        value = var.erp_base_url
      }

      env {
        name  = "ERP_USERNAME"
        value = var.erp_username
      }

      env {
        name        = "ERP_PASSWORD"
        secret_name = "erp-password"
      }

      env {
        name        = "DATABASE_URL"
        secret_name = "database-url"
      }

      env {
        name  = "ADAPTER_SERVICE_URL"
        value = "https://${azurerm_container_app.service["erp_adapter"].ingress[0].fqdn}"
      }
    }
  }
}

# --- Day 14 Phase 5: Application Insights (workspace-based) and alerting ---

resource "azurerm_application_insights" "dev" {
  name                = "appi-crepro-dev"
  resource_group_name = azurerm_resource_group.dev.name
  location            = azurerm_resource_group.dev.location
  workspace_id        = azurerm_log_analytics_workspace.dev.id
  application_type    = "web"
  tags                = local.tags
}

resource "azurerm_key_vault_secret" "appinsights_connection_string" {
  count        = local.deploy
  name         = "appinsights-connection-string"
  value        = azurerm_application_insights.dev.connection_string
  key_vault_id = azurerm_key_vault.dev.id
  depends_on   = [azurerm_role_assignment.kv_secrets_officer_deployer]
}

resource "azurerm_monitor_action_group" "dev" {
  count               = var.alert_email == "" ? 0 : 1
  name                = "ag-crepro-dev"
  resource_group_name = azurerm_resource_group.dev.name
  short_name          = "crepro-dev"
  tags                = local.tags

  email_receiver {
    name          = "oncall"
    email_address = var.alert_email
  }
}

resource "azurerm_monitor_metric_alert" "failed_requests" {
  count               = var.alert_email == "" ? 0 : 1
  name                = "alert-crepro-dev-failed-requests"
  resource_group_name = azurerm_resource_group.dev.name
  scopes              = [azurerm_application_insights.dev.id]
  description         = "Failed HTTP requests across CREPRO services exceeded threshold in 15 minutes."
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT15M"
  tags                = local.tags

  criteria {
    metric_namespace = "microsoft.insights/components"
    metric_name      = "requests/failed"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 10
  }

  action {
    action_group_id = azurerm_monitor_action_group.dev[0].id
  }
}

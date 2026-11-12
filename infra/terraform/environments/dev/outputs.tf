output "resource_group_name" {
  value = azurerm_resource_group.dev.name
}

output "key_vault_name" {
  value = azurerm_key_vault.dev.name
}

output "postgres_fqdn" {
  value = azurerm_postgresql_flexible_server.dev.fqdn
}

output "storage_account_name" {
  value = azurerm_storage_account.dev.name
}

output "container_registry_login_server" {
  value = azurerm_container_registry.dev.login_server
}

output "container_app_environment_id" {
  value = azurerm_container_app_environment.dev.id
}

output "container_app_environment_default_domain" {
  description = "Stable once the environment exists; lets the deploy workflow compute backend FQDNs (ca-crepro-<service>.<this>) to bake into the web image before deploy_services=true has ever run."
  value       = azurerm_container_app_environment.dev.default_domain
}

output "web_url" {
  description = "Public URL of the frontend Container App (empty until deploy_services = true)."
  value       = try("https://${azurerm_container_app.web[0].ingress[0].fqdn}", "")
}

output "identity_health_url" {
  description = "Identity service health endpoint, for the deploy workflow's smoke test (empty until deploy_services = true)."
  value       = try("https://${azurerm_container_app.service["identity"].ingress[0].fqdn}/health", "")
}

output "property_health_url" {
  description = "Property service health endpoint, for the deploy workflow's smoke test (empty until deploy_services = true)."
  value       = try("https://${azurerm_container_app.service["property"].ingress[0].fqdn}/health", "")
}

output "servicebus_namespace_name" {
  value = azurerm_servicebus_namespace.dev.name
}

output "servicebus_erp_events_topic_id" {
  value = azurerm_servicebus_topic.erp_events.id
}

output "service_urls" {
  description = "Ingress FQDNs of the service Container Apps (empty until deploy_services = true)."
  value       = { for name, app in azurerm_container_app.service : name => app.ingress[0].fqdn }
}

output "application_insights_connection_string" {
  value     = azurerm_application_insights.dev.connection_string
  sensitive = true
}

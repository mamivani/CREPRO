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

output "servicebus_namespace_name" {
  value = azurerm_servicebus_namespace.dev.name
}

output "servicebus_erp_events_topic_id" {
  value = azurerm_servicebus_topic.erp_events.id
}

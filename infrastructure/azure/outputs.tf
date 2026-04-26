output "resource_group_name" {
  value       = azurerm_resource_group.datalake.name
  description = "Azure Resource Group name"
}

output "storage_account_name" {
  value       = azurerm_storage_account.datalake.name
  description = "Primary Data Lake storage account name"
}

output "storage_account_primary_blob_endpoint" {
  value       = azurerm_storage_account.datalake.primary_blob_endpoint
  description = "Primary blob endpoint for ADLS Gen2"
}

output "bronze_container_url" {
  value       = "https://${azurerm_storage_account.datalake.name}.blob.core.windows.net/${azurerm_storage_container.bronze.name}"
  description = "Bronze layer container URL"
}

output "silver_container_url" {
  value       = "https://${azurerm_storage_account.datalake.name}.blob.core.windows.net/${azurerm_storage_container.silver.name}"
  description = "Silver layer container URL"
}

output "gold_container_url" {
  value       = "https://${azurerm_storage_account.datalake.name}.blob.core.windows.net/${azurerm_storage_container.gold.name}"
  description = "Gold layer container URL"
}

output "function_app_name" {
  value       = azurerm_function_app.ingestor.name
  description = "Azure Functions app name"
}

output "function_app_url" {
  value       = azurerm_function_app.ingestor.default_host_name
  description = "Azure Functions app URL"
}

output "data_factory_name" {
  value       = azurerm_data_factory.datalake.name
  description = "Azure Data Factory name"
}

output "key_vault_name" {
  value       = azurerm_key_vault.datalake.name
  description = "Azure Key Vault name for secrets management"
}
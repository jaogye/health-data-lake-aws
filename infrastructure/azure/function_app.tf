# Azure Functions App (replaces AWS Lambda)
resource "azurerm_storage_account" "function_app" {
  name                      = "safncdatalake${var.env}${ substr(uuid(), 0, 4)}"
  resource_group_name       = azurerm_resource_group.datalake.name
  location                  = azurerm_resource_group.datalake.location
  account_tier              = "Standard"
  account_replication_type   = "LRS"
  enable_https_traffic_only  = true
}

resource "azurerm_app_service_plan" "function" {
  name                = "asp-health-datalake-${var.env}"
  resource_group_name = azurerm_resource_group.datalake.name
  location            = azurerm_resource_group.datalake.location
  kind                = "Linux"
  reserved            = true

  sku {
    tier = "Premium"
    size = "Y1"
  }
}

resource "azurerm_function_app" "ingestor" {
  name                       = "func-health-datalake-ingestor-${var.env}"
  resource_group_name        = azurerm_resource_group.datalake.name
  location                   = azurerm_resource_group.datalake.location
  app_service_plan_id        = azurerm_app_service_plan.function.id
  storage_account_name       = azurerm_storage_account.function_app.name
  storage_account_access_key = azurerm_storage_account.function_app.primary_access_key
  functions_version          = "~4"
  os_type                    = "linux"

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME = "python"
    BRONZE_CONTAINER_NAME     = azurerm_storage_container.bronze.name
    STORAGE_ACCOUNT_NAME      = azurerm_storage_account.datalake.name
    ENV                       = var.env
  }

  site_config {
    linux_fx_version = "Python|3.11"
    ftps_state       = "Disabled"
    min_tls_version  = "1.2"
  }

  identity {
    type = "SystemAssigned"
  }
}

# Grant Function App access to Data Lake
resource "azurerm_role_assignment" "function_storage" {
  scope              = azurerm_storage_account.datalake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id       = azurerm_function_app.ingestor.identity[0].principal_id
}

# Timer Trigger (replaces EventBridge) - daily at 02:00 UTC
# Azure Functions timer trigger is defined in function code (function.json)
# Schedule: 0 2 * * * (cron expression)
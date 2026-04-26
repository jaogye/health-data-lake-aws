# Azure Data Factory (replaces AWS Glue)
resource "azurerm_data_factory" "datalake" {
  name                = "adf-health-datalake-${var.env}"
  resource_group_name = azurerm_resource_group.datalake.name
  location            = azurerm_resource_group.datalake.location

  identity {
    type = "SystemAssigned"
  }
}

# ADF Linked Service: ADLS Gen2
resource "azurerm_data_factory_linked_service_data_lake_storage_gen2" "datalake" {
  name                = "ls_adls_${var.env}"
  data_factory_id     = azurerm_data_factory.datalake.id
  storage_account_key = azurerm_storage_account.datalake.primary_access_key
  url                = "https://${azurerm_storage_account.datalake.name}.dfs.core.windows.net"

  parameters = {
    bronze_container = azurerm_storage_container.bronze.name
    silver_container = azurerm_storage_container.silver.name
    gold_container   = azurerm_storage_container.gold.name
  }
}

# Pipeline: Bronze to Silver
resource "azurerm_data_factory_pipeline" "bronze_to_silver" {
  name            = "pl_bronze_to_silver_${var.env}"
  data_factory_id = azurerm_data_factory.datalake.id
  description     = "Ingest raw health data and transform to cleaned Silver layer"

  parameters = {
    bronzePath = "~//bronze"
    silverPath = "~//silver"
  }

  activities = [
    {
      name = "BronzeToSilver"
      type = "DatabricksSparkPython"
      type_properties = {
        python_file = "abfss://scripts@${azurerm_storage_account.datalake.name}.dfs.core.windows.net/glue_jobs/bronze_to_silver.py"
        executor_memory = "28GB"
        executor_cores = 4
        runtime_engine = "Standard"
      }
      linked_service_name = azurerm_data_factory_linked_service_data_lake_storage_gen2.datalake.name
    }
  ]
}

# Pipeline: Silver to Gold
resource "azurerm_data_factory_pipeline" "silver_to_gold" {
  name            = "pl_silver_to_gold_${var.env}"
  data_factory_id = azurerm_data_factory.datalake.id
  description     = "Aggregate Silver data to analytics-ready Gold layer"

  parameters = {
    silverPath = "~//silver"
    goldPath   = "~//gold"
  }

  activities = [
    {
      name = "SilverToGold"
      type = "DatabricksSparkPython"
      type_properties = {
        python_file = "abfss://scripts@${azurerm_storage_account.datalake.name}.dfs.core.windows.net/glue_jobs/silver_to_gold.py"
        executor_memory = "28GB"
        executor_cores = 4
        runtime_engine = "Standard"
      }
      linked_service_name = azurerm_data_factory_linked_service_data_lake_storage_gen2.datalake.name
    }
  ]
}

# Trigger: Daily at 02:00 UTC
resource "azurerm_data_factory_trigger_schedule" "daily_ingestion" {
  name            = "trig_daily_${var.env}"
  data_factory_id = azurerm_data_factory.datalake.id
  pipeline_name   = azurerm_data_factory_pipeline.bronze_to_silver.name

  schedule {
    frequency = "Day"
    interval  = 1
    at        = ["02:00:00"]
  }
}

# Grant ADF access to Storage
resource "azurerm_role_assignment" "adf_storage" {
  scope              = azurerm_storage_account.datalake.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id       = azurerm_data_factory.datalake.identity[0].principal_id
}
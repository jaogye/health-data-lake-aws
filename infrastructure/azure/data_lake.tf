# ADLS Gen2 Containers: Bronze / Silver / Gold
resource "azurerm_storage_container" "bronze" {
  name                  = "bronze"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "silver" {
  name                  = "silver"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "gold" {
  name                  = "gold"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

resource "azurerm_storage_container" "scripts" {
  name                  = "scripts"
  storage_account_name  = azurerm_storage_account.datalake.name
  container_access_type = "private"
}

# Upload PySpark jobs to scripts container
resource "azurerm_storage_blob" "bronze_to_silver" {
  name                   = "glue_jobs/bronze_to_silver.py"
  storage_account_name   = azurerm_storage_account.datalake.name
  storage_container_name = azurerm_storage_container.scripts.name
  type                   = "Block"
  source                 = "${path.root}/../../transformation/glue_jobs/bronze_to_silver.py"
  content_type           = "application/x-python"
}

resource "azurerm_storage_blob" "silver_to_gold" {
  name                   = "glue_jobs/silver_to_gold.py"
  storage_account_name   = azurerm_storage_account.datalake.name
  storage_container_name = azurerm_storage_container.scripts.name
  type                   = "Block"
  source                 = "${path.root}/../../transformation/glue_jobs/silver_to_gold.py"
  content_type           = "application/x-python"
}

# Data Lake Gen2 (hierarchical namespace) - enabled by default in ADLS Gen2
# Partitioning strategy mirrors AWS S3: source/year/month/day
terraform {
  required_version = ">= 1.5"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
}

provider "azurerm" {
  features {}
  skip_provider_registration = true
}

# Azure Resource Group
resource "azurerm_resource_group" "datalake" {
  name     = "rg-health-datalake-${var.env}"
  location = var.azure_location

  tags = {
    Project     = "health-data-lake"
    Environment = var.env
    ManagedBy   = "terraform"
    Owner       = "data-engineering"
  }
}

# Azure Key Vault for secrets and keys
resource "azurerm_key_vault" "datalake" {
  name                        = "kv-health-datalake-${var.env}"
  location                    = azurerm_resource_group.datalake.location
  resource_group_name         = azurerm_resource_group.datalake.name
  sku_name                    = "standard"
  tenant_id                   = data.azurerm_client_config.current.tenant_id
  soft_delete_retention_days  = 7
  purge_protection_enabled    = false

  access_policy {
    tenant_id = data.azurerm_client_config.current.tenant_id
    object_id = data.azurerm_client_config.current.object_id
    key_permissions = [
      "Get", "List", "Create", "Delete", "WrapKey", "UnwrapKey", "GetRotationPolicy"
    ]
    secret_permissions = [
      "Get", "List", "Set", "Delete"
    ]
    storage_permissions = [
      "Get", "List"
    ]
  }
}

# Storage Account encryption key
resource "azurerm_storage_account" "datalake" {
  name                      = "stadatalake${var.env}${ substr(uuid(), 0, 4)}"
  resource_group_name       = azurerm_resource_group.datalake.name
  location                  = azurerm_resource_group.datalake.location
  account_tier              = "Standard"
  account_replication_type  = "LRS"
  enable_https_traffic_only  = true
  min_tls_version           = "TLS1_2"

  identity {
    type = "SystemAssigned"
  }

  blob_properties {
    versioning_enabled  = true
    change_feed_enabled = true

    lifecycle_management_policy {
      rule {
        name    = "expire-bronze"
        enabled = true
        filters {
          blob_types   = ["blockBlob"]
          prefix_match = ["bronze/"]
        }
        actions {
          base_blob {
            delete_after_days_since_modification_greater_than = 90
          }
        }
      }
      rule {
        name    = "expire-silver-gold"
        enabled = true
        filters {
          blob_types   = ["blockBlob"]
          prefix_match = ["silver/", "gold/"]
        }
        actions {
          base_blob {
            delete_after_days_since_modification_greater_than = 365
          }
        }
      }
    }
  }

  tags = {
    Project     = "health-data-lake"
    Environment = var.env
  }
}

data "azurerm_client_config" "current" {}
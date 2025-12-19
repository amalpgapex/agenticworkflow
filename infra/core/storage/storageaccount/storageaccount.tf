resource "azurecaf_name" "storage_account_name" {
  name          = var.name
  resource_type = "azurerm_storage_account"
  random_length = 0
  clean_input   = true
}

resource "azurerm_storage_account" "storage" {
  name                     = azurecaf_name.storage_account_name.result
  resource_group_name      = var.resource_group_name
  location                 = var.location
  account_tier             = var.account_tier
  account_replication_type = var.account_replication_type
  account_kind             = var.account_kind
  
  min_tls_version          = "TLS1_2"
  enable_https_traffic_only = true

  blob_properties {
    delete_retention_policy {
      days = var.delete_retention_days
    }
    container_delete_retention_policy {
      days = var.delete_retention_days
    }
  }

  tags = var.tags
}

resource "azurerm_storage_container" "container" {
  for_each              = toset(var.containers)
  name                  = each.value
  storage_account_name  = azurerm_storage_account.storage.name
  container_access_type = var.container_access_type
}

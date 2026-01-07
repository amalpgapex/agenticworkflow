locals {
  tags                         = { azd-env-name : var.environment_name }
  sha                          = base64encode(sha256("${var.environment_name}${var.location}${data.azurerm_client_config.current.subscription_id}"))
  resource_token               = substr(replace(lower(local.sha), "[^A-Za-z0-9_]", ""), 0, 13)
}

resource "azurecaf_name" "rg_name" {
  name          = var.environment_name
  resource_type = "azurerm_resource_group"
  random_length = 0
  clean_input   = true
}

# Deploy resource group
resource "azurerm_resource_group" "rg" {
  name     = azurecaf_name.rg_name.result
  location = var.location
  // Tag the resource group with the azd environment name
  // This should also be applied to all resources created in this module
  tags = { azd-env-name : var.environment_name }
}

# Add resources to be provisioned below.
# To learn more, https://developer.hashicorp.com/terraform/tutorials/azure-get-started/azure-change
# Note that a tag:
#   azd-service-name: "<service name in azure.yaml>"
# should be applied to targeted service host resources, such as:
#  azurerm_linux_web_app, azurerm_windows_web_app for appservice
#  azurerm_function_app for function

# Deploy storage account with blob container
module "storage_account" {
  source  = "Azure/avm-res-storage-storageaccount/azurerm"
  version = "0.6.4"

  account_replication_type          = "LRS"
  location                          = var.location
  name                              = "${var.environment_name}sa"
  resource_group_name               = azurerm_resource_group.rg.name
  infrastructure_encryption_enabled = true

  containers = {
    demo = {
      name                  = "documents"
      container_access_type = "private"
    }
  }  
  
  tags                                = local.tags
}

# Microsoft Foundry (Cognitive Services AIServices) account + single project
module "foundry" {
  source              = "./core/ai/foundry"
  name                = "${var.environment_name}foundry"
  project_name        = "default"
  location            = var.location
  resource_group_id   = azurerm_resource_group.rg.id
  tags                = local.tags
}

# Deploy Cosmos DB account with single MongoDB database

module "azure_cosmos_db" {
  source              = "Azure/cosmosdb/azurerm"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  cosmos_account_name = "${var.environment_name}cosmosdb"
  cosmos_api          = "sql"
  sql_dbs             = {
    one = {
      db_name = "InKCatalystNextGenDB"
      db_throughput = 400
      db_max_throughput = null
    }
  }
  sql_db_containers   = {
      one = {
        container_name           = "Projects"
        db_name                  = "InKCatalystNextGenDB"
        partition_key_path       = "/CreatedBy"
        partition_key_version    = 2
        container_throughout     = 400
        container_max_throughput = null
        default_ttl = null 
        analytical_storage_ttl = null 
        indexing_policy_settings = {
          sql_indexing_mode = "consistent"
          sql_included_path = "/*"
          sql_excluded_path = null
          composite_indexes = {
            compositeindexone = {
              indexes = [
                {
                  path  = "/container/name"
                  order = "Ascending"
                },
                {
                  path  = "/container/id"
                  order = "Ascending"
                }
              ]
            }
          }
          spatial_indexes = {
            spatialindexone = {
              path = "/*"
            }
          }
        }
        sql_unique_key = ["/container/id"]
        conflict_resolution_policy = null 
      }
      one = {
        container_name           = "Workflows"
        db_name                  = "InKCatalystNextGenDB"
        partition_key_path       = "/CreatedBy"
        partition_key_version    = 2
        container_throughout     = 400
        container_max_throughput = null
        default_ttl = null 
        analytical_storage_ttl = null 
        indexing_policy_settings = {
          sql_indexing_mode = "consistent"
          sql_included_path = "/*"
          sql_excluded_path = null
          composite_indexes = {
            compositeindexone = {
              indexes = [
                {
                  path  = "/container/name"
                  order = "Ascending"
                },
                {
                  path  = "/container/id"
                  order = "Ascending"
                }
              ]
            }
          }
          spatial_indexes = {
            spatialindexone = {
              path = "/*"
            }
          }
        }
        sql_unique_key = ["/container/id"]
        conflict_resolution_policy = null 
      }      
  }
  depends_on = [
    azurerm_resource_group.rg
  ]
}

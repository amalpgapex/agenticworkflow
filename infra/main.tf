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
module "storage" {
  source              = "./core/storage/storageaccount"
  name                = "${var.environment_name}sa"
  location            = var.location
  resource_group_name = azurerm_resource_group.rg.name
  account_tier        = "Standard"
  account_replication_type = "LRS"
  containers          = ["data"]
  tags                = local.tags
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
module "cosmos" {
  source         = "./core/database/cosmos"
  location       = var.location
  rg_name        = azurerm_resource_group.rg.name
  resource_token = local.resource_token
  tags           = local.tags
}

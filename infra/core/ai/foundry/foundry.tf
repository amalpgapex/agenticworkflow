# Microsoft Foundry account (Cognitive Services - AIServices)
# Using AzAPI to ensure latest API support for Foundry properties

resource "azapi_resource" "foundry_account" {
  type      = "Microsoft.CognitiveServices/accounts@2025-10-01-preview"
  name      = var.name
  parent_id = var.resource_group_id
  location  = var.location

  body = {
    kind = "AIServices"
    properties = {
      allowProjectManagement       = true
      publicNetworkAccess          = "Enabled"
      restrictOutboundNetworkAccess = false
      disableLocalAuth              = false
      # Set a default project name; the platform will manage creation/association
      defaultProject               = var.project_name
      associatedProjects           = [var.project_name]
    }
    sku = {
      name = "S0"
      tier = "Standard"
    }
  }

  tags = var.tags
}

# Attempt to explicitly create the Foundry project child resource for clarity
# If the API version changes, this may need to be adjusted.
resource "azapi_resource" "foundry_project" {
  type      = "Microsoft.CognitiveServices/accounts/projects@2025-10-01-preview"
  name      = var.project_name
  parent_id = azapi_resource.foundry_account.id
  location  = var.location

  # Minimal body; properties can be extended if required in your subscription
  body = {
    properties = {
      # isDefault is implicit via account.defaultProject; include if required
      # isDefault = true
    }
  }
}

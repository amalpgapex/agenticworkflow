output "foundry_account_id" {
  description = "Resource ID of the Foundry (Cognitive Services) account"
  value       = azapi_resource.foundry_account.id
}

output "foundry_project_name" {
  description = "Name of the Foundry project"
  value       = var.project_name
}

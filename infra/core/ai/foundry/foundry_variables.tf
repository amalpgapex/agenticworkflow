variable "name" {
  description = "Name of the Microsoft Foundry (Cognitive Services) account"
  type        = string
}

variable "project_name" {
  description = "Name of the Foundry project to create/set as default"
  type        = string
}

variable "location" {
  description = "Azure region for the Foundry account"
  type        = string
}

variable "resource_group_id" {
  description = "Resource group ID to deploy the Foundry account under"
  type        = string
}

variable "tags" {
  description = "Tags to apply to the Foundry account"
  type        = map(string)
  default     = {}
}

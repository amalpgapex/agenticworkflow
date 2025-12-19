variable "name" {
  description = "The name of the storage account"
  type        = string
}

variable "location" {
  description = "The Azure region where the storage account will be deployed"
  type        = string
}

variable "resource_group_name" {
  description = "The name of the resource group"
  type        = string
}

variable "account_tier" {
  description = "The storage account tier"
  type        = string
  default     = "Standard"
}

variable "account_replication_type" {
  description = "The replication type for the storage account"
  type        = string
  default     = "LRS"
}

variable "account_kind" {
  description = "The kind of storage account"
  type        = string
  default     = "StorageV2"
}

variable "containers" {
  description = "List of container names to create"
  type        = list(string)
  default     = []
}

variable "container_access_type" {
  description = "The access level for the containers"
  type        = string
  default     = "private"
}

variable "delete_retention_days" {
  description = "Number of days to retain deleted blobs"
  type        = number
  default     = 7
}

variable "tags" {
  description = "Tags to apply to the storage account"
  type        = map(string)
  default     = {}
}

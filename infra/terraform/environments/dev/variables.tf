variable "resource_group_name" {
  description = "Name of the Dev resource group."
  type        = string
  default     = "rg-crepro-dev"
}

variable "location" {
  description = "Primary Azure region (spec Vol 1/Vol 4: South Central US primary, Central US DR secondary)."
  type        = string
  default     = "southcentralus"
}

variable "postgres_admin_login" {
  description = "PostgreSQL Flexible Server administrator login."
  type        = string
  default     = "creproadmin"
}

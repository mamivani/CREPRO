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

variable "deploy_services" {
  description = "Deploy the service Container Apps, reconciliation jobs and Dapr components. Images must already exist in ACR (see DAY14_DEPLOYMENT_GUIDE.md)."
  type        = bool
  default     = false
}

variable "image_tag" {
  description = "Tag of the crepro-<service> images in ACR to deploy."
  type        = string
  default     = "latest"
}

variable "services_external_ingress" {
  description = "Expose service Container Apps on public ingress (needed for smoke tests from outside the environment)."
  type        = bool
  default     = true
}

variable "erp_base_url" {
  description = "Base URL of the ERPNext instance (ERP_BASE_URL). Leave empty to use the in-environment erp_stub (internal FQDN)."
  type        = string
  default     = ""
}

variable "erp_username" {
  description = "ERPNext API username (ERP_USERNAME)."
  type        = string
  default     = "Administrator"
}

variable "erp_password" {
  description = "ERPNext API password. Pass via TF_VAR_erp_password; stored in Key Vault as erp-password. Required when deploy_services is true."
  type        = string
  default     = ""
  sensitive   = true
}

variable "alert_email" {
  description = "Email address for failed-request alerts. Leave empty to skip creating the action group and alert."
  type        = string
  default     = ""
}

variable "dev_tenant_id" {
  description = "Tenant ID the reconciliation jobs scan (TENANT_ID). Required when deploy_services is true."
  type        = string
  default     = ""
}

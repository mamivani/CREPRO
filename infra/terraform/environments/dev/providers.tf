# Terraform and provider versions for the Dev environment (ADR-009: Terraform-managed
# infrastructure only, no portal-created resources).

terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  # Non-secret backend settings (account/container/key) are supplied at
  # `terraform init -backend-config=...` time from backend.hcl, so this file
  # has no environment-specific values hardcoded and can be reused if a second
  # environment (staging/prod) is added later. Authenticates via Azure AD
  # (OIDC in CI, the operator's `az login` locally) rather than a storage
  # account key, per Vol 5 S16: "No secrets in pipelines".
  backend "azurerm" {
    use_azuread_auth = true
  }
}

provider "azurerm" {
  features {
    key_vault {
      # Dev only: lets `terraform destroy` fully remove a Key Vault instead of
      # leaving it soft-deleted and blocking a same-name recreate.
      purge_soft_delete_on_destroy = true
    }
  }

  # GitHub Actions authenticates via OIDC federated credentials (no client
  # secret stored anywhere, see the AZURE_CLIENT_ID/AZURE_TENANT_ID/
  # AZURE_SUBSCRIPTION_ID repo secrets and infra/terraform/environments/dev's
  # three federated credentials: github-main, github-develop, github-pull-request).
  use_oidc = true
}

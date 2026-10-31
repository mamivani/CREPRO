# Non-secret backend configuration, passed to `terraform init -backend-config=backend.hcl`.
# Bootstrapped once outside Terraform itself (the chicken-and-egg problem: Terraform
# needs a backend to exist before it can manage anything), see the Day 3 notes in
# docs/plan/15-day-plan-solo.md.
resource_group_name  = "rg-crepro-tfstate"
storage_account_name = "creprotfstate"
container_name       = "tfstate"
key                  = "dev.terraform.tfstate"

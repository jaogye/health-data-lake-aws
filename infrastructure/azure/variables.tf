variable "azure_location" {
  description = "Azure region to deploy resources"
  type        = string
  default     = "westeurope"  # West Europe - closest to Belgium
}

variable "env" {
  description = "Deployment environment (dev, staging, prod)"
  type        = string
  default     = "dev"
  validation {
    condition     = contains(["dev", "staging", "prod"], var.env)
    error_message = "env must be one of: dev, staging, prod"
  }
}
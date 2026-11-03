variable "subscription_id" {
  type        = string
  description = "Explicit subscription selection; no default prevents accidental deployment."
  validation {
    condition     = can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", var.subscription_id))
    error_message = "Supply the intended Azure subscription UUID."
  }
}

variable "prefix" {
  type    = string
  default = "anukumar-lab"
  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,19}$", var.prefix))
    error_message = "Use 3-20 lowercase letters, digits or hyphens, beginning with a letter."
  }
}

variable "environment" {
  type    = string
  default = "dev"
  validation {
    condition     = contains(["dev", "test"], var.environment)
    error_message = "This demonstration supports dev or test, not production."
  }
}

variable "location" {
  type    = string
  default = "centralindia"
}

variable "enable_aks" {
  type        = bool
  default     = false
  description = "Opt-in: AKS creates billable compute and networking."
}

variable "aks_admin_group_object_ids" {
  type        = list(string)
  default     = []
  description = "Existing Entra groups for AKS administration; required by the AKS module when enabled."
  validation {
    condition     = alltrue([for id in var.aks_admin_group_object_ids : can(regex("^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$", id))])
    error_message = "Each admin group must be an Entra object UUID."
  }
}

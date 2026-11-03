variable "name" { type = string }
variable "location" { type = string }
variable "resource_group_name" { type = string }
variable "tags" { type = map(string) }
variable "admin_group_object_ids" {
  type = list(string)
  validation {
    condition     = length(var.admin_group_object_ids) > 0
    error_message = "AKS requires at least one existing Entra admin group. Do not disable identity controls to bypass this."
  }
}

# Deliberately separate from the foundation VNet: AKS owns its managed network.
resource "azurerm_kubernetes_cluster" "this" {
  name                              = "aks-${var.name}"
  location                          = var.location
  resource_group_name               = var.resource_group_name
  dns_prefix                        = var.name
  sku_tier                          = "Free"
  private_cluster_enabled           = true
  local_account_disabled            = true
  oidc_issuer_enabled               = true
  workload_identity_enabled         = true
  role_based_access_control_enabled = true
  tags                              = var.tags

  default_node_pool {
    name       = "system"
    node_count = 1
    vm_size    = "Standard_D2s_v5"
    upgrade_settings {
      max_surge = "1"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  azure_active_directory_role_based_access_control {
    admin_group_object_ids = var.admin_group_object_ids
  }

  network_profile {
    network_plugin = "azure"
    network_policy = "azure"
    outbound_type  = "loadBalancer"
  }
}

output "name" { value = azurerm_kubernetes_cluster.this.name }
output "oidc_issuer_url" { value = azurerm_kubernetes_cluster.this.oidc_issuer_url }

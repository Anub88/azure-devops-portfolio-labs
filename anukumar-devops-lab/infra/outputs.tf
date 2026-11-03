output "resource_group_name" {
  value = module.foundation.resource_group_name
}

output "network_id" {
  value = module.foundation.network_id
}

output "aks_name" {
  value = var.enable_aks ? module.aks[0].name : null
}

output "aks_oidc_issuer_url" {
  value = var.enable_aks ? module.aks[0].oidc_issuer_url : null
}

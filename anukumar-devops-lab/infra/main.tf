locals {
  name = "${var.prefix}-${var.environment}"
  tags = {
    purpose     = "independent-portfolio-lab"
    environment = var.environment
    owner       = "Anukumar Bendi"
  }
}

module "foundation" {
  source   = "./modules/foundation"
  name     = local.name
  location = var.location
  tags     = local.tags
}

module "aks" {
  count                  = var.enable_aks ? 1 : 0
  source                 = "./modules/aks"
  name                   = local.name
  location               = var.location
  resource_group_name    = module.foundation.resource_group_name
  admin_group_object_ids = var.aks_admin_group_object_ids
  tags                   = local.tags
}

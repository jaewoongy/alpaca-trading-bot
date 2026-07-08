terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
    }
  }
}

provider "azurerm" {
  subscription_id      = "f268cfbd-b3b9-4f82-9460-2ea9022d8dd3"
  storage_use_azuread  = true
  features {}
}

data "azurerm_resource_group" "rg" {
  name = "rg-alpaca-trading-bot"
}

resource "azurerm_log_analytics_workspace" "mcp_logs" {
  name                = "alpaca-trading-logs"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "mcp_insights" {
  name                = "alpaca-trading-insights"
  location            = data.azurerm_resource_group.rg.location
  resource_group_name = data.azurerm_resource_group.rg.name
  application_type    = "web"
  workspace_id        = azurerm_log_analytics_workspace.mcp_logs.id
}

resource "azurerm_container_registry" "acr" {
  name                = "alpacatradingacr2026jy"
  resource_group_name = data.azurerm_resource_group.rg.name
  location            = data.azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = false
}

resource "azurerm_container_app_environment" "mcp_env" {
  name                       = "alpaca-trading-mcp-env"
  location                   = data.azurerm_resource_group.rg.location
  resource_group_name        = data.azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.mcp_logs.id
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

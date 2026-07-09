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
  admin_enabled       = true
}

resource "azurerm_container_app_environment" "mcp_env" {
  name                       = "alpaca-trading-mcp-env"
  location                   = data.azurerm_resource_group.rg.location
  resource_group_name        = data.azurerm_resource_group.rg.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.mcp_logs.id
}

resource "azurerm_container_app" "mcp_server" {
  name                         = "alpaca-trading-mcp"
  container_app_environment_id = azurerm_container_app_environment.mcp_env.id
  resource_group_name          = data.azurerm_resource_group.rg.name
  revision_mode                = "Single"

  registry {
    server               = azurerm_container_registry.acr.login_server
    username              = azurerm_container_registry.acr.admin_username
    password_secret_name = "acr-password"
  }

  secret {
    name  = "acr-password"
    value = azurerm_container_registry.acr.admin_password
  }
  secret {
    name  = "alpaca-api-key"
    value = var.alpaca_api_key
  }
  secret {
    name  = "alpaca-secret-key"
    value = var.alpaca_secret_key
  }

  template {
    container {
      name   = "mcp-server"
      image  = "${azurerm_container_registry.acr.login_server}/alpaca-trading-mcp:latest"
      cpu    = 0.5
      memory = "1Gi"

      env {
        name        = "ALPACA_API_KEY"
        secret_name = "alpaca-api-key"
      }
      env {
        name        = "ALPACA_SECRET_KEY"
        secret_name = "alpaca-secret-key"
      }
    }
    min_replicas = 0
    max_replicas = 2
  }

  ingress {
    external_enabled = true
    target_port      = 8000
    transport         = "auto"
    traffic_weight {
      latest_revision = true
      percentage      = 100
    }
  }
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "container_app_fqdn" {
  value = azurerm_container_app.mcp_server.latest_revision_fqdn
}

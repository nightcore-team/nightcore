variable "image_tag" {
  type    = string
  default = "latest"
}

variable "repository" {
  type    = string
}


job "nightcore-bot" {
  datacenters = ["dc1"]
  type        = "service"

  update {
    max_parallel     = 0
    min_healthy_time = "15s"
    auto_revert      = false
  }

  group "nightcore-bot" {
    count = 1

    disconnect {
      lost_after = "40s"
    }

    service {
      name = "dashboard-backend"

      tags = [
          "traefik.enable=true",
          "traefik.http.routers.dashboard-backend.rule=Host(`api.nightcore.space`)",
          "traefik.http.routers.dashboard-backend.priority=10",
          "traefik.http.routers.dashboard-backend.entrypoints=websecure",
          "traefik.http.routers.dashboard-backend.service=dashboard-backend",
          "traefik.http.services.dashboard-backend.loadbalancer.server.port=5000",
          "traefik.http.routers.dashboard-backend.tls=true",
          
          "traefik.http.middlewares.backend-ratelimit.ratelimit.average=2",
          "traefik.http.middlewares.backend-ratelimit.ratelimit.period=1s",
          "traefik.http.middlewares.backend-ratelimit.ratelimit.burst=8",
          "traefik.http.routers.dashboard-backend.middlewares=backend-ratelimit",

          "traefik.http.routers.dashboard-backend-patch.rule=Host(`api.nightcore.space`) && Method(`PATCH`)",
          "traefik.http.routers.dashboard-backend-patch.priority=15",
          "traefik.http.routers.dashboard-backend-patch.entrypoints=websecure",
          "traefik.http.routers.dashboard-backend-patch.service=dashboard-backend",
          "traefik.http.routers.dashboard-backend-patch.tls=true",
          "traefik.http.routers.dashboard-backend-patch.middlewares=patch-ratelimit",

          "traefik.http.middlewares.patch-ratelimit.ratelimit.average=1",
          "traefik.http.middlewares.patch-ratelimit.ratelimit.period=10s",
          "traefik.http.middlewares.patch-ratelimit.ratelimit.burst=2"
      ]
    }

    task "nightcore-bot" {
      driver = "docker"

      vault {
        role = "runner-nightcore"
      }

      identity {
        name = "vault_default"
        aud  = ["vault.io"]
        ttl  = "1h"
      }

      template {
        data = <<EOT
{{ with secret "secret/data/ci/github-registry" }}
REGISTRY_USERNAME={{ .Data.data.username }}
REGISTRY_TOKEN={{ .Data.data.token }}
{{ end }}
EOT
        destination = "secrets/registry.env"
        env         = true
        change_mode = "restart"
      }

      resources {
        cpu    = 800
        memory = 1000
      }

      config {
        image = "ghcr.io/${var.repository}:${var.image_tag}"

        network_mode = "host"

        auth {
          username       = "${REGISTRY_USERNAME}"
          password       = "${REGISTRY_TOKEN}"
        }
      }

      template {
        data = <<EOT
{{ with secret "secret/data/ci/repos/nightcore" }}
BOT_TOKEN={{ .Data.data.BOT_TOKEN }}
DISABLE_FORUM_TASK={{ .Data.data.DISABLE_FORUM_TASK }}
FORUM_API_KEY={{ .Data.data.FORUM_API_KEY }}
FORUM_API_URL={{ .Data.data.FORUM_API_URL }}
POSTGRES_URL={{ .Data.data.POSTGRES_URL }}
API_PORT={{ .Data.data.API_PORT }}
API_HOST={{ .Data.data.API_HOST }}
API_DOMAIN={{ .Data.data.API_DOMAIN }}
DASHBOARD_FRONTEND_URI={{ .Data.data.DASHBOARD_FRONTEND_URI }}
JWT_ALGORITHM={{ .Data.data.JWT_ALGORITHM }}
JWT_PUBLIC={{ .Data.data.JWT_PUBLIC }}
{{ end }}
EOT
        destination = "secrets/bot.env"
        env         = true
      }

      logs {
        max_files     = 3
        max_file_size = 10
      }

    }
  }
}
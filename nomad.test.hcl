variable "image_tag" {
  type    = string
  default = "latest"
}

variable "repository" {
  type    = string
}

variable "bot_token" {
  type = string
}

variable "disable_forum_task" {
  type = string
}

variable "forum_api_key" {
  type = string
}

variable "forum_api_url" {
  type = string
}

variable "postgres_user" {
  type    = string
  default = "nightcore"
}

variable "postgres_password" {
  type = string
}

variable "postgres_db" {
  type    = string
  default = "nightcore"
}

variable "api_port" {
  type = string
}

variable "api_host" {
  type = string
}

variable "api_domain" {
  type = string
}

variable "dashboard_frontend_uri" {
  type = string
}

variable "jwt_public" {
  type = string
}

variable "jwt_algorithm" {
  type = string
}

job "nightcore-bot-test" {
  namespace = "apps"
  type        = "service"

  constraint {
    attribute = "${meta.roles}"
    operator = "set_contains"
    value = "apps"
  }

  update {
    max_parallel     = 1
    min_healthy_time = "30s"
    auto_revert      = false
  }

  group "nightcore-bot" {
    count = 1

    disconnect {
      lost_after = "40s"
    }

    ephemeral_disk {
      sticky  = true
      migrate = true
      size    = 2048
    }

    network {
      port "postgres" {}
    }

    service {
      name = "dashboard-backend-test"

      tags = [
          "traefik.enable=true",
          "traefik.http.routers.dashboard-backend-test.rule=Host(`api.nightcore.tech`)",
          "traefik.http.routers.dashboard-backend-test.priority=10",
          "traefik.http.routers.dashboard-backend-test.entrypoints=tunnel",
          "traefik.http.routers.dashboard-backend-test.service=dashboard-backend-test",
          "traefik.http.services.dashboard-backend-test.loadbalancer.server.port=5000",

          "traefik.http.middlewares.backend-test-ratelimit.ratelimit.average=2",
          "traefik.http.middlewares.backend-test-ratelimit.ratelimit.period=1s",
          "traefik.http.middlewares.backend-test-ratelimit.ratelimit.burst=8",
          "traefik.http.middlewares.backend-test-ratelimit.ratelimit.sourcecriterion.requestheadername=CF-Connecting-IP",
          "traefik.http.routers.dashboard-backend-test.middlewares=backend-test-ratelimit",

          "traefik.http.routers.dashboard-backend-test-patch.rule=Host(`api.nightcore.tech`) && Method(`PATCH`)",
          "traefik.http.routers.dashboard-backend-test-patch.priority=15",
          "traefik.http.routers.dashboard-backend-test-patch.entrypoints=tunnel",
          "traefik.http.routers.dashboard-backend-test-patch.service=dashboard-backend-test",
          "traefik.http.routers.dashboard-backend-test-patch.middlewares=patch-test-ratelimit",

          "traefik.http.middlewares.patch-test-ratelimit.ratelimit.average=1",
          "traefik.http.middlewares.patch-test-ratelimit.ratelimit.period=10s",
          "traefik.http.middlewares.patch-test-ratelimit.ratelimit.burst=2",
          "traefik.http.middlewares.patch-test-ratelimit.ratelimit.sourcecriterion.requestheadername=CF-Connecting-IP"
      ]
    }

    task "postgres" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = true
      }

      resources {
        cpu    = 200
        memory = 200
      }

      config {
        image = "postgres:16-alpine"

        network_mode = "host"

        args = [
          "-c", "listen_addresses=127.0.0.1",
          "-c", "port=${NOMAD_PORT_postgres}",
        ]
      }

      env {
        POSTGRES_USER     = var.postgres_user
        POSTGRES_PASSWORD = var.postgres_password
        POSTGRES_DB       = var.postgres_db
        PGDATA            = "/alloc/data/postgres"
      }

      logs {
        max_files     = 3
        max_file_size = 10
      }
    }

    task "wait-for-postgres" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = false
      }

      resources {
        cpu    = 50
        memory = 32
      }

      config {
        image = "postgres:16-alpine"

        network_mode = "host"

        command = "sh"
        args = [
          "-c",
          "until pg_isready -h 127.0.0.1 -p ${NOMAD_PORT_postgres} -U ${var.postgres_user} -d ${var.postgres_db}; do sleep 1; done",
        ]
      }
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
        cpu    = 350
        memory = 350
      }

      config {
        image = "ghcr.io/${var.repository}:${var.image_tag}"

        network_mode = "host"

        auth {
          username       = "${REGISTRY_USERNAME}"
          password       = "${REGISTRY_TOKEN}"
        }
      }

      env {
        BOT_TOKEN              = var.bot_token
        DISABLE_FORUM_TASK     = var.disable_forum_task
        FORUM_API_KEY          = var.forum_api_key
        FORUM_API_URL          = var.forum_api_url
        POSTGRES_USER          = var.postgres_user
        POSTGRES_PASSWORD      = var.postgres_password
        POSTGRES_HOST          = "127.0.0.1"
        POSTGRES_PORT          = "${NOMAD_PORT_postgres}"
        POSTGRES_DB            = var.postgres_db
        API_PORT               = var.api_port
        API_HOST               = var.api_host
        API_DOMAIN             = var.api_domain
        DASHBOARD_FRONTEND_URI = var.dashboard_frontend_uri
        JWT_PUBLIC             = var.jwt_public
        JWT_ALGORITHM          = var.jwt_algorithm
      }

      logs {
        max_files     = 3
        max_file_size = 10
      }

    }
  }
}
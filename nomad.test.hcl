variable "bot_image_tag" {
  type    = string
  default = "latest"
}

variable "bot_repository" {
  type    = string
}

variable "auth_image_tag" {
  type    = string
}

variable "auth_repository" {
  type    = string
  default = "nightcore-team/nightcore-auth-service"
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

variable "auth_jwt_private" {
  type = string
}

variable "auth_discord_client_id" {
  type = string
}

variable "auth_discord_client_secret" {
  type = string
}

variable "auth_discord_redirect_uri" {
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
      port "redis" {}
    }

    service {
      name = "dashboard-backend-test"

      tags = [
          "traefik.enable=true",
          "traefik.http.routers.dashboard-backend-test.rule=Host(`api.nightcore.tech`)",
          "traefik.http.routers.dashboard-backend-test.priority=10",
          "traefik.http.routers.dashboard-backend-test.entrypoints=tunnel",
          "traefik.http.routers.dashboard-backend-test.service=dashboard-backend-test",
          "traefik.http.services.dashboard-backend-test.loadbalancer.server.port=5010",

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

    service {
      name = "dashboard-auth-service-test"

      tags = [
          "traefik.enable=true",
          "traefik.http.routers.dashboard-auth-service-test.rule=Host(`api.nightcore.tech`) && PathPrefix(`/auth`)",
          "traefik.http.routers.dashboard-auth-service-test.priority=20",
          "traefik.http.routers.dashboard-auth-service-test.entrypoints=tunnel",
          "traefik.http.routers.dashboard-auth-service-test.service=dashboard-auth-service-test",
          "traefik.http.services.dashboard-auth-service-test.loadbalancer.server.port=5011",

          "traefik.http.middlewares.auth-test-ratelimit.ratelimit.average=2",
          "traefik.http.middlewares.auth-test-ratelimit.ratelimit.period=1s",
          "traefik.http.middlewares.auth-test-ratelimit.ratelimit.burst=2",
          "traefik.http.middlewares.auth-test-ratelimit.ratelimit.sourcecriterion.requestheadername=CF-Connecting-IP",
          "traefik.http.routers.dashboard-auth-service-test.middlewares=auth-test-ratelimit"
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

    task "redis" {
      driver = "docker"

      lifecycle {
        hook    = "prestart"
        sidecar = true
      }

      resources {
        cpu    = 50
        memory = 50
      }

      config {
        image = "redis:7-alpine"

        network_mode = "host"

        args = [
          "--bind", "127.0.0.1",
          "--port", "${NOMAD_PORT_redis}",
          "--dir", "/alloc/data",
          "--maxmemory", "40mb",
          "--maxmemory-policy", "volatile-lru",
        ]
      }

      logs {
        max_files     = 3
        max_file_size = 10
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
        cpu    = 250
        memory = 250
      }

      config {
        image = "ghcr.io/${var.bot_repository}:${var.bot_image_tag}"

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
        API_PORT               = "5010"
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

    task "nightcore-auth-service" {
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
        cpu    = 100
        memory = 100
      }

      config {
        image = "ghcr.io/${var.auth_repository}:${var.auth_image_tag}"

        network_mode = "host"

        auth {
          username       = "${REGISTRY_USERNAME}"
          password       = "${REGISTRY_TOKEN}"
        }
      }

      env {
        API_PORT                   = "5011"
        API_HOST                   = var.api_host
        API_DOMAIN                 = var.api_domain
        DASHBOARD_FRONTEND_URI     = var.dashboard_frontend_uri
        JWT_PUBLIC_KEY             = var.jwt_public
        JWT_PRIVATE_KEY            = var.auth_jwt_private
        JWT_ALGORITHM              = var.jwt_algorithm
        DISCORD_AUTH_CLIENT_ID     = var.auth_discord_client_id
        DISCORD_AUTH_CLIENT_SECRET = var.auth_discord_client_secret
        DISCORD_AUTH_REDIRECT_URI  = var.auth_discord_redirect_uri
        REDIS_HOST                 = "127.0.0.1"
        REDIS_PORT                 = "${NOMAD_PORT_redis}"
      }

      logs {
        max_files     = 3
        max_file_size = 10
      }

    }
  }
}

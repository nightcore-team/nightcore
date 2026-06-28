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
        cpu    = 500
        memory = 600
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
{{ end }}
EOT
        destination = "secrets/bot.env"
        env         = true
      }

      template {
        data = <<EOT
{{ with secret "secret/data/keydb" }}
REDIS_PASSWORD={{ .Data.data.password }}
REDIS_HOST={{ .Data.data.host }}
{{ end }}
EOT
        destination = "secrets/keydb.env"
        env         = true
      }

      logs {
        max_files     = 3
        max_file_size = 10
      }

    }
  }
}
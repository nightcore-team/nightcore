<!-- markdownlint-restore -->

<div align="center">

<h1>💫 Nightcore Discord Bot</h1>

<p>A feature-rich Discord bot for Arizona RP community with economy system, moderation tools, forum integration, and much more.</p>

<!-- prettier-ignore-start -->

| Project    |     | Status                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ---------- | --- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tech Stack |     | ![Python](https://img.shields.io/badge/Python-3.13-202235?style=flat&logo=python&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![Discord.py](https://img.shields.io/badge/Discord.py-Latest-202235?style=flat&logo=discord&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-202235?style=flat&logo=postgresql&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-202235?style=flat&logo=sqlalchemy&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![Pydantic](https://img.shields.io/badge/Pydantic-Latest-202235?style=flat&logo=pydantic&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![uv](https://img.shields.io/badge/uv-Latest-202235?style=flat&logo=astral&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![Docker](https://img.shields.io/badge/Docker-Ready-202235?style=flat&logo=docker&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![Alembic](https://img.shields.io/badge/Alembic-Latest-202235?style=flat&logo=alembic&logoColor=49bdfd&labelColor=202235&color=49bdfd) |
| Meta       |     | ![Linting - Ruff](https://img.shields.io/badge/Linting-Ruff-202235?style=flat&logo=ruff&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![Code Style - Ruff](https://img.shields.io/badge/Code_Style-Ruff-202235?style=flat&logo=ruff&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![License - MIT](https://img.shields.io/badge/License-MIT-202235?style=flat&logoColor=49bdfd&labelColor=202235&color=49bdfd) ![Type Checking - Mypy](https://img.shields.io/badge/Type_Checking-Mypy-202235?style=flat&logo=python&logoColor=49bdfd&labelColor=202235&color=49bdfd)                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |

<!-- prettier-ignore-end -->

</div>

<hr>

## 📋 Table of Contents

- [📋 Table of Contents](#-table-of-contents)
- [🛠 Tech Stack](#-tech-stack)
- [📦 Requirements](#-requirements)
  - [For Docker Setup:](#for-docker-setup)
  - [For Local Setup:](#for-local-setup)
- [🚀 Installation](#-installation)
  - [Docker Setup (Recommended)](#docker-setup-recommended)
  - [Local Setup](#local-setup)
- [⚙️ Configuration](#️-configuration)
  - [Required Variables](#required-variables)
  - [Optional Variables](#optional-variables)
  - [Getting Discord Bot Token](#getting-discord-bot-token)
- [🗄️ Database Migrations](#️-database-migrations)
  - [Create a new migration](#create-a-new-migration)
  - [Apply migrations](#apply-migrations)
  - [Rollback migration](#rollback-migration)
  - [View migration history](#view-migration-history)
- [👨‍💻 Development](#-development)
  - [Code Style](#code-style)
  - [Development Mode](#development-mode)
- [📁 Project Structure](#-project-structure)
- [📝 License](#-license)

## 🛠 Tech Stack

- **Python 3.13**
- **discord.py**: Discord API wrapper
- **PostgreSQL 16**: Database with asyncpg driver
- **SQLAlchemy 2.0**: Async ORM
- **Alembic**: Database migrations
- **Pydantic**: Settings management and validation
- **Docker**: Containerized deployment
- **uv**: Fast Python package installer

## 📦 Requirements

### For Docker Setup:
- Docker 20.10+
- Docker Compose 2.0+

### For Local Setup:
- Python 3.13+
- PostgreSQL 16+
- UV package manager (or pip)
- Git

## 🚀 Installation

### Docker Setup (Recommended)

1. **Clone the repository**
```bash
git clone https://github.com/nightcore-team/nightcore.git
cd nightcore
```

2. **Create environment file**
```bash
cp .env.example .env
```

3. **Configure environment variables** (see [Configuration](#-configuration))

4. **Build and start containers**
```bash
docker-compose up --build
```

The bot will automatically:
- Build the Docker image
- Start PostgreSQL database
- Run database migrations
- Launch the bot

To run in detached mode:
```bash
docker-compose up -d
```

To stop the bot:
```bash
docker-compose down
```

### Local Setup

1. **Clone the repository**
```bash
git clone https://github.com/nightcore-team/nightcore.git
cd nightcore
```

2. **Install UV package manager** (if not installed)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **Create virtual environment and install dependencies**
```bash
uv sync
```

4. **Set up PostgreSQL database**
```bash
# Create database
psql -U postgres
CREATE DATABASE database;
CREATE USER user WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE database TO user;
\q
```

5. **Create environment file**
```bash
cp .env.example .env
```

6. **Configure environment variables** (see [Configuration](#-configuration))

7. **Run database migrations**
```bash
uv run alembic upgrade head
```

8. **Start the bot**
```bash
uv run python main.py
```

## ⚙️ Configuration

Create a `.env` file in the root directory with the following variables:

### Required Variables

```env
# Discord Bot
BOT_TOKEN=discord_bot_token

# PostgreSQL Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_HOST=host # Use 'localhost' for local setup
POSTGRES_PORT=port
POSTGRES_DB=database

# Alternative: Use full database URI instead of individual fields
# POSTGRES_DATABASE_URI=postgresql+asyncpg://user:password@host:port/database

# Forum API Integration
FORUM_API_URL=https://forum.arzguard.com/api
FORUM_API_KEY=your_forum_api_key
```

### Optional Variables

```env
# Bot Configuration
EMBED_DESCRIPTION_LIMIT=4096
VIEW_V2_DESCRIPTION_LIMIT=3000
VIEW_V2_COMPONENTS_LIMIT=40
DELETE_MESSAGES_SECONDS=604800
VOTEBAN_ATTACHMENTS_LIMIT=7
CLOSED_TICKET_ALIVE_HOURS=48
ROLE_REQUESTS_ALIVE_HOURS=2
CASE_REWARDS_LIMIT=30
MAX_CUSTOM_REWARD_SIZE=100
BUG_REPORT_CHANNEL_ID=1442803332233171088
DISABLE_FORUM_TASK=false

# Developer User IDs (comma-separated)
DEVELOPER_IDS=1280700292530176131,566255833684508672,451359852418039808

# Database Connection Pool
POSTGRES_ECHO=false
POSTGRES_ECHO_POOL=true
POSTGRES_POOL_MAX_OVERFLOW=30
POSTGRES_POOL_SIZE=10
POSTGRES_POOL_TIMEOUT=0
POSTGRES_POOL_PRE_PING=true
```

### Getting Discord Bot Token

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Create a new application or select existing one
3. Go to "Bot" section
4. Click "Reset Token" and copy the token
5. Enable required privileged intents:
   - Presence Intent
   - Server Members Intent
   - Message Content Intent

## 🗄️ Database Migrations

The project uses Alembic for database migrations.

### Create a new migration
```bash
make migration
# or manually:
alembic revision --autogenerate -m "Your migration message"
```

### Apply migrations
```bash
make migrate
# or manually:
alembic upgrade head
```

### Rollback migration
```bash
alembic downgrade -1
```

### View migration history
```bash
alembic history
```

## 👨‍💻 Development

### Code Style

The project uses **Ruff** for linting and formatting:

```bash
# Check code
uv run ruff check .

# Format code
uv run ruff format .

# Fix auto-fixable issues
uv run ruff check --fix .
```
> Check pyproject.toml for `ruff` configuration

### Development Mode

For development, you can mount local files in Docker:

```yaml
# Already configured in docker-compose.yml
volumes:
  - ./src/:/app/src/
  - ./main.py:/app/main.py
```

This allows live code reloading without rebuilding the container.

## 📁 Project Structure

```
nightcore/
├── src/
│   ├── __init__.py
│   ├── config/                           # Global configuration
│   │   ├── config.py                     # Main config composition
│   │   └── env.py                       # Base environment settings
│   ├── infra/                           # Infrastructure layer
│   │   ├── api/                         # External APIs
│   │   │   ├── forum/                   # NightForo API client
│   │   │   │   └── ...
│   │   └── db/                          # Database layer
│   │       ├── config.py                 # Database configuration
│   │       ├── operations.py            # Common DB operations
│   │       ├── session.py               # Session management
│   │       ├── uow.py                   # Unit of Work pattern
│   │       ├── utils.py                 # Database utilities
│   │       └── models/                  # SQLAlchemy models
│   ├── nightcore/                       # Bot core
│   │   ├── bot.py                       # Bot class
│   │   ├── config.py                     # Bot configuration
│   │   ├── exceptions.py                # Custom exceptions
│   │   ├── setup.py                     # Setup bot instance and modules to load
│   │   ├── components/                  # Reusable global UI components
│   │   │   ├── __init__.py
│   │   │   ├── embed/                   # embeds
│   │   │   └── v2/                      # v2 (modals, views)
│   │   ├── events/                      # Discord event handlers
│   │   │   ├── error.py                 # Error handling
│   │   │   ├── interaction.py           # Interaction events
│   │   │   ├── channel/                 # Channel events
│   │   │   ├── dto/                     # Event DTOs
│   │   │   ├── member/                  # Member events (join, leave, etc.)
│   │   │   ├── message/                 # Message events
│   │   │   ├── reaction/                # Reaction events
│   │   │   ├── role/                    # Role events
│   │   │   └── voice/                   # Voice state events
│   │   ├── features/                    # Feature modules
│   │   │   ├── clans/                   # Clan management system
│   │   │   ├── compbuilder/             # Component builder
│   │   │   ├── config/                   # Bot configuration commands
│   │   │   ├── economy/                 # Economy & casino system
│   │   │   ├── faq/                     # FAQ system
│   │   │   ├── forum/                   # Forum integration
│   │   │   ├── meta/                    # Meta commands (info, stats)
│   │   │   ├── moderation/              # Moderation tools
│   │   │   ├── private_rooms/           # Private voice rooms
│   │   │   ├── proposals/               # Community voting system
│   │   │   ├── role_requests/           # Role request system
│   │   │   ├── system/                  # System commands
│   │   │   └── tickets/                 # Support ticket system
│   │   ├── services/                    # Business logic services
│   │   │   └── ...
│   │   ├── tasks/                       # Background tasks
│   │   │   ├── ...
│   │   └── utils/                       # Bot utilities
│   │       ├── __init__.py
│   │       ├── ...
│   │       ├── field_validators/         # Field validation utilities
│   │       ├── permissions/             # Permission helpers
│   │       └── transformers/            # Command transformers
│   └── utils/                           # Shared utilities
│       └── logging/                     # Logging configuration
│           ├── config.py                 # Logging config
│           └── setup.py                 # Logging setup
├── migrations/                          # Alembic database migrations
│   ├── drop_structure.sql               # Drop all triggers and functions
│   ├── env.py                           # Alembic environment
│   ├── README                           # Alembic readme
│   ├── script.py.mako                   # Migration template
│   ├── structure.sql                    # Full DB triggers and functions structure
│   └── versions/                        # Migration versions
│       └── ...
├── docker/                              # Docker configuration
│   ├── docker-entrypoint.sh             # Container entrypoint script
├── main.py                              # Application entry point
├── pyproject.toml                       # Project metadata & dependencies # rules
├── docker-compose.yml                   # Docker orchestration
├── Dockerfile                            # Docker image definition
├── alembic.ini                          # Alembic configuration
├── Makefile                              # Common development commands (only migrations)
├── LICENSE                              # License file
└── README.md                            # This file

```

## 📝 License

This project is licensed under the terms specified in the [LICENSE](LICENSE) file.

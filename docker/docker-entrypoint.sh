#!/usr/bin/env sh
set -euo pipefail


echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting application..."
exec python main.py
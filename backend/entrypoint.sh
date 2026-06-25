#!/bin/sh
set -e

export PYTHONPATH=/app

echo "Tables and default data are created by init.sql on app startup."
echo "Starting application..."
exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8010

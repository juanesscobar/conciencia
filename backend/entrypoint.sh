#!/bin/bash
set -e

echo "🌱 Ejecutando seed de admin..."
python scripts/seed_local_admin.py

echo "🌱 Ejecutando seed de agentes..."
python scripts/seed_agents.py || true

echo "🚀 Iniciando servidor..."
exec gunicorn app.main:app \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --workers 4 \
    --timeout 120

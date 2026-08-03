#!/bin/bash
# Deploy helper: create sprint + verify
set -e

API=http://localhost:8000/api/v1

echo "=== PROYECTOS ==="
PROJECTS=$(curl -s $API/projects/)
echo "$PROJECTS" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    print(p['id'], '|', p['name'])
"

# Crear sprint con el primer proyecto activo
PID=$(echo "$PROJECTS" | python3 -c "
import sys, json
projects = json.load(sys.stdin)
active = [p for p in projects if p.get('status') == 'active'] or projects
print(active[0]['id'])
")

echo ""
echo "=== CREAR SPRINT (proyecto $PID) ==="
curl -s -X POST $API/sprints/ -H 'Content-Type: application/json' -d "{
  \"project_id\": \"$PID\",
  \"name\": \"Sprint 1 - Foundation\",
  \"goal\": \"Cimentar la factory: dashboard operativo, entregables y reportes\",
  \"status\": \"active\",
  \"start_date\": \"2026-08-03\",
  \"end_date\": \"2026-08-16\"
}" | python3 -m json.tool

echo ""
echo "=== SPRINTS EXISTENTES ==="
curl -s $API/sprints/ | python3 -m json.tool

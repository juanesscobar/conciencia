#!/bin/bash
# Crea la tarea de Mejoras UX Multilimp en Mission Control
API=http://localhost:8000/api/v1

# Proyecto Multilimp
ML_ID="9dc7696e-43ab-4560-8c04-6394e7864009"

echo '=== CREAR TAREA ==='
curl -s -X POST $API/tasks/ -H 'Content-Type: application/json' -d "{
  \"project_id\": \"$ML_ID\",
  \"title\": \"Mejoras UX - MultiLimp\",
  \"description\": \"Actualizar repo Multilimp en GitHub con mejoras de UX requeridas. Flujo completo: tarea -> ejecucion -> commit/push -> deploy -> registro en MC.\",
  \"status\": \"in_progress\",
  \"priority\": \"high\",
  \"type\": \"feature\",
  \"estimated_hours\": 4
}" | python3 -c "import sys,json; d=json.load(sys.stdin); print('TAREA:', d['id'], '|', d['title'], '|', d['status'])"

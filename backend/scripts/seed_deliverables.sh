#!/bin/bash
# Registra entregables del día (deploy 2026-08-02/03)
API=http://localhost:8000/api/v1

SPRINT_ID="d50924f1-7e6e-4ef0-a32b-2eeced1a4434"
MC_PROJECT_ID="0c3d49e2-c6d6-43d1-a1da-6bb839cb7e75"
ML_PROJECT_ID="9dc7696e-43ab-4560-8c04-6394e7864009"

echo '=== CREAR ENTREGABLES ==='

curl -s -X POST $API/deliverables -H 'Content-Type: application/json' -d "{
  \"project_id\": \"$MC_PROJECT_ID\",
  \"sprint_id\": \"$SPRINT_ID\",
  \"title\": \"Módulo de Entregables + Informe de Sprint\",
  \"description\": \"CRUD de deliverables, informe consolidado por sprint (tareas+commits+PRs), resumen global. Deployado a producción.\",
  \"type\": \"report\",
  \"status\": \"final\",
  \"url\": \"https://github.com/juanesscobar/mission-control/commit/fa96475\",
  \"external_id\": \"fa96475\"
}" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', d['id'], d['title'])"

curl -s -X POST $API/deliverables -H 'Content-Type: application/json' -d "{
  \"project_id\": \"$MC_PROJECT_ID\",
  \"sprint_id\": \"$SPRINT_ID\",
  \"title\": \"Fix: normalización de repos GitHub + Autopilot 24/7\",
  \"description\": \"Fix del bug juanesscobar/juanesscobar/x, script autopilot con cron (sync horario, reporte diario/semanal).\",
  \"type\": \"commit\",
  \"status\": \"final\",
  \"url\": \"https://github.com/juanesscobar/mission-control/commit/363f5e8\",
  \"external_id\": \"363f5e8\"
}" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', d['id'], d['title'])"

curl -s -X POST $API/deliverables -H 'Content-Type: application/json' -d "{
  \"project_id\": \"$ML_PROJECT_ID\",
  \"sprint_id\": \"$SPRINT_ID\",
  \"title\": \"Sync GitHub Multilimp (10 commits)\",
  \"description\": \"Sincronización automática de actividad del repo Multilimp al activity feed.\",
  \"type\": \"commit\",
  \"status\": \"final\",
  \"url\": \"https://github.com/juanesscobar/Multilimp\",
  \"external_id\": \"autopilot\"
}" | python3 -c "import sys,json; d=json.load(sys.stdin); print('OK:', d['id'], d['title'])"

echo ''
echo '=== VERIFICAR INFORME DE SPRINT ==='
curl -s $API/reports/sprint/$SPRINT_ID | python3 -c "
import sys, json
r = json.load(sys.stdin)
print('Sprint:', r['sprint']['name'])
print('Tareas:', r['tasks']['total'], '| done:', r['tasks']['done'], '|', str(r['tasks']['completion_pct']) + '%')
print('Entregables:', len(r['deliverables']))
print('Commits GitHub:', len(r['github']['commits']), '| PRs:', len(r['github']['merged_pulls']))
for d in r['deliverables']:
    print('  -', d['type'], '|', d['title'])
"

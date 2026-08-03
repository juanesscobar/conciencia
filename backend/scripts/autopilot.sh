#!/bin/bash
# ============================================================
# MISSION CONTROL AUTOPILOT
# Ejecutado por cron — sync GitHub + reporte diario
# ============================================================
API=http://localhost:8000/api/v1
REPORTS_DIR=/opt/mission-control/reports
mkdir -p $REPORTS_DIR

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

sync_github() {
  log "SYNC: sincronizando proyectos con GitHub..."
  PROJECTS=$(curl -s $API/projects/)
  echo "$PROJECTS" | python3 -c "
import sys, json
for p in json.load(sys.stdin):
    if p.get('github_repo'):
        print(p['id'], p['github_repo'])
" | while read pid repo; do
    RESULT=$(curl -s -X POST $API/integrations/github/sync/$pid)
    log "SYNC: $repo -> $RESULT"
  done
}

daily_report() {
  REPORT="$REPORTS_DIR/daily_$(date '+%Y%m%d').json"
  curl -s $API/reports/summary > "$REPORT"
  log "REPORT: guardado en $REPORT"
  # Informe del sprint activo si existe
  SPRINT_ID=$(curl -s $API/sprints/ | python3 -c "
import sys, json
sprints = json.load(sys.stdin)
active = [s for s in sprints if s.get('status') == 'active']
print(active[0]['id'] if active else '')
")
  if [ -n "$SPRINT_ID" ]; then
    SPRINT_REPORT="$REPORTS_DIR/sprint_$(date '+%Y%m%d').json"
    curl -s $API/reports/sprint/$SPRINT_ID > "$SPRINT_REPORT"
    log "REPORT: sprint guardado en $SPRINT_REPORT"
  fi
}

case "$1" in
  sync)  sync_github ;;
  daily) daily_report ;;
  all)   sync_github; daily_report ;;
  *)     log "USO: $0 {sync|daily|all}"; exit 1 ;;
esac

log "DONE"

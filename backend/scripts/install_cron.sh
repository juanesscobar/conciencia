#!/bin/bash
# Instala los cron jobs de Mission Control en el servidor
# - Cada hora: sync GitHub
# - Cada día 08:00: reporte diario (summary + sprint)
# - Cada domingo 09:00: reporte semanal

CRON_LINE="0 * * * * bash /opt/mission-control/autopilot.sh sync >> /var/log/mission-control-autopilot.log 2>&1"
DAILY_LINE="0 8 * * * bash /opt/mission-control/autopilot.sh daily >> /var/log/mission-control-autopilot.log 2>&1"
WEEKLY_LINE="0 9 * * 0 bash /opt/mission-control/autopilot.sh all >> /var/log/mission-control-autopilot.log 2>&1"

# Remover líneas viejas de mission-control si existieran
crontab -l 2>/dev/null | grep -v 'autopilot.sh' | crontab -

# Agregar las nuevas
(crontab -l 2>/dev/null; echo "$CRON_LINE"; echo "$DAILY_LINE"; echo "$WEEKLY_LINE") | crontab -

echo '=== CRONTAB RESULTANTE ==='
crontab -l

echo ''
echo '=== LOG FILE ==='
touch /var/log/mission-control-autopilot.log
ls -la /var/log/mission-control-autopilot.log

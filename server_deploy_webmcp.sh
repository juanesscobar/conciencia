#!/bin/bash
# Deploy WebMCP demo app en Hetzner (additivo, sin tocar servicios existentes)
set -e
cd /opt/mission-control || exit 1

echo "=== 1. git pull (fast-forward) ==="
git pull --ff-only origin v2-refactor

echo "=== 2. build webmcp-demo ==="
docker compose build webmcp-demo

echo "=== 3. up webmcp-demo (solo el servicio nuevo) ==="
docker compose up -d webmcp-demo

echo "=== 4. validar + recargar nginx (config nueva) ==="
docker exec mission-control-nginx-1 nginx -t
docker exec mission-control-nginx-1 nginx -s reload

echo "=== 5. verificación ==="
sleep 2
curl -s -o /dev/null -w 'demo page http_code=%{http_code}\n' https://mc.46.62.196.151.sslip.io/webmcp-demo/ --max-time 15
curl -s https://mc.46.62.196.151.sslip.io/webmcp-demo/api/webmcp/context --max-time 15 | head -c 200
echo ""
echo "=== estado ==="
docker ps --format '{{.Names}}: {{.Status}}' | grep webmcp-demo
echo "DONE"

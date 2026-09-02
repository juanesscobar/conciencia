#!/bin/bash
# Fix deploy webmcp-demo: entrypoint vacío + recrear nginx (bind mount inode)
set -e
cd /opt/mission-control || exit 1

echo "=== pull ==="
git pull --ff-only origin v2-refactor

echo "=== recreate webmcp-demo (entrypoint fix) ==="
docker compose up -d webmcp-demo

echo "=== recrear nginx (re-bind nginx.conf nuevo) ==="
docker compose up -d --force-recreate nginx

echo "=== validar ==="
sleep 3
docker ps --format '{{.Names}}: {{.Status}}' | grep -E "webmcp-demo|nginx"
docker exec mission-control-nginx-1 sha1sum /etc/nginx/nginx.conf
echo "--- demo page ---"
curl -s -o /dev/null -w 'http=%{http_code}\n' https://mc.46.62.196.151.sslip.io/webmcp-demo/ --max-time 15
echo "--- bridge context ---"
curl -s https://mc.46.62.196.151.sslip.io/webmcp-demo/api/webmcp/context --max-time 15 | head -c 200
echo ""
echo "--- logs demo ---"
docker logs --tail 5 mission-control-webmcp-demo-1 2>&1
echo "DONE"

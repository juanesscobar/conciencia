#!/bin/bash
cd /opt/mission-control || exit 1
echo "=== git ==="
git rev-parse HEAD 2>/dev/null; git status --short 2>/dev/null | head -5; git branch --show-current 2>/dev/null
echo "=== compose services (names+images) ==="
grep -E "^  [a-z-]+:|image:|build:|container_name:" docker-compose.yml | head -30
echo "=== certbot? ==="
docker ps -a --format '{{.Names}}' | grep -i certbot
echo "=== nginx conf == repo? ==="
docker exec mission-control-nginx-1 sha1sum /etc/nginx/nginx.conf 2>/dev/null
sha1sum nginx/nginx.conf 2>/dev/null
echo "=== repo remote ==="
git remote -v 2>/dev/null | head -2

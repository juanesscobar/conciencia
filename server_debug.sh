#!/bin/bash
echo "=== webmcp-demo logs ==="
docker logs --tail 20 mission-control-webmcp-demo-1 2>&1
echo "=== nginx conf: location webmcp? ==="
docker exec mission-control-nginx-1 sh -c 'grep -n "webmcp-demo" /etc/nginx/nginx.conf | head'
echo "=== nginx conf server_names 443 ==="
docker exec mission-control-nginx-1 sh -c 'grep -n "server_name\|listen 443" /etc/nginx/nginx.conf'
echo "=== host file sha vs container ==="
sha1sum /opt/mission-control/nginx/nginx.conf
docker exec mission-control-nginx-1 sha1sum /etc/nginx/nginx.conf
echo "=== git head server ==="
cd /opt/mission-control && git log --oneline -1

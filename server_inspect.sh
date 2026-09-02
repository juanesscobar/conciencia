#!/bin/bash
# inspección del server mission-control (deploy webmcp demo)
cd /opt/mission-control || exit 1
echo "=== compose services ==="
docker compose ps --format '{{.Name}}: {{.Status}}' 2>/dev/null | head
echo "=== nginx conf locations ==="
docker exec mission-control-nginx-1 sh -c 'ls /etc/nginx/conf.d/ 2>/dev/null; echo ---; grep -rn "server_name\|proxy_pass\|ssl_certificate\|listen " /etc/nginx/conf.d/ /etc/nginx/nginx.conf 2>/dev/null' | head -50
echo "=== certs montados ==="
docker inspect mission-control-nginx-1 --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}' 2>/dev/null | head

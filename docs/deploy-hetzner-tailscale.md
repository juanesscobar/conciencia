# Deploy en Hetzner con Tailscale

> Acceso seguro desde tu tailnet — sin puertos públicos expuestos

## Arquitectura

```
┌─────────────────────────────────────────────────┐
│  Hetzner VPS (46.62.196.151)                    │
│  ┌───────────────────────────────────────────┐  │
│  │ Tailscale (100.x.y.z)                     │  │
│  │   ↓                                       │  │
│  │ Docker Compose                            │  │
│  │   ├─ nginx:80 (localhost solo)            │  │
│  │   ├─ backend:8000 (interno)               │  │
│  │   ├─ frontend:80 (interno)                │  │
│  │   ├─ postgres:5432 (interno)              │  │
│  │   └─ redis:6379 (interno)                 │  │
│  └───────────────────────────────────────────┘  │
│                                                 │
│  Firewall UFW:                                  │
│    - 22/tcp (SSH) ← público                     │
│    - Todo lo demás ← solo via Tailscale         │
└─────────────────────────────────────────────────┘

Acceso desde tu laptop/celular (con Tailscale):
  http://mission-control      (MagicDNS)
  http://100.x.y.z            (IP directa)
```

## Setup rápido (automático)

```bash
# En el VPS Hetzner (como root)
curl -fsSL https://raw.githubusercontent.com/juanesscobar/mission-control/main/setup-hetzner-tailscale.sh | bash
```

O si ya clonaste el repo:

```bash
cd /opt/mission-control
bash setup-hetzner-tailscale.sh
```

## Setup manual (paso a paso)

### 1. Instalar Tailscale en el VPS

```bash
curl -fsSL https://tailscale.com/install.sh | sh
tailscale up --hostname=mission-control
```

Te dará un link para autenticar. Después de autenticar:

```bash
# Verificar conexión
tailscale status
tailscale ip  # anota la IP (100.x.y.z)
```

### 2. Instalar Docker

```bash
curl -fsSL https://get.docker.com | sh
```

### 3. Clonar y configurar

```bash
cd /opt
git clone https://github.com/juanesscobar/mission-control.git
cd mission-control
cp .env.example .env
```

### 4. Editar .env

```bash
nano .env
```

Completar:
- `POSTGRES_PASSWORD` — generar con `openssl rand -base64 32`
- `REDIS_PASSWORD` — generar con `openssl rand -base64 32`
- `SECRET_KEY` — generar con `openssl rand -base64 32`
- `GITHUB_TOKEN` — tu PAT de GitHub
- `DEEPSEEK_API_KEY` — para agentes LLM (opcional)
- `CORS_ORIGINS=http://mission-control`

### 5. Firewall

```bash
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw enable
```

**NO abrir puertos 80/443** — solo accesible via Tailscale.

### 6. Deploy

```bash
docker compose -f docker-compose.tailscale.yml up -d --build
```

### 7. Verificar

```bash
curl http://localhost/health
docker compose -f docker-compose.tailscale.yml logs -f
```

## Acceso

Desde cualquier dispositivo con Tailscale instalado y en tu tailnet:

```
http://mission-control          # MagicDNS (si está activo)
http://100.x.y.z                # IP de Tailscale del VPS
```

Login: `admin` / `MC-Admin#2026!`

## HTTPS con Tailscale (opcional)

Tailscale puede generar certificados TLS automáticos:

```bash
# En el VPS
tailscale cert mission-control

# Los certs se guardan en:
# /var/lib/tailscale/certs/mission-control.crt
# /var/lib/tailscale/certs/mission-control.key
```

Para usarlos, copiá los archivos a `nginx/certs/` y ajustá `nginx-tailscale.conf`.

## Comandos útiles

```bash
# Logs
docker compose -f docker-compose.tailscale.yml logs -f

# Reiniciar
docker compose -f docker-compose.tailscale.yml restart

# Actualizar código + redeploy
git pull
docker compose -f docker-compose.tailscale.yml up -d --build

# Estado de servicios
docker compose -f docker-compose.tailscale.yml ps

# Estado de Tailscale
tailscale status

# IP de Tailscale
tailscale ip
```

## Seguridad

- ✅ Solo SSH (22) expuesto al público
- ✅ Mission Control solo accesible desde tu tailnet
- ✅ Postgres/Redis sin puertos públicos
- ✅ Firewall UFW deny-by-default
- ✅ Secretos fuertes generados aleatoriamente
- ✅ JWT con expiración de 60 min

## Troubleshooting

### No puedo acceder desde mi laptop

1. Verificar que Tailscale está corriendo en ambos lados:
   ```bash
   tailscale status
   ```

2. Verificar que el VPS tiene IP de Tailscale:
   ```bash
   tailscale ip
   ```

3. Probar ping desde tu laptop:
   ```bash
   ping mission-control
   # o
   ping 100.x.y.z
   ```

### El servicio no responde

```bash
# Ver logs
docker compose -f docker-compose.tailscale.yml logs

# Verificar que nginx está corriendo
docker compose -f docker-compose.tailscale.yml ps

# Reiniciar
docker compose -f docker-compose.tailscale.yml restart
```

### Quiero exponer públicamente (no recomendado)

Si necesitás acceso público (ej: para webhooks), usá **Tailscale Funnel**:

```bash
tailscale funnel 80
```

Esto expone el puerto 80 con HTTPS automático via `https://mission-control.ts.net`.

## Comparación: Tailscale vs Let's Encrypt público

| Aspecto | Tailscale | Let's Encrypt público |
|---------|-----------|----------------------|
| Seguridad | ✅ Solo tu tailnet | ⚠️ Público |
| Setup | ✅ Simple | ⚠️ Requiere DNS |
| Certificados | ✅ Automáticos | ✅ Automáticos |
| Acceso móvil | ✅ Con app Tailscale | ✅ Desde cualquier lado |
| Webhooks | ⚠️ Requiere Funnel | ✅ Directo |
| Costo | ✅ Gratis | ✅ Gratis |

**Recomendación**: Usá Tailscale para uso personal/equipo. Usá Let's Encrypt público solo si necesitás webhooks o acceso desde dispositivos sin Tailscale.

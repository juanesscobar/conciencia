#!/bin/bash
# ============================================================
# MISSION CONTROL — Setup para Hetzner + Tailscale
# ============================================================
# Ejecutar como root en el VPS Hetzner
# Instala Tailscale, configura firewall, despliega Mission Control
# ============================================================

set -e

echo "🚀 Mission Control — Setup Hetzner + Tailscale"
echo "================================================"

# Verificar que somos root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Este script debe ejecutarse como root"
    exit 1
fi

# 1. Actualizar sistema
echo "📦 Actualizando sistema..."
apt-get update -qq
apt-get upgrade -y -qq

# 2. Instalar dependencias básicas
echo "📦 Instalando dependencias..."
apt-get install -y -qq curl git ufw

# 3. Instalar Docker si no existe
if ! command -v docker &> /dev/null; then
    echo "🐳 Instalando Docker..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "✅ Docker ya instalado: $(docker --version)"
fi

# 4. Instalar Docker Compose plugin si no existe
if ! docker compose version &> /dev/null; then
    echo "🐳 Instalando Docker Compose plugin..."
    apt-get install -y -qq docker-compose-plugin
else
    echo "✅ Docker Compose ya instalado: $(docker compose version)"
fi

# 5. Instalar Tailscale
if ! command -v tailscale &> /dev/null; then
    echo "🔒 Instalando Tailscale..."
    curl -fsSL https://tailscale.com/install.sh | sh
else
    echo "✅ Tailscale ya instalado: $(tailscale version | head -1)"
fi

# 6. Conectar Tailscale
echo ""
echo "🔒 Conectando a Tailscale..."
echo "   Se abrirá un link para autenticar en tu cuenta"
echo ""
tailscale up --hostname=mission-control --accept-routes

# 7. Obtener IP de Tailscale
TS_IP=$(tailscale ip -4)
echo ""
echo "✅ Tailscale conectado"
echo "   IP de Tailscale: $TS_IP"
echo "   Hostname: mission-control"

# 8. Configurar firewall UFW
echo ""
echo "🔥 Configurando firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
# NO abrir puertos 80/443 al público — solo accesible via Tailscale
ufw --force enable

echo "✅ Firewall configurado (solo SSH público)"

# 9. Opcional: Tailscale HTTPS (certificados automáticos)
echo ""
read -p "¿Querés habilitar HTTPS automático con Tailscale? (s/N): " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Ss]$ ]]; then
    echo "🔒 Habilitando Tailscale HTTPS..."
    tailscale cert mission-control
    
    # Crear directorio para certificados
    mkdir -p /opt/mission-control/nginx/certs
    
    # Copiar certificados
    cp /var/lib/tailscale/certs/*.crt /opt/mission-control/nginx/certs/
    cp /var/lib/tailscale/certs/*.key /opt/mission-control/nginx/certs/
    
    echo "✅ Certificados Tailscale instalados"
    echo "   Renueva con: tailscale cert mission-control"
fi

# 10. Crear directorio de la app
echo ""
echo "📁 Preparando directorio..."
mkdir -p /opt/mission-control
cd /opt/mission-control

# 11. Clonar o actualizar repo
if [ ! -d ".git" ]; then
    echo "📥 Clonando repositorio..."
    read -p "URL del repo (o presioná Enter para usar el default): " REPO_URL
    REPO_URL=${REPO_URL:-https://github.com/juanesscobar/mission-control.git}
    git clone "$REPO_URL" .
else
    echo "📥 Actualizando repositorio..."
    git pull
fi

# 12. Configurar .env
echo ""
echo "⚙️  Configurando variables de entorno..."
if [ ! -f ".env" ]; then
    cp .env.example .env
    
    # Generar secretos aleatorios
    POSTGRES_PASS=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    REDIS_PASS=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    SECRET_KEY=$(openssl rand -base64 32 | tr -dc 'a-zA-Z0-9' | head -c 32)
    
    # Actualizar .env
    sed -i "s/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=$POSTGRES_PASS/" .env
    sed -i "s/REDIS_PASSWORD=.*/REDIS_PASSWORD=$REDIS_PASS/" .env
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
    sed -i "s|CORS_ORIGINS=.*|CORS_ORIGINS=http://mission-control|" .env
    
    echo "✅ .env generado con secretos aleatorios"
    echo ""
    echo "⚠️  IMPORTANTE: Editá /opt/mission-control/.env y agregá:"
    echo "   - GITHUB_TOKEN (para sync de repos)"
    echo "   - DEEPSEEK_API_KEY (para agentes LLM)"
    echo "   - OPENAI_API_KEY (opcional, multi-provider)"
    echo ""
    read -p "Presioná Enter cuando hayas completado .env..."
else
    echo "✅ .env ya existe"
fi

# 13. Desplegar con Docker Compose
echo ""
echo "🐳 Desplegando Mission Control..."
docker compose -f docker-compose.tailscale.yml up -d --build

# 14. Esperar a que los servicios estén listos
echo ""
echo "⏳ Esperando a que los servicios inicien..."
sleep 10

# 15. Verificar health
echo ""
echo "🔍 Verificando estado..."
if curl -s http://localhost/health | grep -q "healthy"; then
    echo "✅ Mission Control está corriendo"
else
    echo "⚠️  El servicio puede estar iniciando aún. Verificá con:"
    echo "   docker compose -f docker-compose.tailscale.yml logs"
fi

# 16. Mostrar información de acceso
echo ""
echo "================================================"
echo "✅ MISSION CONTROL DESPLEGADO"
echo "================================================"
echo ""
echo "📍 Acceso desde tu tailnet:"
echo "   http://mission-control          (MagicDNS)"
echo "   http://$TS_IP                   (IP directa)"
echo ""
echo "🔐 Login:"
echo "   Usuario: admin"
echo "   Password: MC-Admin#2026!"
echo "   (cambialo en Settings después)"
echo ""
echo "📋 Comandos útiles:"
echo "   Ver logs:     docker compose -f docker-compose.tailscale.yml logs -f"
echo "   Reiniciar:    docker compose -f docker-compose.tailscale.yml restart"
echo "   Actualizar:   git pull && docker compose -f docker-compose.tailscale.yml up -d --build"
echo "   Estado:       docker compose -f docker-compose.tailscale.yml ps"
echo ""
echo "🔒 Tailscale:"
echo "   Estado:       tailscale status"
echo "   IP:           tailscale ip"
echo "   HTTPS cert:   tailscale cert mission-control"
echo ""
echo "🛡️  Firewall:"
echo "   Solo SSH (22) está abierto al público"
echo "   Mission Control (80) solo accesible via Tailscale"
echo ""

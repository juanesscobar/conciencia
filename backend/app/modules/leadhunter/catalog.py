"""Catálogo de servicios de Conciencia Software.

Es la oferta comercial que el sales squad usa para mapear compatibilidad
con cada lead. Precios en USD, orientativos por segmento
(pyme / mediana / corporativo).
"""

CONCIENCIA_BRAND = {
    "name": "Conciencia",
    "tagline": "Software factory paraguaya: convertimos procesos manuales en software que vende, ahorra y escala.",
    "services_intro": (
        "Desarrollamos a medida (no revendemos licencias): web apps, CRMs, ERPs, "
        "agentes de IA, automatización, ciberseguridad y presencia digital."
    ),
}

SERVICES = [
    {
        "id": "webapp",
        "emoji": "🌐",
        "name": "Web App / Portal a medida",
        "desc": "Sistema web para gestionar operaciones: clientes, pedidos, stock, reportes.",
        "solves": ["Operación manual en Excel/papel", "Información dispersa entre áreas", "Sin reportes en tiempo real"],
        "price": {"pyme": "USD 1.500 – 4.000", "mediana": "USD 4.000 – 9.000", "corporativo": "USD 9.000+"},
    },
    {
        "id": "crm",
        "emoji": "📊",
        "name": "CRM a medida",
        "desc": "Pipeline comercial, seguimiento de clientes, cotizaciones y recordatorios automáticos.",
        "solves": ["Ventas sin seguimiento", "Clientes olvidados", "Sin métricas comerciales"],
        "price": {"pyme": "USD 2.000 – 5.000", "mediana": "USD 5.000 – 12.000", "corporativo": "USD 12.000+"},
    },
    {
        "id": "erp",
        "emoji": "🏭",
        "name": "ERP / Gestión integrada",
        "desc": "Facturación, inventario, compras, cuentas por cobrar/pagar en un solo sistema.",
        "solves": ["Procesos desconectados", "Errores de inventario", "Cobranzas desordenadas"],
        "price": {"pyme": "USD 5.000 – 12.000", "mediana": "USD 12.000 – 30.000", "corporativo": "USD 30.000+"},
    },
    {
        "id": "ai-agent",
        "emoji": "🤖",
        "name": "Agente IA / Chatbot",
        "desc": "Asistente que atiende consultas 24/7, califica interesados y responde en WhatsApp/Web.",
        "solves": ["Demora en responder clientes", "Costo de atención repetitiva", "Pérdida de consultas fuera de horario"],
        "price": {"pyme": "USD 1.000 – 3.000", "mediana": "USD 3.000 – 8.000", "corporativo": "USD 8.000+"},
    },
    {
        "id": "automation",
        "emoji": "⚙️",
        "name": "Automatización de procesos (RPA)",
        "desc": "Robots que hacen tareas repetitivas: cargas, reportes, avisos, integraciones entre sistemas.",
        "solves": ["Tareas manuales repetitivas", "Errores humanos", "Cuellos de botella operativos"],
        "price": {"pyme": "USD 1.000 – 4.000", "mediana": "USD 4.000 – 10.000", "corporativo": "USD 10.000+"},
    },
    {
        "id": "ecommerce",
        "emoji": "🛒",
        "name": "E-commerce / Tienda online",
        "desc": "Tienda con catálogo, carrito, pagos y envíos integrados.",
        "solves": ["Vender solo por teléfono/WhatsApp", "Sin catálogo online", "No captar pedidos fuera de horario"],
        "price": {"pyme": "USD 2.000 – 5.000", "mediana": "USD 5.000 – 12.000", "corporativo": "USD 12.000+"},
    },
    {
        "id": "cybersecurity",
        "emoji": "🔒",
        "name": "Ciberseguridad / Hardening",
        "desc": "Auditoría, protección de datos, respaldos y endurecimiento de sistemas.",
        "solves": ["Riesgo de filtración de datos", "Sin respaldos confiables", "Accesos sin control"],
        "price": {"pyme": "USD 800 – 2.000", "mediana": "USD 2.000 – 6.000", "corporativo": "USD 6.000+"},
    },
    {
        "id": "landing",
        "emoji": "🎨",
        "name": "Landing page / Identidad digital",
        "desc": "Página de venta profesional con formulario de contacto y seguimiento de interesados.",
        "solves": ["Sin presencia digital", "No captar interesados", "Marca poco profesional"],
        "price": {"pyme": "USD 500 – 1.500", "mediana": "USD 1.500 – 3.000", "corporativo": "USD 3.000+"},
    },
    {
        "id": "support",
        "emoji": "🛠️",
        "name": "Soporte y mantenimiento",
        "desc": "Mantenimiento evolutivo, soporte técnico y mejora continua con SLA.",
        "solves": ["Sistemas que quedan obsoletos", "Sin respuesta cuando algo falla", "Sin mejora continua"],
        "price": {"pyme": "desde USD 300/mes", "mediana": "desde USD 500/mes", "corporativo": "desde USD 1.000/mes"},
    },
]


def catalog_context(segment: str = "pyme") -> str:
    """Render del catálogo en markdown para inyectar en el prompt del squad."""
    seg = (segment or "pyme").lower()
    if seg not in ("pyme", "mediana", "corporativo"):
        seg = "pyme"
    lines = [
        f"# Catálogo de servicios — {CONCIENCIA_BRAND['name']}",
        CONCIENCIA_BRAND["tagline"],
        CONCIENCIA_BRAND["services_intro"],
        "",
        f"Segmento del lead asumido para precios: **{seg}**.",
        "",
    ]
    for s in SERVICES:
        lines.append(f"### {s['emoji']} {s['name']}")
        lines.append(f"- Qué es: {s['desc']}")
        lines.append(f"- Resuelve: {', '.join(s['solves']).lower()}")
        lines.append(f"- Inversión ({seg}): {s['price'][seg]}")
        lines.append("")
    return "\n".join(lines)

<div align="center">

# 🧠 Conciencia

### El Control Plane Open Source para Trabajo Autónomo

**Construir agentes IA es fácil. Ejecutarlos de forma confiable en producción es lo difícil.**

[![Versión](https://img.shields.io/badge/version-0.1.0--alpha-00ff41?style=flat-square&labelColor=0a0f1a)](CHANGELOG.md)
[![Licencia MIT](https://img.shields.io/badge/license-MIT-00ff41?style=flat-square&labelColor=0a0f1a)](LICENSE)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React-00d9ff?style=flat-square&labelColor=0a0f1a)]()

[▶ Probar demo en vivo](https://mc.46.62.196.151.sslip.io) · [Sitio web](https://conciencia-software.vercel.app) · [Docs](docs/ARCHITECTURE.md) · [Contribuir](CONTRIBUTING.md)

</div>

---

## ¿Qué es Conciencia?

Conciencia es la **capa entre los modelos + agentes + herramientas y el trabajo
autónomo real**. El control plane para ejecutar agentes en producción:

- **BUILD** — agentes, herramientas, modelos, skills, servidores MCP
- **OPERATE** — misiones, workflows, ejecución, observabilidad
- **CONTROL** — gobernanza, aprobaciones, auditoría, costos, políticas

La abstracción central: la **MISIÓN** — una unidad de trabajo autónomo con
agentes, herramientas, estado, aprobaciones y trazabilidad completa.

> No es otro chatbot. No es otro framework de agentes. No es otro constructor
> de workflows. Conciencia es **infraestructura para sistemas autónomos confiables**.

---

## ¿Por qué Conciencia?

| Problema | Conciencia |
|---|---|
| Los agentes solo funcionan en demos | **Misiones** con estado real, reintentos y ejecución |
| Sin control humano | **Gates de aprobación** — human-in-the-loop por diseño |
| Sin rendición de cuentas | **Auditoría completa** — cada acción, decisión y costo |
| Cadenas LLM frágiles | **LLM Harness** — multi-proveedor con fallback automático |
| Silos | **MCP nativo** — conectá cualquier tool/server, email incluido |
| Sin gobernanza | **Políticas, roles, trazabilidad, costos** |

---

## 🚀 Quickstart (3 comandos)

```bash
git clone https://github.com/juanesscobar/mission-control.git
cd mission-control
docker compose up -d --build
```

Abrí `http://localhost` — el admin se crea con `LOCAL_ADMIN_PASSWORD` (ver `.env.example`).

**¿Preferís desarrollo local sin Docker?** → [Quickstart local](docs/DEVELOPMENT.md)

> 🧪 ¿Sin API keys? El LLM Harness corre en **modo simulado** para explorar todo
> el control plane sin gastar nada.

---

## 🎬 Demo insignia: Calificación autónoma de leads

```
Lead entra al sistema      →  Lead Hunter (Overpass/OSM)
      ↓
Agente research            →  enriquecimiento (website → email/tel)
      ↓
Enriquecimiento + scoring  →  LLM Harness (score 0-100, sector, preguntas)
      ↓
Aprobación humana          →  revisión del prospecto calificado
      ↓
Agente outreach            →  propuesta PDF + email vía MCP (SMTP/IMAP)
      ↓
CRM update                 →  kanban, notas, eventos
      ↓
Auditoría                  →  todo logueado, trazado y costeado
```

---

## Conceptos core

- **Misiones** — unidades de trabajo autónomo (calificar un lead, shippear una feature)
- **Agentes** — 8 roles (dev, ops, qa, pm, rd, comms, fin, admin), cada uno con su
  `SOUL.md` como system prompt
- **Workflows** — flujos multi-paso con gates de aprobación y DAG de tareas
- **LLM Harness** — routing multi-proveedor (DeepSeek, OpenAI, Anthropic, Google,
  OpenRouter, Ollama) con fallback, costos y latencia
- **MCP** — servidores externos; el email server built-in expone
  `email_send`, `email_inbox`, `email_test` a los agentes
- **Control plane** — gobernanza, políticas, decisiones, auditoría, trazas, costos
- **Command center** — modo Operator (control total) vs modo Client (solo resultados)

---

## Arquitectura

<div align="center">

![Arquitectura de Conciencia](docs/architecture.svg)

</div>

**Stack:** FastAPI · PostgreSQL · Redis · React + Vite + Tailwind · Docker · MCP (stdio) · nginx

Detalle completo: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## ✨ Features

- 🤖 **8 agentes** con identidad `SOUL.md` + registro en DB
- 🧠 **LLM Harness** — multimodal, fallback, tracking de costo y latencia
- ⚙️ **Workflows + gates de aprobación** — human-in-the-loop
- 🔀 **Task DAG** — dependencias con estados READY/ASSIGNED/BLOCKED
- 📬 **Módulo email** — multi-proveedor (Gmail/Outlook/genérico), IMAP + SMTP,
  credenciales cifradas (Fernet), expuesto como MCP tools
- 🔌 **MCP Tool Registry** — attach de cualquier servidor MCP stdio
- 💰 **Lead Hunter** — descubrimiento Overpass/OSM, dedupe, enriquecimiento IA,
  scoring, propuestas PDF, entrega por email/WhatsApp
- 📊 **Governance** — proyectos, sprints, métricas, reportes, decisiones
- 👤 **Memoria de usuario** — contexto persistente por operador
- 🔒 **Seguridad por defecto** — solo nginx expone puertos, Postgres/Redis internos,
  secrets cifrados, auditoría completa

---

## 🤝 Comunidad & Contribución

- [Guía de contribución](CONTRIBUTING.md) — de good-first-issues a integraciones profundas
- [Templates de issues](.github/ISSUE_TEMPLATE/) — bug, feature, docs
- [Política de seguridad](SECURITY.md) — reporte privado de vulnerabilidades

---

## 📄 Licencia

[MIT](LICENSE) © 2026 Juan Andrés Escobar Vega

---

<div align="center">

</div>

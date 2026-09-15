<div align="center">

# 🧠 Conciencia

### El Control Plane Open Source para Trabajo Autónomo

**Construir agentes IA es fácil. Ejecutarlos de forma confiable en producción es lo difícil.**

[![Versión](https://img.shields.io/badge/version-0.6.0-00ff41?style=flat-square&labelColor=0a0f1a)](CHANGELOG.md)
[![Licencia MIT](https://img.shields.io/badge/license-MIT-00ff41?style=flat-square&labelColor=0a0f1a)](LICENSE)
[![Stack](https://img.shields.io/badge/stack-FastAPI%20%2B%20React-00d9ff?style=flat-square&labelColor=0a0f1a)]()
[![Tests](https://img.shields.io/badge/tests-140%20green-00ff41?style=flat-square&labelColor=0a0f1a)]()
[![Hecho con ❤️](https://img.shields.io/badge/hecho%20con-❤️-ff4d4d?style=flat-square&labelColor=0a0f1a)]()

[▶ Probar demo en vivo](https://mc.46.62.196.151.sslip.io) · [Sitio web](https://conciencia-software.vercel.app) · [Docs](docs/ARCHITECTURE.md) · [Guía de uso](docs/USAGE.md) · [Contribuir](CONTRIBUTING.md)

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

> 🧪 **¿Sin API keys?** El LLM Harness corre en **modo simulado** y la búsqueda
> semántica usa embeddings simulados determinísticos — explorá todo el control
> plane sin gastar un centavo.

**Walkthrough completo** (web, CLI y API): [📖 docs/USAGE.md](docs/USAGE.md)

---

## 🎬 La demo estrella: Calificación Autónoma de Leads

```
Lead entra al sistema        →  Lead Hunter (Overpass/OSM)
      ↓
Agente research              →  enriquecimiento (website → email/tel)
      ↓
Enriquecimiento IA + scoring →  LLM Harness (score 0-100, sector, preguntas)
      ↓
Aprobación humana            →  revisá el prospecto calificado
      ↓
Agente outreach              →  propuesta PDF + email vía MCP (SMTP/IMAP)
      ↓
Actualización CRM            →  kanban, notas, eventos
      ↓
Auditoría                    →  todo logueado, trazado y costeado
```

El pipeline completo corre en la demo en vivo — desde lead crudo hasta propuesta
enviada, con agentes, herramientas, modelos, aprobaciones, logs, costo y auditoría visibles.

---

## Conceptos centrales

- **Misiones** — unidades de trabajo autónomo (calificar un lead, shippear una feature)
- **Agentes** — 11 roles integrados (dev, ops, qa, pm, rd, comms, fin, admin +
  research, classify, contacts de LeadHunter), cada uno con su `SOUL.md` como system prompt
- **Workflows** — flujos multi-paso con gates de aprobación y dependencias DAG
- **LLM Harness** — routing multi-proveedor (DeepSeek, OpenAI, Anthropic, Google,
  OpenRouter, Ollama) con fallback, costos y métricas de latencia
- **Multi-Runtime** — ejecutá agentes con generic, claude_code, codex, opencode,
  openclaw o mcp (runner seguro por subprocess, sin shell)
- **MCP** — conectá servidores externos de tools; el servidor de email integrado
  expone `email_send`, `email_inbox`, `email_test` a los agentes
- **Control plane** — gobernanza, políticas, decisiones, audit log, trazas, costos
- **Command center** — modo Operator (control total) vs modo Client (solo resultados)

---

## Arquitectura

<div align="center">

![Arquitectura de Conciencia](docs/architecture.svg)

</div>

```
CONCIENCIA
   │
┌──┼─────────┬────────────┐
BUILD      OPERATE      CONTROL
Agentes    Misiones    Gobernanza
Tools      Workflows   Aprobaciones
Modelos    Runtime     Auditoría
Skills     Ejecución   Observabilidad
```

**Stack:** FastAPI · PostgreSQL · Redis · React + Vite + Tailwind · Docker · MCP
(stdio) · nginx (entrypoint de producción).

Detalles: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

---

## ✨ Features

- 🤖 **11 agentes** con identidades `SOUL.md` (8 roles core + 3 LeadHunter:
  research / classify / contacts), permisos ALLOW/DENY, auditoría completa
- 🧠 **LLM Harness** — multi-proveedor (DeepSeek, OpenAI, Anthropic, Google,
  OpenRouter, Ollama), fallback, tracking de costos/latencia, token budgets
- 🔀 **Ejecución multi-runtime** — generic, claude_code, codex, opencode,
  openclaw, mcp (runner seguro por subprocess, sin shell)
- ⚙️ **Workflows + gates de aprobación** — ejecución human-in-the-loop
- 🔀 **Task DAG** — dependencias con estados READY/ASSIGNED/BLOCKED
- 📬 **Módulo de email** — multi-proveedor (Gmail/Outlook/generic), IMAP read +
  SMTP send, credenciales cifradas (Fernet), expuesto como tools MCP
- 🔌 **MCP Tool Registry** — conectá cualquier servidor MCP stdio
- 🎯 **Lead Hunter Intelligence** — el pipeline estrella (ver abajo)
- 📊 **Gobernanza** — proyectos, sprints, métricas, reportes, decisiones
- 👤 **Memoria de usuario** — contexto persistente por operador
- 🖥️ **CLI `conciencia`** — misma lógica de dominio que web/API, cero código duplicado
- 🔒 **Seguridad por defecto** — solo nginx expone puertos, Postgres/Redis internos,
  secretos cifrados, auditoría completa

### 🎯 Lead Hunter Intelligence (F1-F11, spec completo ✅)

Pipeline completo de prospección — hunt → enrich → rank → qualify → propose → deliver:

- **Discovery**: Overpass/OSM (sin API key), bbox configurable, dedupe por
  nombre/dominio/tel normalizados, jobs async + cron APScheduler
- **Búsqueda NL**: interpretación de texto libre + filtros estructurados (país,
  región, ciudad, categoría, industria, segmento, presencia online, score mínimo)
- **Búsqueda semántica**: vector backend (InMemory / pgvector), embeddings reales
  o simulados (provider compatible OpenAI)
- **Score Intelligence**: 4 scores explicables — Search Relevance, Lead Score,
  Opportunity Score, Data Quality — con weights configurables y razones "why this match"
- **Enrichment**: scraping del website (email/tel, anti-junk) + agentes IA
- **Propuestas**: generación de PDF + entrega por email/WhatsApp
- **Pipeline kanban**: new → contacted → qualified → proposal → won/lost
- **Exports**: CSV/JSON · **Búsquedas guardadas y listas de leads**

### 🖥️ CLI `conciencia`

```bash
pip install -e backend/          # instala el entry point `conciencia`

conciencia health
conciencia search "empresas logísticas" --country PY --online website
conciencia leads list --status qualified
conciencia leads export --format csv --out leads.csv
conciencia lead inspect <id>     # detalle completo + razones
conciencia lead score <id>       # 4 scores explicables
conciencia lead enrich <id>      # enrich desde el website
conciencia hunt --industry distribuidoras
conciencia config get            # settings (get/set)
conciencia agents · conciencia modules
```

Referencia CLI completa: [docs/USAGE.md](docs/USAGE.md#4-uso-cli)

---

## 📸 Screenshots

<!-- TODO: agregar screenshots reales (login, dashboard, missions, email, lead hunter) -->
_Próximamente — mientras tanto, la demo en vivo: https://mc.46.62.196.151.sslip.io_

---

## 🗺️ Roadmap

- **v0.6** — actual: control plane + Lead Hunter Intelligence completo
  (F1-F11, 140 tests backend, DoD 21/21)
- **v0.7** — UI de model/tool registry, provenance source_records, pgvector en prod
- **v0.8** — marketplace de agentes, más servidores MCP
- **v1.0** — Conciencia Cloud (managed), integraciones enterprise, equipos

Ver [CHANGELOG.md](CHANGELOG.md), [docs/LEADHUNTER_INTELLIGENCE_PLAN.md](docs/LEADHUNTER_INTELLIGENCE_PLAN.md)
y los issues abiertos.

---

## 🤝 Comunidad y Contribuciones

- [Guía de contribución](CONTRIBUTING.md) — desde good-first-issues de 30 min hasta integraciones profundas
- [Plantillas de issues](.github/ISSUE_TEMPLATE/) — bug, feature, docs
- [Política de seguridad](SECURITY.md) — reporte privado de vulnerabilidades

---

## 📄 Licencia

[MIT](LICENSE) © 2026 Juan Andrés Escobar Vega

---

<div align="center">

*

</div>

# 🎯 MISSION CONTROL
## Software Factory + Project Governance System

**CEO:** Iron Toto (@irontoto7)  
**Estado:** Planificación → MVP  
**Versión:** 1.0.0-alpha  

---

## 🏗️ Visión

Mission Control es el **cerebro operativo** que orquesta todos los proyectos, sub-agentes y métricas. Trabajamos como una software factory: vos sos el CEO que define estrategia, los sub-agentes ejecutan, y el sistema trackea todo.

**Principios:**
1. **Autonomía con supervisión** — los agentes pueden actuar, pero envían previews antes de deploys
2. **Métricas accionables** — benchmark contra industria + métricas personales
3. **Transparencia total** — dashboard unificado con estado de todo
4. **Iteración continua** — MVP primero, automatización después

---

## 📦 Portafolio de Proyectos

### 🔴 Core (Activo/Alto Valor)
| Proyecto | Stack | Estado | Prioridad |
|----------|-------|--------|-----------|
| **Open Agent IA** | FastAPI + PostgreSQL + Redis | MVP entregado | P0 |
| **JobScout** | Node.js + Remotive API | Funcionando | P1 |
| **Atiendo AI** | Node.js + whatsapp-web.js | Activo | P1 |
| **Mission Control** | FastAPI/React + PostgreSQL | En planificación | P0 |

### 🟡 Legacy/Mantenimiento
| Proyecto | Stack | Estado | Notas |
|----------|-------|--------|-------|
| **nanobot** | Python + Flask | v0.1.3 | OpenClaw simplificado |

### 🔵 Integrados en Mission Control (Recreados)
| Proyecto | Stack Original | Integración | Notas |
|----------|----------------|-------------|-------|
| **TaskOk v2** | Node.js + Mongo | FastAPI + React | Dashboard gestión de tareas + control de asistencia integrado en MC |

### 🟢 GitHub Portfolio (23 repos)
- **conciencia** y otros proyectos para pulir una vez estabilicemos core

---

## 🤖 Sub-Agentes de la Software Factory

### 1. 👨‍💻 Developer Agent (DEV)
**Responsabilidad:** Codificación, PRs, code reviews, debugging

**Capacidades:**
- Generar features desde especificaciones
- Crear PRs con descripción y tests
- Code review automático (estilo, bugs, performance)
- Debugging y fix de issues

**Autonomía:** 
- ✅ Puede escribir código y tests
- ✅ Puede crear branches y PRs
- ⚠️ Necesita aprobación para merge a main
- ❌ No puede deployar a producción sin preview

---

### 2. 🚀 DevOps Agent (OPS)
**Responsabilidad:** Infraestructura, deploys, CI/CD, monitoreo

**Capacidades:**
- Setup de infra (Docker, K8s, cloud)
- Pipeline CI/CD
- Deploys a staging/prod
- Monitoreo y alertas
- Backups y disaster recovery

**Autonomía:**
- ✅ Puede configurar infra y pipelines
- ✅ Deploy automático a staging
- ⚠️ Deploy a prod con preview obligatorio
- ✅ Puede escalar recursos automáticamente

---

### 3. 🧪 QA Agent (QA)
**Responsabilidad:** Testing, calidad, validación

**Capacidades:**
- Escribir tests unitarios/integración/E2E
- Ejecutar test suites
- Validar ACs (Acceptance Criteria)
- Detectar regresiones
- Verificar performance

**Autonomía:**
- ✅ Puede rechazar PRs por calidad
- ✅ Puede bloquear deploys con bugs críticos
- ✅ Reporta métricas de cobertura

---

### 4. 📊 Product Agent (PM)
**Responsabilidad:** Roadmap, priorización, especificaciones

**Capacidades:**
- Mantener backlog ordenado
- Escribir especificaciones claras
- Priorizar features según impacto/esfuerzo
- Definir milestones y releases
- User stories y ACs

**Autonomía:**
- ✅ Puede reordenar prioridades (con notificación)
- ✅ Puede crear tickets/features
- ⚠️ Cambios de roadmap grandes necesitan sync con CEO

---

### 5. 📚 Research Agent (R&D)
**Responsabilidad:** Investigación, documentación, análisis técnico

**Capacidades:**
- Research de tecnologías/libs nuevas
- Análisis de competencia
- Documentación técnica y de usuario
- Spike/proof of concepts
- Análisis de deuda técnica

**Autonomía:**
- ✅ Puede investigar y documentar
- ✅ Puede recomendar adoptar/rechazar tecnologías
- ⚠️ Decisiones arquitectónicas grandes necesitan aprobación

---

### 6. 🎨 Comms Strategy Agent (COMMS)
**Responsabilidad:** Comunicación, marketing, contenido, community

**Capacidades:**
- Estrategia de comunicación por proyecto
- Copy para landing pages
- Posts para redes (LinkedIn, Twitter/X)
- Newsletter/email updates
- Documentación pública/docs sites

**Autonomía:**
- ✅ Puede crear borradores de contenido
- ⚠️ Publicaciones públicas necesitan aprobación
- ✅ Puede programar posts aprobados

---

### 7. 💰 Finance Agent (FIN)
**Responsabilidad:** Finanzas, presupuestos, métricas de negocio

**Capacidades:**
- Track de costos (infra, APIs, servicios)
- Proyecciones de revenue (si aplica)
- ROI de features/proyectos
- Alertas de gastos anormales
- Reports financieros

**Autonomía:**
- ✅ Puede alertar sobre overspending
- ✅ Puede recomendar optimizaciones de costo
- ⚠️ Cambios de planes de pricing necesitan aprobación

---

### 8. 🎯 Admin Agent (ADMIN)
**Responsabilidad:** Tareas administrativas, organización, recordatorios

**Capacidades:**
- Scheduling de reuniones/checkpoints
- Follow-ups de tareas pendientes
- Organización de documentos
- Recordatorios de deadlines
- Resúmenes de estado

**Autonomía:**
- ✅ Puede crear recordatorios y tareas
- ✅ Puede enviar resúmenes periódicos
- ✅ Puede reorganizar documentación

---

## 📊 Sistema de Métricas

### Métricas de Industria (Benchmark)
| Métrica | Target | Fuente |
|---------|--------|--------|
| Lead Time (idea → prod) | < 7 días | DORA |
| Deployment Frequency | > 1/día | DORA |
| Change Failure Rate | < 15% | DORA |
| MTTR (recovery) | < 1 hora | DORA |
| Code Coverage | > 80% | Estándar |
| PR Review Time | < 24h | Estándar |
| Bug Escape Rate | < 5% | Estándar |

### Métricas Personales (Iron Toto)
| Métrica | Objetivo | Tracking |
|---------|----------|----------|
| Proyectos activos completados/mes | 2+ | Manual → Auto |
| Features shipped/semana | 3+ | Dashboard |
| Horas de deep work/semana | 20+ | Time tracking |
| Nuevos usuarios/adopción | Variable | Por proyecto |
| Repos actualizados/mes | 5+ | GitHub API |
| Side project revenue | $XXX/mes | Manual |

---

## 🏛️ Estructura de Trabajo

### Ritmos (Cadencia)

| Ritmo | Frecuencia | Participantes | Output |
|-------|------------|---------------|--------|
| **Daily** | Diaria | Todos los agentes | Status update (escrito) |
| **Sprint Planning** | Semanal | PM + CEO | Sprint backlog definido |
| **Sprint Review** | Semanal | Todos | Demo + métricas |
| **Retrospective** | Quincenal | Todos | Mejoras de proceso |
| **Strategy Sync** | Mensual | CEO + PM + R&D | Roadmap ajustado |
| **Financial Review** | Mensual | FIN + CEO | Reporte de costos/ROI |

### Flujo de Trabajo (GitHub Flow)

```
1. PM crea feature ticket con especificaciones
2. DEV toma ticket → branch → desarrollo
3. QA escribe tests de aceptación
4. DEV abre PR → QA review automático
5. OPS valida CI/CD pasa
6. Deploy a staging automático
7. QA valida en staging
8. Preview enviado a CEO para aprobación
9. Deploy a producción (manual o auto según riesgo)
10. Métricas actualizadas automáticamente
```

---

## 🗺️ Roadmap Mission Control

### Fase 1: Foundation (Semanas 1-2)
- [ ] Setup repo Mission Control
- [ ] Definir arquitectura base (FastAPI + React)
- [ ] Modelo de datos: Proyectos, Agentes, Tareas, Métricas
- [ ] Dashboard básico (read-only de proyectos)
- [ ] Integración GitHub API (lista repos, commits, PRs)

### Fase 2: Governance (Semanas 3-4)
- [ ] CRUD de proyectos
- [ ] Sistema de tareas con estados
- [ ] Dashboard de métricas básicas
- [ ] Integración con Telegram (notificaciones)
- [ ] Bot de status diario automatizado

### Fase 3: Agents MVP (Semanas 5-6)
- [ ] Implementar DEV Agent básico (code review)
- [ ] Implementar PM Agent (backlog management)
- [ ] Implementar ADMIN Agent (reminders)
- [ ] Comandos Telegram para interactuar con agentes

### Fase 4: Automation (Semanas 7-8)
- [ ] DEV Agent puede crear PRs
- [ ] OPS Agent maneja deploys staging
- [ ] QA Agent ejecuta tests automáticos
- [ ] Preview system antes de deploys prod

### Fase 5: Intelligence (Semanas 9-12)
- [ ] FIN Agent con tracking de costos
- [ ] COMMS Agent con estrategia de contenido
- [ ] R&D Agent con research automático
- [ ] Dashboard predictivo (predicciones de entrega)

---

## 🎯 Próximos Pasos Inmediatos

1. **Aprobar este plan** (vos como CEO)
2. **Crear SOUL.md de cada agente** (personalidad + instrucciones)
3. **Setup repo Mission Control** (estructura base)
4. **Sprint 1:** Foundation + Dashboard read-only

---

*Documento vivo — se actualiza según evolucione la factory.*

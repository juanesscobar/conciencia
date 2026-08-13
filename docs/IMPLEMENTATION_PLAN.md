# Mission Control — Plan de Implementación

> **Visión:** Open-source AI Software Factory Control Plane.
> Plan, orchestrate, govern and observe AI agents building software.

**Orden (decisión del CEO):**
1. 🟢 Estabilización E2E (funcionalidad > arquitectura)
2. 🟡 Control Plane P0 (adapters, registry, DAG, audit, workflows)
3. 🟠 Control Plane P1 (matching, approvals, cost, health, GitHub)
4. 🔵 Open Source (docs, cleanup, pilots)
5. 💰 Monetización (solo análisis, cero billing)

**Reglas:** inspeccionar antes de modificar · no reescribir · cambios incrementales · tests por etapa · no romper compatibilidad · PR-sized commits.

---

## 🟢 ETAPA 0 — Estabilización E2E

| PR | Descripción | Estado |
|----|-------------|--------|
| 0.1 | `docs/e2e-health-check.md` — inventario WORKING/BROKEN/MOCKED | ✅ |
| 0.2 | LeadHunterJob formal: `POST /leads/jobs` + cancel/retry async | ⏳ |
| 0.3 | Observabilidad de pasos del job (searching→extracting→scoring→done) | ⏳ |
| 0.4 | Error handling explícito (timeout, rate limit, partial) | ⏳ |
| 0.5 | Test E2E job→leads→persistencia→API | ⏳ |
| 0.6 | Fix blockers (DEEPSEEK_API_KEY, SMTP real, mocks) | ⏳ |

## 🟡 ETAPA 1 — Control Plane P0

| PR | Descripción | Estado |
|----|-------------|--------|
| 1.1 | AgentAdapter interface + Generic/OpenClaw adapter | ✅ |
| 1.2 | Agent Registry: health/heartbeat, runtime, provider, model | ✅ |
| 1.3 | Task DAG: task_dependencies n-n + READY/BLOCKED | ✅ |
| 1.4 | Audit events append-only + run persistence | ✅ |
| 1.5 | Workflow engine declarativo (mínimo, pausable) | ✅ |

## 🟠 ETAPA 2 — Control Plane P1

| PR | Descripción | Estado |
|----|-------------|--------|
| 2.1 | Capability matching (requirements → candidates → best) | ✅ |
| 2.2 | Approval gates UI (PENDING/APPROVED/REJECTED) | ✅ |
| 2.3 | Cost tracking real por ejecución + budgets | ⏳ |
| 2.4 | Agent health dashboard + alertas | ⏳ |
| 2.5 | GitHub: issue→task→run→commit→PR | ⏳ |

## 🔵 ETAPA 3 — Open Source

- README reposicionado · docs (architecture/adapters/workflows/governance/api) · cleanup mocks · CI tests

## 💰 ETAPA 4 — Monetización (análisis)

- `docs/business-model.md` · pricing · go-to-market · open-core strategy · BYOK

---

## Definición de Éxito (E2E)

- [ ] Backend inicia · [ ] Frontend inicia · [ ] Migraciones OK
- [ ] Lead Hunter crea job · [ ] Job ejecuta real · [ ] Leads extraídos/validados/deduplicados/scored/persistidos
- [ ] Frontend muestra resultados · [ ] Errores visibles · [ ] Jobs fallan y se reintentan
- [ ] Test E2E · [ ] Docs · [ ] Sin mocks ocultos en flujo principal

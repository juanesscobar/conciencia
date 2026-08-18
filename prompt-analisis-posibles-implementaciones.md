posibles implementaciones: 



1: # Mission Control — Evolución a AI Software Factory Control Plane



\## Contexto



Este repositorio es "Mission Control", una plataforma para coordinar una software factory basada en agentes de IA.



El objetivo de esta evolución NO es convertir Mission Control en otro framework de agentes ni copiar proyectos existentes.



Queremos convertirlo progresivamente en un:



> \*\*Open-source AI Software Factory Control Plane\*\*



La plataforma debe encargarse principalmente de:



\* planificación;

\* proyectos;

\* tareas;

\* agentes;

\* asignación;

\* workflows;

\* ejecución;

\* revisión;

\* aprobaciones humanas;

\* observabilidad;

\* costes;

\* auditoría;

\* governance;

\* integración con diferentes runtimes de agentes.



Los agentes externos deben encargarse de la ejecución especializada.



\---



\# REGLA PRINCIPAL



Antes de modificar código:



1\. Inspecciona completamente la arquitectura existente.

2\. Identifica frontend, backend, base de datos, modelos, servicios, autenticación y sistema actual de agentes.

3\. Identifica qué funcionalidades ya existen.

4\. NO reemplaces componentes existentes si pueden evolucionarse.

5\. NO hagas una reescritura completa.

6\. Mantén compatibilidad con las funcionalidades actuales.

7\. Prioriza cambios incrementales.

8\. Ejecuta tests después de cada etapa.

9\. Documenta decisiones arquitectónicas importantes.

10\. Si encuentras una decisión que pueda romper compatibilidad, detente y documenta el problema antes de implementarla.



\---



\# VISIÓN DEL PRODUCTO



La arquitectura conceptual debe evolucionar hacia:



Human Layer

↓

Dashboard / API / Approvals

↓

Governance Layer

↓

Policies / RBAC / Audit / Costs / Security

↓

Orchestration Layer

↓

Projects / Tasks / Dependencies / Workflows

↓

Agent Adapter Layer

↓

Claude Code / Codex / OpenClaw / CrewAI / LangGraph / otros

↓

Execution Layer

↓

GitHub / Git / Docker / CI/CD / infrastructure



Mission Control debe permanecer independiente del runtime específico de cada agente.



\---



\# FASE 1 — Agent Adapter Architecture



Crear una abstracción estándar:



AgentAdapter



Debe permitir:



\* register\_agent()

\* get\_agent\_status()

\* dispatch\_task()

\* cancel\_task()

\* pause\_task()

\* resume\_task()

\* send\_message()

\* receive\_event()

\* stream\_logs()

\* get\_capabilities()



Los agentes concretos deben implementarse mediante adapters.



Ejemplos:



\* GenericAgentAdapter

\* OpenClawAdapter

\* ClaudeCodeAdapter

\* CodexAdapter

\* CrewAIAdapter

\* LangGraphAdapter



No asumir que todos los agentes funcionan igual.



Mission Control debe trabajar con un contrato común.



\---



\# FASE 2 — Agent Registry



Crear un registro central de agentes.



Cada agente debe tener:



\* id

\* name

\* description

\* role

\* capabilities

\* runtime

\* model

\* provider

\* status

\* availability

\* workspace

\* version

\* health status

\* last heartbeat

\* cost configuration

\* permissions



Ejemplo conceptual:



Agent:



Developer



Capabilities:



\* python

\* fastapi

\* docker

\* postgres

\* testing



Otro agente:



Reviewer



Capabilities:



\* code-review

\* security

\* testing



Esto permitirá implementar posteriormente capability-based task assignment.



\---



\# FASE 3 — Capability Matching



Agregar un sistema de matching:



Task requirements

↓

Required capabilities

↓

Agent Registry

↓

Candidate Agents

↓

Best Agent

↓

Dispatch



El sistema debe poder determinar:



"Esta tarea necesita Python + FastAPI + PostgreSQL"



y encontrar agentes compatibles.



No usar únicamente el nombre/rol del agente.



\---



\# FASE 4 — Task Dependencies



Convertir las tareas en un DAG cuando corresponda.



Ejemplo:



Architecture

↓

Backend

↓

Frontend

↓

Tests

↓

Security Review

↓

Deployment



Una tarea solamente debe desbloquearse cuando sus dependencias estén satisfechas.



Implementar estados claros:



BACKLOG

READY

ASSIGNED

RUNNING

BLOCKED

REVIEW

APPROVAL\_REQUIRED

COMPLETED

FAILED

CANCELLED



\---



\# FASE 5 — Workflow Engine



Crear workflows declarativos.



Ejemplo conceptual:



plan

→ implement

→ test

→ review

→ security

→ human approval

→ deploy



Cada step debe poder especificar:



\* agent

\* required capabilities

\* timeout

\* retry policy

\* approval requirement

\* dependencies

\* maximum cost

\* allowed tools



El workflow debe poder pausarse y reanudarse.



\---



\# FASE 6 — Human-in-the-loop



Agregar explícitamente puntos de aprobación humana.



Ejemplos:



\* aprobar arquitectura;

\* aprobar PR;

\* aprobar deployment;

\* aprobar uso de herramientas sensibles;

\* aprobar gasto superior al límite;

\* aprobar cambios destructivos.



Estados:



PENDING\_APPROVAL

APPROVED

REJECTED



Nunca permitir que un agente ignore una approval gate.



\---



\# FASE 7 — Governance



Crear una capa de governance.



Debe incluir:



\## RBAC



Roles iniciales:



\* Owner

\* Admin

\* Manager

\* Developer

\* Reviewer

\* Viewer



\## Policies



Permitir definir:



\* herramientas permitidas;

\* repositorios permitidos;

\* branches permitidos;

\* límites de coste;

\* acciones que requieren aprobación;

\* acciones prohibidas.



\---



\# FASE 8 — Audit Log



Todo evento importante debe generar un audit event.



Ejemplos:



\* agent\_registered

\* task\_created

\* task\_assigned

\* task\_started

\* task\_completed

\* task\_failed

\* workflow\_started

\* workflow\_paused

\* approval\_requested

\* approval\_granted

\* approval\_rejected

\* tool\_invoked

\* deployment\_started

\* deployment\_completed



Cada evento debería contener:



\* timestamp

\* actor

\* actor\_type

\* project

\* task

\* event\_type

\* metadata

\* correlation\_id



El audit log debe ser append-only desde el punto de vista de la aplicación.



\---



\# FASE 9 — Cost Intelligence



Agregar tracking de costes.



Registrar por ejecución:



\* provider

\* model

\* input tokens

\* output tokens

\* cached tokens cuando esté disponible

\* estimated cost

\* execution duration

\* task

\* agent

\* project



Permitir visualizar:



Cost

↓

Project

↓

Task

↓

Agent

↓

Model



Agregar:



\* budget por proyecto;

\* budget por task;

\* budget por agent;

\* alertas;

\* cost overrun detection.



El objetivo no es solamente mostrar tokens.



Mission Control debe responder:



> "¿Cuánto costó producir este resultado?"



\---



\# FASE 10 — Observability



Crear una vista de ejecución.



Cada run debe poder mostrar:



\* agent;

\* task;

\* start time;

\* duration;

\* status;

\* logs;

\* tool calls;

\* output;

\* errors;

\* retries;

\* cost;

\* artifacts;

\* Git commit;

\* PR.



Una ejecución debe poder reconstruirse posteriormente.



\---



\# FASE 11 — Execution Replay



Diseñar los runs como entidades persistentes.



Debe ser posible:



\* inspeccionar una ejecución;

\* ver su timeline;

\* identificar errores;

\* comparar ejecuciones;

\* consultar qué agente participó;

\* consultar qué modelo se utilizó;

\* consultar cuánto costó.



Preparar la arquitectura para replay/debugging.



No implementar un replay completo si requiere una reescritura; primero implementar event persistence correctamente.



\---



\# FASE 12 — GitHub Integration



Expandir integración GitHub.



Mission Control debe poder asociar:



Project

↓

Repository

↓

Issue

↓

Task

↓

Agent Run

↓

Commit

↓

Pull Request

↓

Review

↓

Deployment



Registrar referencias a:



\* repository;

\* branch;

\* commit SHA;

\* PR;

\* issue.



No duplicar innecesariamente información que ya pertenece a GitHub.



\---



\# FASE 13 — Software Factory Metrics



Agregar métricas de ingeniería.



Dashboard:



\## Delivery



\* tasks completed;

\* tasks failed;

\* cycle time;

\* lead time;

\* throughput;

\* blocked time.



\## Agents



\* success rate;

\* failure rate;

\* average duration;

\* workload;

\* utilization.



\## AI Economics



\* tokens;

\* cost;

\* cost/task;

\* cost/project;

\* cost/PR;

\* cost/successful task.



\## Quality



\* test success rate;

\* review rejection rate;

\* bug/rework rate;

\* deployment success rate.



La finalidad es responder:



> "¿La software factory está mejorando?"



y no solamente:



> "¿Cuántos agentes están online?"



\---



\# FASE 14 — Agent Health



Implementar heartbeat y health monitoring.



Estados:



ONLINE

IDLE

BUSY

DEGRADED

OFFLINE

ERROR



Mostrar:



\* last heartbeat;

\* current task;

\* current session;

\* runtime;

\* provider;

\* model.



Agregar alertas cuando un agente desaparece durante una ejecución.



\---



\# FASE 15 — API-FIRST



Toda funcionalidad importante del dashboard debe tener una API correspondiente.



Preparar Mission Control para:



\* CLI;

\* agentes;

\* webhooks;

\* integraciones;

\* automatizaciones;

\* futuras aplicaciones móviles.



Documentar API mediante OpenAPI.



\---



\# FASE 16 — Event-Driven Architecture



No implementar una arquitectura distribuida innecesaria.



Sin embargo, diseñar eventos internos de forma consistente.



Ejemplo:



TaskCreated

TaskAssigned

TaskStarted

TaskCompleted

TaskFailed

ApprovalRequested

ApprovalGranted

AgentConnected

AgentDisconnected



Esto permitirá posteriormente integrar:



\* WebSockets;

\* queues;

\* webhooks;

\* external event buses.



\---



\# FASE 17 — Security



Agregar progresivamente:



\* secret management;

\* API authentication;

\* scoped API keys;

\* RBAC;

\* permission checks;

\* audit logs;

\* rate limiting;

\* webhook signature validation;

\* secure credential storage.



Nunca almacenar secrets de proveedores directamente en logs.



Nunca exponer API keys en respuestas del frontend.



\---



\# FASE 18 — Architecture Documentation



Crear:



docs/

architecture.md

agent-adapters.md

workflows.md

governance.md

security.md

api.md

cost-tracking.md



Agregar diagramas Mermaid cuando aporten claridad.



Documentar especialmente:



1\. cómo se registra un agente;

2\. cómo se asigna una task;

3\. cómo se ejecuta un workflow;

4\. cómo se registra una ejecución;

5\. cómo funciona una approval gate;

6\. cómo se registra el coste;

7\. cómo se integra GitHub.



\---



\# FASE 19 — Testing



Implementar progresivamente:



Unit tests

Integration tests

API tests

Workflow tests

Adapter tests



Casos importantes:



\* agent unavailable;

\* task timeout;

\* agent failure;

\* retry;

\* approval rejection;

\* budget exceeded;

\* dependency blocked;

\* duplicate event;

\* GitHub failure.



\---



\# FASE 20 — PRODUCT POSITIONING



Actualizar README y documentación.



Mission Control debe describirse como:



> Open-source control plane for AI software factories.



No como:



> AI chatbot.



No como:



> LLM framework.



No como:



> Another agent framework.



La propuesta:



> Plan, orchestrate, govern and observe AI agents building software.



\---



\# REGLAS DE IMPLEMENTACIÓN



Prioridad:



P0:



\* Agent Adapter

\* Agent Registry

\* Task dependencies

\* Workflow state

\* Audit events

\* Run persistence



P1:



\* Capability matching

\* Human approvals

\* Cost tracking

\* GitHub integration

\* Agent health



P2:



\* Advanced metrics

\* Replay

\* Policies

\* Webhooks

\* CLI



P3:



\* Multi-tenant SaaS

\* Billing

\* Cloud deployment

\* Enterprise SSO

\* advanced analytics



No implementar P3 antes de estabilizar P0/P1.



\---



\# CRITERIO DE ÉXITO



Al finalizar las primeras fases, un usuario debe poder:



1\. Crear un proyecto.

2\. Registrar varios agentes.

3\. Definir sus capabilities.

4\. Crear una task.

5\. Definir dependencias.

6\. Asignar automáticamente el agente adecuado.

7\. Ejecutar el agente mediante un adapter.

8\. Ver el run en tiempo real.

9\. Ver logs.

10\. Ver coste.

11\. Solicitar aprobación humana.

12\. Continuar el workflow.

13\. Asociar commit/PR.

14\. Registrar el resultado.

15\. Consultar todo posteriormente mediante audit log.



\---



\# IMPORTANTE



No implementar todo de una vez.



Primero genera:



1\. Architecture Assessment.

2\. Current vs Target Architecture.

3\. Gap Analysis.

4\. Proposed database changes.

5\. Proposed API changes.

6\. Implementation plan dividido en PR-sized milestones.



Después de presentar ese plan, comienza únicamente por P0.



No realices cambios destructivos sin aprobación.





2: 

\# Mission Control — End-to-End Stabilization \& Lead Hunter



\## OBJETIVO PRINCIPAL



Antes de agregar nuevas funcionalidades arquitectónicas, convertir Mission Control en un producto funcional de extremo a extremo.



La prioridad absoluta es:



> \*\*FUNCIONALIDAD > ARQUITECTURA > FEATURES > MONETIZACIÓN\*\*



Actualmente Mission Control incluye un Lead Hunter en desarrollo.



El Lead Hunter debe funcionar realmente end-to-end dentro de Mission Control.



NO implementar todavía:



\* billing;

\* subscriptions;

\* multi-tenancy;

\* enterprise SSO;

\* marketplace;

\* arquitectura distribuida innecesaria;

\* grandes refactors;

\* nuevas funcionalidades que no sean necesarias para completar el flujo E2E.



Primero debemos conseguir una versión estable, demostrable y reproducible.



\---



\# REGLA #1 — NO ASUMIR QUE ALGO FUNCIONA



Antes de modificar código:



1\. Inspeccionar TODO el repositorio.

2\. Ejecutar backend.

3\. Ejecutar frontend.

4\. Ejecutar tests existentes.

5\. Revisar migraciones.

6\. Revisar variables de entorno.

7\. Revisar servicios externos.

8\. Revisar endpoints.

9\. Revisar modelos de base de datos.

10\. Revisar integración del Lead Hunter.

11\. Revisar ejecución real de agentes.

12\. Identificar TODO código incompleto, mock, TODO, FIXME o placeholder.



No asumir que una feature funciona porque existe una pantalla o endpoint.



\---



\# FASE 0 — PRODUCT HEALTH CHECK



Crear un documento:



docs/e2e-health-check.md



Debe contener:



\* arquitectura actual;

\* cómo levantar el sistema;

\* dependencias;

\* variables de entorno;

\* servicios externos;

\* estado del backend;

\* estado del frontend;

\* estado de DB;

\* estado de agentes;

\* estado de Lead Hunter;

\* funcionalidades funcionando;

\* funcionalidades rotas;

\* funcionalidades simuladas;

\* blockers.



Clasificar cada funcionalidad:



WORKING

PARTIALLY\_WORKING

BROKEN

MOCKED

NOT\_IMPLEMENTED



\---



\# FASE 1 — BASE DEL SISTEMA



Verificar completamente:



Frontend

↓

API

↓

Service layer

↓

Database

↓

External services



Comprobar:



\* health endpoint;

\* database connection;

\* migrations;

\* authentication si existe;

\* CORS;

\* environment configuration;

\* error handling;

\* frontend API client.



Debe existir un procedimiento reproducible para levantar Mission Control desde cero.



Documentarlo.



\---



\# FASE 2 — LEAD HUNTER E2E



Esta es la prioridad máxima.



El flujo deseado:



User

↓

Mission Control UI

↓

Create Lead Hunter Job

↓

Define search criteria

↓

Submit job

↓

Backend creates job

↓

Agent / Lead Hunter executes

↓

External data sources

↓

Lead extraction

↓

Lead normalization

↓

Lead validation

↓

Lead scoring

↓

Persistence

↓

Results API

↓

Mission Control Dashboard

↓

User reviews leads

↓

User takes action



TODO el flujo debe ser real.



No aceptar mocks como implementación final.



\---



\# FASE 3 — LEAD HUNTER JOB



Crear/validar una entidad LeadHunterJob.



Debe contener como mínimo:



\* id;

\* project\_id;

\* status;

\* query / search criteria;

\* configuration;

\* created\_at;

\* started\_at;

\* completed\_at;

\* error;

\* results\_count.



Estados:



PENDING

RUNNING

COMPLETED

FAILED

CANCELLED



\---



\# FASE 4 — LEAD MODEL



Validar/crear una entidad Lead.



Como mínimo:



\* id;

\* job\_id;

\* company\_name;

\* website;

\* contact\_name cuando esté disponible;

\* contact\_email cuando esté disponible;

\* phone cuando esté disponible;

\* location;

\* industry;

\* source;

\* source\_url;

\* score;

\* qualification;

\* status;

\* metadata;

\* created\_at;

\* updated\_at.



No almacenar información que no sea necesaria.



Respetar las condiciones de uso de las fuentes de datos utilizadas.



\---



\# FASE 5 — LEAD PIPELINE



Separar claramente:



Discovery

↓

Extraction

↓

Normalization

↓

Validation

↓

Deduplication

↓

Scoring

↓

Persistence



Cada etapa debe poder diagnosticarse.



Si una etapa falla:



\* registrar error;

\* conservar información útil;

\* marcar el job apropiadamente;

\* evitar perder silenciosamente resultados.



\---



\# FASE 6 — DEDUPLICATION



Implementar deduplicación.



Un mismo lead no debería aparecer repetido por:



\* misma URL;

\* mismo dominio;

\* mismo email;

\* combinación razonable de company + contact.



No eliminar datos automáticamente si existe riesgo de falso positivo.



Preferir marcar conflictos antes que destruir información.



\---



\# FASE 7 — LEAD SCORING



El scoring debe ser explícito y reproducible.



Ejemplo:



Lead

↓

Criteria

↓

Score

↓

Qualification



Documentar exactamente cómo se calcula.



No utilizar un LLM para scoring si una regla determinista puede resolverlo.



Cuando se utilice IA:



\* registrar modelo;

\* registrar prompt/version;

\* registrar resultado;

\* registrar coste cuando esté disponible.



\---



\# FASE 8 — ASYNC EXECUTION



Si Lead Hunter realiza operaciones largas:



NO bloquear el request HTTP.



Utilizar el mecanismo async/queue/background job que ya exista en el proyecto.



Si actualmente no existe una arquitectura adecuada:



implementar la solución mínima necesaria.



Priorizar simplicidad.



\---



\# FASE 9 — OBSERVABILITY



El usuario debe poder saber:



Job:

RUNNING



↓



Step:

Searching



↓



Step:

Extracting



↓



Step:

Validating



↓



Step:

Scoring



↓



Step:

Completed



Cada job debe registrar:



\* timestamps;

\* estado;

\* errores;

\* cantidad de resultados;

\* duración.



\---



\# FASE 10 — FRONTEND



La UI debe permitir:



1\. Crear un Lead Hunter job.

2\. Configurar búsqueda.

3\. Iniciar ejecución.

4\. Ver estado.

5\. Ver progreso.

6\. Ver errores.

7\. Ver resultados.

8\. Filtrar leads.

9\. Ordenar por score.

10\. Abrir detalles.

11\. Ver fuente.

12\. Exportar resultados si existe esa funcionalidad.

13\. Reintentar jobs fallidos.



No crear una UI visualmente compleja si la funcionalidad backend todavía no funciona.



\---



\# FASE 11 — API CONTRACT



Documentar:



POST /lead-hunter/jobs

GET /lead-hunter/jobs

GET /lead-hunter/jobs/{id}

POST /lead-hunter/jobs/{id}/cancel

POST /lead-hunter/jobs/{id}/retry

GET /lead-hunter/jobs/{id}/leads



Adaptar estos endpoints a la arquitectura existente si ya existen equivalentes.



NO duplicar endpoints innecesariamente.



\---



\# FASE 12 — ERROR HANDLING



Comprobar explícitamente:



\* external API failure;

\* timeout;

\* rate limit;

\* invalid credentials;

\* empty search;

\* malformed data;

\* duplicate lead;

\* database failure;

\* agent failure;

\* partial results.



Nunca devolver:



HTTP 200 + "success"



cuando realmente falló el proceso.



\---



\# FASE 13 — END-TO-END TEST



Crear al menos un test E2E real:



Create Job

↓

Execute

↓

Retrieve Results

↓

Validate Leads



Debe comprobar:



\* job creado;

\* job ejecutado;

\* status correcto;

\* resultados persistidos;

\* API devuelve resultados;

\* frontend puede consumirlos.



Si las fuentes externas requieren credenciales y no pueden utilizarse en CI:



crear una separación clara:



\* integration test real;

\* E2E test con fixture controlada.



No ocultar una simulación detrás de un nombre que sugiera ejecución real.



\---



\# FASE 14 — DEMO FLOW



Crear un flujo reproducible:



1\. Levantar Mission Control.

2\. Crear proyecto.

3\. Abrir Lead Hunter.

4\. Introducir criterios.

5\. Ejecutar búsqueda.

6\. Esperar procesamiento.

7\. Obtener leads.

8\. Visualizarlos.

9\. Abrir detalle.

10\. Exportar/usar resultados.



Este flujo debe poder demostrarse sin intervención manual en la base de datos.



\---



\# FASE 15 — INTEGRACIÓN CON MISSION CONTROL



Lead Hunter no debe convertirse en una aplicación aislada dentro del repositorio.



Debe integrarse conceptualmente:



Project

↓

Lead Hunter Job

↓

Agent

↓

Task

↓

Execution

↓

Leads

↓

Activity



Cuando corresponda, registrar actividad en Mission Control.



\---



\# FASE 16 — AGENTS



Identificar qué agente ejecuta Lead Hunter.



Debe ser posible saber:



\* agent;

\* model;

\* provider;

\* execution id;

\* start/end;

\* status.



No acoplar Lead Hunter innecesariamente a un único proveedor.



Preparar una abstracción para poder cambiar posteriormente:



DeepSeek

OpenAI

Anthropic

Gemini

Kimi

etc.



Pero NO implementar todos los providers ahora.



\---



\# FASE 17 — SECURITY



Revisar:



\* API keys;

\* secrets;

\* logs;

\* user input;

\* external URLs;

\* SSRF;

\* arbitrary code execution;

\* shell execution;

\* database injection;

\* prompt injection;

\* malicious lead data.



Particularmente importante:



Los datos obtenidos por Lead Hunter deben considerarse UNTRUSTED INPUT.



Nunca ejecutar automáticamente instrucciones contenidas dentro de páginas web, emails o campos de leads.



\---



\# FASE 18 — COST TRACKING PREPARATION



No implementar billing todavía.



Pero registrar cuando sea posible:



\* model;

\* provider;

\* tokens;

\* duration;

\* estimated cost;

\* job;

\* agent.



Esto permitirá monetizar posteriormente sin rehacer la arquitectura.



\---



\# FASE 19 — CODE QUALITY



Después de que E2E funcione:



\* eliminar dead code;

\* eliminar mocks innecesarios;

\* corregir TODO críticos;

\* mejorar nombres;

\* separar responsabilidades;

\* validar tipos;

\* mejorar errores;

\* agregar tests.



NO hacer un refactor masivo.



\---



\# DEFINITION OF DONE



Mission Control NO se considera listo hasta que:



\[ ] Backend inicia correctamente.

\[ ] Frontend inicia correctamente.

\[ ] Database/migrations funcionan.

\[ ] Lead Hunter puede crear un job.

\[ ] Job puede ejecutarse realmente.

\[ ] Agente puede ejecutar el proceso.

\[ ] Fuentes externas funcionan.

\[ ] Leads se extraen.

\[ ] Leads se validan.

\[ ] Leads se deduplican.

\[ ] Leads se califican.

\[ ] Leads se almacenan.

\[ ] Frontend muestra resultados.

\[ ] Errores son visibles.

\[ ] Jobs pueden fallar correctamente.

\[ ] Jobs pueden reintentarse.

\[ ] Existe al menos un E2E test.

\[ ] Existe documentación para ejecutar el sistema.

\[ ] No existen mocks ocultos en el flujo principal.



\---



\# ORDEN DE EJECUCIÓN



NO implementar todo simultáneamente.



Trabajar en este orden:



1\. Health Check

2\. Fix critical blockers

3\. Backend

4\. Database

5\. Lead Hunter execution

6\. Lead persistence

7\. API

8\. Frontend

9\. Error handling

10\. E2E tests

11\. Security

12\. Cost tracking

13\. Documentation

14\. Only then architectural improvements



Al terminar cada etapa:



\* ejecutar tests;

\* verificar funcionamiento;

\* reportar cambios;

\* reportar problemas restantes.



Antes de continuar a una etapa que dependa de otra, verificar que la anterior funciona.



El objetivo final de esta fase es:



> \*\*Mission Control debe poder demostrarse funcionando end-to-end con Lead Hunter desde la interfaz hasta el resultado persistido.\*\*







2:



\# Mission Control — Monetization \& Business Strategy



\## OBJETIVO



Diseñar una estrategia comercial sostenible para Mission Control.



Mission Control se posicionará como:



> \*\*Open-source AI Software Factory Control Plane\*\*



La plataforma coordina:



\* proyectos;

\* tareas;

\* agentes;

\* workflows;

\* executions;

\* approvals;

\* observability;

\* governance;

\* GitHub;

\* AI costs;

\* Lead Hunter;

\* futuras integraciones con diferentes agent runtimes.



IMPORTANTE:



No implementar billing todavía.



Primero realizar un análisis estratégico basado en el producto REAL existente.



\---



\# 1. PRODUCT AUDIT



Inspeccionar el repositorio y determinar:



\* funcionalidades actuales;

\* funcionalidades realmente funcionando;

\* funcionalidades diferenciadoras;

\* funcionalidades que podrían monetizarse;

\* dependencia de servicios externos;

\* costes variables;

\* costes potenciales de infraestructura.



Separar:



CORE

vs

PREMIUM

vs

ENTERPRISE



\---



\# 2. TARGET CUSTOMER



Identificar posibles clientes:



\## Persona 1 — Individual Developer



Necesidades:



\* ejecutar agentes;

\* organizar tareas;

\* visualizar runs;

\* GitHub.



\## Persona 2 — AI Developer / Consultant



Necesidades:



\* múltiples agentes;

\* múltiples proyectos;

\* workflows;

\* clientes;

\* observability.



\## Persona 3 — Startup



Necesidades:



\* AI software factory;

\* team collaboration;

\* governance;

\* costs;

\* audit.



\## Persona 4 — Software Agency



Necesidades:



\* múltiples clientes;

\* múltiples proyectos;

\* agentes especializados;

\* reporting;

\* cost tracking.



\## Persona 5 — Enterprise



Necesidades:



\* RBAC;

\* SSO;

\* audit;

\* security;

\* private deployment;

\* compliance;

\* SLA.



Determinar cuál debería ser el primer ICP (Ideal Customer Profile).



\---



\# 3. BUSINESS MODEL



Evaluar estos modelos:



A. Open Source

B. Open Core

C. SaaS

D. BYOK SaaS

E. Managed Cloud

F. Enterprise Self-Hosted

G. Professional Services

H. Consulting

I. Custom Integrations



Para cada modelo indicar:



\* ventajas;

\* desventajas;

\* costes;

\* dificultad;

\* escalabilidad;

\* potencial de ingresos;

\* dependencia del soporte;

\* riesgo.



\---



\# 4. RECOMMENDED MODEL



Evaluar especialmente:



\## Community



Open source.



Incluye:



\* self-hosted;

\* projects;

\* tasks;

\* agents;

\* workflows;

\* GitHub;

\* basic dashboard.



\## Cloud



Managed SaaS.



Incluir potencialmente:



\* hosted infrastructure;

\* team collaboration;

\* advanced observability;

\* cost analytics;

\* advanced workflows;

\* backups;

\* notifications.



\## Business



Funciones avanzadas:



\* RBAC;

\* audit;

\* policies;

\* advanced analytics;

\* SSO;

\* larger limits;

\* retention.



\## Enterprise



Evaluar:



\* private deployment;

\* VPC;

\* SSO/SAML;

\* SCIM;

\* advanced security;

\* SLA;

\* dedicated support;

\* custom integrations.



\---



\# 5. BYOK



Analizar como estrategia principal:



Bring Your Own Key.



El cliente utiliza sus propias credenciales:



\* OpenAI;

\* Anthropic;

\* Google;

\* DeepSeek;

\* Moonshot;

\* otros.



Mission Control cobra por:



\* orchestration;

\* governance;

\* observability;

\* collaboration;

\* infrastructure;

\* management.



NO asumir el coste de los tokens del cliente en el modelo BYOK.



Analizar ventajas y desventajas.



\---



\# 6. LEAD HUNTER MONETIZATION



Analizar Lead Hunter como posible módulo comercial.



Posibles modelos:



\* free limited searches;

\* monthly credits;

\* pay per lead;

\* pay per qualified lead;

\* subscription;

\* premium module.



Comparar:



Lead Hunter como parte del core

vs

Lead Hunter como premium add-on.



Analizar especialmente:



\* coste por búsqueda;

\* coste de APIs;

\* coste de scraping/data;

\* coste de LLM;

\* valor económico del lead;

\* margen.



No proponer precios arbitrarios sin justificar la lógica.



\---



\# 7. PRICING STRATEGY



Proponer pricing inicial orientativo.



Evaluar:



Free

Developer

Team

Business

Enterprise



Analizar si conviene cobrar por:



\* users;

\* agents;

\* concurrent runs;

\* projects;

\* executions;

\* workflow runs;

\* storage;

\* log retention;

\* seats;

\* advanced features.



Evitar cobrar directamente por tokens cuando BYOK sea el modelo.



\---



\# 8. UNIT ECONOMICS



Crear un modelo conceptual:



\## Revenue



\## Infrastructure



\## Storage



\## Observability



\## Support



\# Payment fees



Gross Margin



Analizar escenarios:



10 customers

100 customers

1,000 customers

10,000 customers



No inventar costes reales.



Cuando falten datos, utilizar supuestos explícitos.



\---



\# 9. OPEN SOURCE STRATEGY



Definir:



Qué permanecerá open source.



Qué podría ser premium.



Qué debería permanecer enterprise.



Evitar artificialmente ocultar funcionalidades fundamentales.



El objetivo del open source debe ser:



Adoption

→ GitHub

→ Community

→ Self-hosted users

→ Cloud conversions

→ Enterprise



\---



\# 10. COMPETITIVE POSITIONING



Comparar conceptualmente Mission Control con:



\* Builderz Mission Control;

\* Orchestratia;

\* Stoneforge;

\* Overdeck;

\* Buzz;

\* OpenClaw;

\* coding-agent orchestration tools.



No copiar funcionalidades.



Identificar:



\* gaps;

\* oportunidades;

\* diferenciadores.



\---



\# 11. DIFFERENTIATION



Evaluar especialmente este posicionamiento:



> "Control plane for AI software factories."



La propuesta debería abarcar:



Planning

→ Orchestration

→ Execution

→ Review

→ Governance

→ Observability

→ Economics



Identificar qué parte puede convertirse en ventaja competitiva sostenible.



\---



\# 12. PROFESSIONAL SERVICES



Evaluar servicios:



\* Mission Control deployment;

\* AI Software Factory setup;

\* custom agent adapters;

\* GitHub integration;

\* workflow design;

\* governance;

\* security;

\* consulting;

\* training.



Crear posibles paquetes:



Starter

Professional

Enterprise



Sin inventar precios definitivos.



\---



\# 13. GO-TO-MARKET



Crear estrategia inicial:



Phase 1:

Open source developers



Phase 2:

AI developers / consultants



Phase 3:

Small software teams



Phase 4:

Agencies



Phase 5:

Enterprise



Definir:



\* acquisition channel;

\* content;

\* GitHub;

\* demos;

\* documentation;

\* community;

\* partnerships.



\---



\# 14. PRODUCT ROADMAP FOR MONETIZATION



Separar:



NOW

NEXT

LATER



NOW:



\* stable core;

\* Lead Hunter E2E;

\* documentation;

\* GitHub;

\* API;

\* basic observability.



NEXT:



\* cloud architecture;

\* teams;

\* authentication;

\* usage metrics;

\* cost tracking;

\* BYOK;

\* premium features.



LATER:



\* billing;

\* Stripe;

\* enterprise;

\* SSO;

\* private deployments;

\* advanced governance.



No implementar billing hasta que exista product-market evidence.



\---



\# 15. VALIDATION



Diseñar experimentos para validar willingness-to-pay antes de construir una plataforma comercial completa.



Ejemplos:



\* GitHub users;

\* waitlist;

\* early access;

\* paid pilot;

\* consulting deployment;

\* design partners.



El objetivo es comprobar:



> ¿Quién pagaría?

> ¿Por qué pagaría?

> ¿Cuánto pagaría?

> ¿Qué problema considera suficientemente importante?



\---



\# 16. FINAL DELIVERABLE



Crear:



docs/business-model.md

docs/pricing-strategy.md

docs/go-to-market.md

docs/open-core-strategy.md



Y un resumen ejecutivo:



1\. ICP recomendado.

2\. Producto gratuito.

3\. Producto Cloud.

4\. Enterprise.

5\. Lead Hunter monetization.

6\. BYOK strategy.

7\. Pricing recomendado.

8\. Diferenciación.

9\. Go-to-market.

10\. Roadmap comercial.



IMPORTANTE:



No modificar código de producción durante este análisis.



No implementar Stripe.



No implementar billing.



No cambiar arquitectura.



Primero presentar las conclusiones y recomendaciones.



El objetivo es diseñar una estrategia comercial que pueda implementarse después de que Mission Control tenga un flujo E2E estable.







El orden que yo seguiría



Ahora mismo:



Mission Control → Lead Hunter → E2E → tests → estabilidad



Después:



Agent adapters → workflows → observability → governance



Después:



Open source → usuarios → feedback → primeros pilotos



Y recién entonces:



Cloud + BYOK + Team + Enterprise + Billing


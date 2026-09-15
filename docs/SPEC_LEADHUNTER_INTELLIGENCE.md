# CONCIENCIA — LEADHUNTER INTELLIGENCE ENGINE + MODULAR AGENTIC BUSINESS OS

## ROLE

Actúa como Principal Software Architect, Staff Backend Engineer, Search Engineer, Data Engineer, AI/Agent Systems Engineer y Product Engineer.

Tu misión es auditar, corregir y evolucionar el proyecto actual **Conciencia**, comenzando por el módulo **LeadHunter**, sin destruir funcionalidades existentes y sin introducir arquitectura innecesaria antes de validar el flujo end-to-end.

No asumas que la implementación actual está bien diseñada.

Primero inspecciona el código, modelos, endpoints, componentes UI, servicios, base de datos, configuración, scraping, búsqueda y flujo actual de LeadHunter.

Después diseña y ejecuta las modificaciones necesarias.

---

# 1. PRODUCT VISION

Conciencia no debe evolucionar como un simple CRM, scraper o dashboard.

La visión de largo plazo es:

> **Conciencia = AI Control Plane / Business Operating System modular para que una persona o empresa pueda configurar, operar, automatizar y extender su negocio mediante datos, agentes, workflows y módulos especializados.**

LeadHunter es el primer gran módulo de validación.

Conciencia debe poder eventualmente soportar:

* Lead generation
* Business intelligence
* CRM
* ERP
* Sales
* Marketing
* Operations
* Finance
* Inventory
* Logistics
* Procurement
* Customer support
* Project management
* Software engineering
* Data analysis
* Research
* Internal company agents
* Custom business modules
* Custom workflows
* Custom agents
* Custom tools
* Semantic search
* Structured search
* Knowledge bases
* Automation
* CLI operation
* API operation
* Web UI operation

Pero NO implementar todo ahora.

La arquitectura debe permitirlo sin convertir el producto actual en un monolito innecesariamente complejo.

---

# 2. PRINCIPLE: LEADHUNTER FIRST

La prioridad inmediata es:

> **hacer que LeadHunter sea excelente, coherente, confiable, rápido y realmente útil.**

No construir una gran arquitectura futurista que todavía no tenga un flujo funcional.

Orden obligatorio:

1. Auditar LeadHunter actual.
2. Corregir problemas de UX/UI.
3. Corregir filtros.
4. Corregir geografía.
5. Mejorar búsqueda.
6. Mejorar utilización de datos.
7. Mejorar deduplicación.
8. Mejorar scoring/relevance.
9. Mejorar resultados.
10. Probar E2E.
11. Crear CLI equivalente.
12. Extraer capacidades reutilizables.
13. Recién entonces preparar la base del sistema modular.

---

# 3. LEADHUNTER SHOULD NOT BE "JUST A SCRAPER"

Conceptualmente separar:

DATA SOURCES
↓
INGESTION
↓
NORMALIZATION
↓
ENTITY RESOLUTION
↓
ENRICHMENT
↓
INDEXING
↓
SEARCH
↓
SCORING
↓
LEAD INTELLIGENCE
↓
AGENTS
↓
WORKFLOWS
↓
ACTIONS

Una empresa encontrada no debe ser simplemente:

{
name,
address,
phone
}

Debe convertirse progresivamente en una entidad empresarial reutilizable.

Ejemplo conceptual:

Company

* identity
* legal_name
* trade_name
* website
* domain
* industry
* category
* description
* employees
* revenue_estimate
* locations
* contact_points
* emails
* phones
* social_profiles
* source_records
* source_confidence
* data_quality
* last_verified_at
* enrichment_status
* technologies
* business_signals
* keywords
* embeddings
* semantic_profile
* lead_score
* opportunity_score
* intent_signals
* notes
* relationships
* activities
* tags

La arquitectura debe permitir que nuevos campos y enriquecimientos sean agregados posteriormente sin romper todo el sistema.

---

# 4. IMPORTANT — INSPIRE FROM EXPLEE, DO NOT CLONE IT

Tomar como inspiración conceptual:

* Structured filters
* Natural language search
* Semantic company discovery
* Geographic segmentation
* Enriched company profiles
* Multiple data sources
* AI enrichment
* Relevance/scoring
* Data freshness
* Deduplication
* Search by business definition
* Search by people/job role
* Search by custom criteria
* Country/region browsing

Explee actualmente combina múltiples fuentes y utiliza perfiles enriquecidos para construir una visión más completa de una empresa. Su API también contempla convertir consultas en lenguaje natural a filtros estructurados.

NO copiar:

* código
* UI
* branding
* estructura propietaria
* datos privados
* scraping ilegal
* modelos propietarios
* funcionalidades sin entender su propósito

La inspiración debe ser arquitectónica y de producto.

---

# 5. FIX LEADHUNTER FILTERS

El panel actual de Leads presenta incoherencias entre:

* texto libre
* filtros estructurados
* ubicación
* categorías
* resultados
* configuración regional

Rediseñar el concepto.

Debe existir una separación clara:

## QUERY

Qué estoy buscando.

Ejemplo:

"playas de vehículos que vendan vehículos usados en Ciudad del Este"

## FILTERS

Qué restricciones aplican.

Ejemplo:

Country = Paraguay

Region = Alto Paraná

City = Ciudad del Este

Industry = Automotive

Category = Used Car Dealer

Has Website = true

Has Phone = true

## SORT / RANKING

Cómo ordenar.

Ejemplo:

Relevance
Lead Score
Data Completeness
Opportunity
Distance
Freshness

## SOURCE

De dónde provienen los datos.

OpenStreetMap
OpenStreetMap-derived provider
Website
Government registry
Manual
Other provider

Nunca mezclar estos conceptos en un único campo ambiguo.

---

# 6. NATURAL LANGUAGE SEARCH

LeadHunter debe soportar consultas humanas.

Ejemplos:

"Buscar playas de autos usados en Ciudad del Este"

"Empresas logísticas de Paraguay"

"Restaurantes en Alto Paraná con teléfono y página web"

"Distribuidoras de bebidas en Asunción"

"Empresas de construcción de más de 20 empleados en Paraguay"

"Concesionarias que tengan página web pero no formulario de contacto"

La consulta natural NO debe ejecutar directamente SQL arbitrario.

Pipeline:

Natural Language Query
→ Intent Parser
→ Query Object
→ Structured Filters
→ Search Engine
→ Ranking
→ Results

Crear un objeto intermedio canónico:

SearchQuery

Ejemplo conceptual:

{
"query": "playas de autos usados",
"entity_type": "business",
"country": "PY",
"region": "Alto Paraná",
"city": "Ciudad del Este",
"category": "used_car_dealer",
"required_fields": [
"phone"
],
"sort": "relevance"
}

Este objeto debe poder utilizarse desde:

* Web UI
* CLI
* API
* Agents
* Workflows

---

# 7. GEOGRAPHY MUST BE FIRST-CLASS

La API/provider geográfico actualmente es demasiado global para la UX del producto.

No eliminar la capacidad global.

En cambio implementar una capa de configuración geográfica.

Modelo:

GLOBAL
→ CONTINENT
→ COUNTRY
→ REGION/STATE/DEPARTMENT
→ CITY
→ DISTRICT
→ LOCAL AREA

Para el deployment actual:

DEFAULT COUNTRY = PARAGUAY

Pero la arquitectura debe permitir:

PARAGUAY
BRAZIL
ARGENTINA
URUGUAY
GLOBAL

sin modificar código.

---

# 8. SETTINGS — GEOGRAPHIC SCOPE

En Settings crear:

## Search Geography

Default country:

Paraguay

Default region:

Optional

Default city:

Optional

Search scope:

* City
* Region
* Country
* Multiple countries
* Global

Provider:

* OpenStreetMap
* Other supported providers

Provider restrictions:

country allowlist
region allowlist
rate limits
request limits
timeout
caching

Ejemplo:

SEARCH_DEFAULT_COUNTRY=PY

SEARCH_ALLOWED_COUNTRIES=PY,BR,AR

No hardcodear Paraguay dentro del servicio de búsqueda.

Debe ser configuración.

---

# 9. GEOGRAPHIC SAFETY / CONTROL

La interfaz NO debe permitir que una consulta accidentalmente termine haciendo:

"restaurants"

→ todo el mundo.

El sistema debe aplicar:

default geographic scope.

Ejemplo:

User:
"restaurantes"

Context:
Paraguay

Interpretation:

restaurants + Paraguay

Solamente si el usuario explícitamente selecciona "Global" se permite búsqueda mundial.

Implementar un Geographic Scope object.

---

# 10. OSM / PROVIDER ABSTRACTION

No acoplar LeadHunter directamente al proveedor geográfico.

Crear una abstracción:

GeoProvider

con capacidades como:

* search_places()
* geocode()
* reverse_geocode()
* resolve_region()
* resolve_country()
* resolve_city()

Crear adapter:

OpenStreetMapProvider

Posteriormente:

GoogleMapsProvider
MapboxProvider
HereProvider
CustomProvider

sin alterar el Search Engine.

Respetar rate limits, caching, attribution y políticas de uso del proveedor.

No implementar mecanismos para evadir límites o restricciones del proveedor.

---

# 11. DATA SOURCE ABSTRACTION

Crear conceptualmente:

DataSource

Tipos:

* GeoSource
* WebSource
* RegistrySource
* ManualSource
* APIDataSource
* ImportedDataset
* InternalDatabase

Cada registro debe mantener provenance:

source
source_id
source_url
retrieved_at
last_verified_at
confidence
provider

No destruir información de origen durante la normalización.

---

# 12. ENTITY RESOLUTION

El mismo negocio puede aparecer:

* en OpenStreetMap
* website
* directorio
* registro
* importación
* CRM

No mostrar duplicados.

Crear un sistema de:

Entity Resolution

Matching signals:

* domain
* phone
* normalized company name
* address
* coordinates
* email
* tax/legal identifier
* source IDs

Resultado:

Canonical Business Entity

con múltiples Source Records.

---

# 13. SEARCH ENGINE

Separar claramente:

Database filtering

de

Semantic search

de

Ranking.

Idealmente soportar:

1. Exact filters
2. Full-text search
3. Semantic search
4. Hybrid search
5. Ranking

Ejemplo:

"empresas de logística que probablemente necesiten software de gestión de flotas"

Esto no es simplemente un WHERE SQL.

Debe poder utilizar:

keywords
embeddings
business profile
signals
metadata
filters
AI classification

---

# 14. SEMANTIC SEARCH

Preparar arquitectura para embeddings.

Entidad:

BusinessDocument

Campos:

business_id
text
embedding
metadata

Metadata:

country
region
city
industry
category
size
source
status

Vector backend debe ser abstracto.

Puede comenzar con:

Postgres + pgvector

y evolucionar posteriormente a:

Qdrant
Weaviate
Milvus
otro proveedor

NO introducir un vector database externo si PostgreSQL + pgvector cubre correctamente la fase actual.

---

# 15. INTELLIGENT RANKING

Los resultados no deben ser simplemente ordenados por fecha.

Crear un Search Score compuesto.

Ejemplo conceptual:

score =
semantic_relevance

* category_match
* geographic_match
* data_completeness
* website_presence
* contactability
* freshness
* business_signals

No asumir pesos arbitrarios permanentemente.

Crear configuración:

RankingWeights

para que el administrador pueda modificarlos.

---

# 16. LEAD SCORE

Separar:

Search Relevance

de

Lead Score

de

Opportunity Score

Ejemplo:

Search Relevance:
92%

Lead Score:
81

Opportunity Score:
74

Porque una empresa puede ser muy relevante para la búsqueda pero no ser comercialmente buena.

---

# 17. AI ENRICHMENT

La plataforma debe poder posteriormente ejecutar enrichment agents.

Ejemplos:

CompanyResearchAgent

BusinessClassificationAgent

ContactDiscoveryAgent

WebsiteAnalyzerAgent

TechnologyDetectionAgent

LeadScoringAgent

OpportunityDetectionAgent

CRMResearchAgent

Estos agentes NO deben vivir dentro del componente LeadHunter.

Deben utilizar una capa genérica:

AgentRuntime

con:

Agent
Model
Tool
Context
Task
Run
Result

---

# 18. AGENTS AS FIRST CLASS OBJECTS

Un agente debe ser configurable.

Ejemplo:

Agent:

"Automotive Market Researcher"

Role:

Research companies related to automotive.

Tools:

web_search
database_search
website_fetch
semantic_search
crm

Output schema:

CompanyResearchReport

Otro:

"Lead Qualification Agent"

Inputs:

Lead

Outputs:

QualificationResult

Otro:

"Software Engineer Agent"

Tools:

filesystem
git
terminal
python
database
browser/API

---

# 19. CLI IS NOT AN AFTERTHOUGHT

Crear una interfaz CLI de Conciencia.

Ejemplos:

conciencia search "playas de autos usados" --country PY

conciencia leads search "empresas logísticas" --region "Alto Paraná"

conciencia leads export --format csv

conciencia company inspect <id>

conciencia company enrich <id>

conciencia search semantic "empresas con potencial para software de logística"

conciencia agent list

conciencia agent run lead-qualifier

conciencia workflow list

conciencia workflow run sales-prospecting

conciencia module list

conciencia config get

conciencia config set search.country PY

El CLI debe consumir los mismos servicios internos que la Web UI.

NO crear un segundo backend para CLI.

Arquitectura:

CLI
↓
Application Services
↓
Domain
↓
Infrastructure

Web:
Web UI
↓
API/Application Services
↓
Domain
↓
Infrastructure

Agent:
Agent Runtime
↓
Application Services
↓
Domain
↓
Infrastructure

---

# 20. CONCIENCIA CORE

Preparar conceptualmente un núcleo reutilizable:

Conciencia Core

Responsabilidades:

* Identity
* Configuration
* Modules
* Data
* Search
* Agents
* Tools
* Workflows
* Events
* Permissions
* Audit
* Notifications

No implementar todos los subsistemas inmediatamente.

Crear interfaces y boundaries limpios.

---

# 21. MODULE SYSTEM

Conciencia debe poder crecer mediante módulos.

Ejemplo:

modules/
leadhunter/
crm/
erp/
logistics/
sales/
marketing/
finance/
inventory/
support/
projects/
software-engineering/

Cada módulo debería tener:

manifest
routes
models
services
permissions
commands
agents
workflows
settings
ui

Conceptualmente:

ModuleManifest

{
id,
name,
version,
description,
dependencies,
capabilities,
permissions
}

---

# 22. CONFIGURABLE FROM ZERO

Un dueño de negocio debe poder comenzar con un Conciencia vacío.

Ejemplo:

Create Workspace

↓

"What type of business do you operate?"

↓

Automotive

↓

Configure:

Customers
Vehicles
Sales
Purchases
Inventory
Employees
Finance
Leads

↓

Conciencia configura módulos recomendados.

Pero el usuario debe poder:

enable
disable
configure
extend
create

módulos.

---

# 23. BUSINESS EXAMPLE: CAR DEALERSHIP

Para una playa de automotores:

Modules:

CRM
Vehicles
Inventory
Sales
Purchases
Leads
Marketing
Finance
Documents

Agents:

LeadHunterAgent
VehicleResearchAgent
SalesAssistantAgent
CustomerQualificationAgent
PricingAgent
MarketingAgent

Workflows:

NewLead
VehicleAcquisition
VehicleSale
FollowUp
CustomerReactivation

---

# 24. BUSINESS EXAMPLE: SOFTWARE DEVELOPER

Para un desarrollador:

Modules:

Projects
Clients
CRM
Sales
Billing
Tasks
Software Engineering
Repositories
Documentation

Agents:

CodingAgent
ResearchAgent
QAAgent
DocumentationAgent
SalesAgent
ProposalAgent

El desarrollador debe poder:

crear software
gestionar clientes
hacer propuestas
seguir leads
facturar
administrar proyectos

desde el mismo sistema.

---

# 25. SOFTWARE ENGINEERING MODE

Conciencia debe poder convertirse también en un workspace de ingeniería.

Conceptualmente:

PROJECT
↓
REPOSITORY
↓
ISSUE
↓
TASK
↓
AGENT
↓
TOOL
↓
WORKFLOW
↓
CODE
↓
TEST
↓
DEPLOY

Tools:

Git
GitHub
Terminal
Python
Node
Docker
Databases
HTTP
Browser
Filesystem

Agents:

Developer
Reviewer
QA
DevOps
Researcher
Architect

Esto NO significa construir un IDE ahora.

Significa que el core debe permitir esos módulos posteriormente.

---

# 26. CRM / ERP SHOULD BE MODULES

No hacer:

Conciencia = CRM + ERP + LeadHunter + IDE.

Hacer:

Conciencia Core

*

Modules.

Ejemplo:

Conciencia
├── Core
├── LeadHunter
├── CRM
├── ERP
├── Logistics
├── Software Engineering
└── Custom Modules

Esto evita acoplamiento.

---

# 27. AGENT + MODULE INTERACTION

Un agente debe poder utilizar módulos.

Ejemplo:

SalesAgent

Capabilities:

crm.read
crm.write
leads.search
leads.score
email.send
calendar.create

Otro:

FinanceAgent

Capabilities:

invoices.read
payments.read
reports.generate

Otro:

DeveloperAgent

Capabilities:

repo.read
repo.write
terminal.execute
tests.run

Esto conduce naturalmente a un sistema:

Agent → Capabilities → Tools → Modules → Data

---

# 28. PERMISSIONS

No permitir acceso global automáticamente.

Cada Agent debe tener:

permissions

Cada Module:

permissions

Cada Tool:

permissions

Ejemplo:

LeadHunterAgent

ALLOW:
leads.read
search.execute

DENY:
finance.write

Esto será importante para seguridad futura.

---

# 29. AUDITABILITY

Toda acción significativa debe poder registrar:

who
agent
user
module
tool
action
input_reference
result
timestamp
cost
status

No guardar secretos ni información sensible innecesaria en logs.

---

# 30. DATABASE STRATEGY

No introducir múltiples bases de datos sin necesidad.

Preferencia inicial:

PostgreSQL

Usar:

relational data
JSONB
full text
pgvector

cuando sea apropiado.

Modelo conceptual:

Core tables

users
workspaces
modules
settings
agents
tools
workflows
runs
events

LeadHunter tables

companies
locations
contacts
sources
source_records
searches
search_results
lead_scores
enrichment_runs
embeddings

Posteriormente otros módulos pueden introducir:

customers
vehicles
invoices
products
projects
repositories

pero cada módulo debe controlar su dominio.

---

# 31. ADMIN / SETTINGS

El administrador debe poder modificar sin cambiar código:

Default country
Allowed countries
Default region
Search providers
Provider limits
Search ranking weights
Lead scoring weights
AI models
Embedding model
Data refresh intervals
Enrichment policies
Enabled modules
Enabled agents
Agent permissions
Feature flags

---

# 32. UX PRINCIPLE

La interfaz no debe sentirse como:

"un formulario con 30 filtros".

Debe sentirse como:

"un sistema inteligente para encontrar y entender negocios".

Ideal flow:

Search

"What are you looking for?"

↓

Natural language input

↓

AI interprets query

↓

Shows interpreted filters

↓

User can edit filters

↓

Search

↓

Ranked results

↓

Business profile

↓

Sources

↓

Insights

↓

Actions

↓

Save to CRM

↓

Enrich

↓

Assign agent

↓

Create workflow

---

# 33. LEAD DETAIL

Cada lead debe poder mostrar:

Overview
Contact
Location
Business category
Website
Sources
Data quality
Confidence
Signals
AI summary
Why this lead matches
Lead score
Opportunity score
Related businesses
Similar businesses
Search history
Activities
CRM status
Agents
Enrichment history

---

# 34. "WHY THIS RESULT?"

Una característica importante.

Cuando aparezca una empresa:

mostrar:

"Why this lead matches"

Ejemplo:

92% relevance because:

* Automotive business
* Used vehicle dealership
* Located in Ciudad del Este
* Website detected
* Phone detected
* Relevant business description
* Matches requested category

Esto aumenta la confianza del usuario.

---

# 35. DATA QUALITY

Cada entidad debe tener:

Data Quality Score

basado en:

completeness
freshness
source reliability
consistency
verification

Ejemplo:

Data Quality: 87/100

No presentar datos como hechos absolutos cuando son inferidos.

Distinguir:

Observed
Extracted
Inferred
AI-generated
User-provided

---

# 36. SEARCH CACHE

Evitar consultas repetidas innecesarias.

Implementar caching donde sea apropiado.

Cache:

geocoding
provider responses
search queries
semantic embeddings
enrichment results

Con TTL configurable.

---

# 37. PAGINATION / LARGE DATASETS

Nunca cargar miles de resultados al frontend.

Usar:

cursor pagination

cuando sea posible.

Separar:

search
ranking
pagination
export.

---

# 38. EXPORTS

LeadHunter debe permitir:

CSV
JSON
API

Posteriormente:

CRM import
Webhook
Workflow
Agent input

---

# 39. TESTING

Crear tests para:

Query parsing
Geography restrictions
Country default
Provider adapters
Deduplication
Entity resolution
Search filters
Semantic search
Ranking
Lead score
Pagination
CLI
API
Database
Permissions

Crear al menos un flujo E2E:

User enters:

"playas de autos usados"

Country:

Paraguay

Region:

Alto Paraná

↓

Search

↓

Provider

↓

Normalization

↓

Deduplication

↓

Database

↓

Ranking

↓

UI

↓

Lead detail

Debe funcionar realmente.

---

# 40. SEARCH BENCHMARK

Crear un pequeño dataset de prueba.

Ejemplos:

Query:

"playas de autos usados en Ciudad del Este"

Expected categories:

used_car_dealer
car_dealer
automotive

Expected geography:

Paraguay
Alto Paraná
Ciudad del Este

Query:

"empresas logísticas en Paraguay"

Expected:

logistics
transport
freight
shipping

Medir:

precision
recall aproximado
duplicates
false positives
latency
data completeness

---

# 41. CLI TESTS

Debe existir:

conciencia health

conciencia search "playas de autos usados" --country PY

conciencia search "empresas logísticas" --country PY --region "Alto Paraná"

conciencia company list

conciencia company inspect <id>

conciencia leads score <id>

conciencia agent list

conciencia module list

Los mismos resultados importantes deben ser producidos por el mismo dominio que la Web UI.

---

# 42. ARCHITECTURE PRINCIPLE

Preferir:

Domain
Application
Infrastructure
Interfaces

en lugar de:

Frontend-specific logic
Backend-specific duplicated logic
CLI-specific logic

La lógica de negocio debe ser reutilizable.

---

# 43. FUTURE AGENTIC ARCHITECTURE

Preparar estas abstracciones:

Agent
Model
Tool
Capability
Context
Task
Workflow
Run
Memory
Knowledge
Event
Approval

Conceptualmente:

Agent
↓
Task
↓
Context
↓
Tools
↓
Modules
↓
Data
↓
Result
↓
Event

Pero implementar únicamente las piezas necesarias para LeadHunter actualmente.

---

# 44. COMMAND BAR

Preparar conceptualmente una interfaz transversal:

⌘K / Ctrl+K

Ejemplos:

"Search logistics companies in Paraguay"

"Create a lead list"

"Analyze this company"

"Enrich these 20 leads"

"Create CRM workflow"

"Run LeadHunter"

"Show companies with no website"

"Create a research agent"

No convertir esto simplemente en un chatbot.

Debe ser un Command Interface capaz de ejecutar acciones reales.

---

# 45. AGENTIC SEARCH

En el futuro una consulta puede generar un workflow.

Example:

"Find 100 logistics companies in Paraguay that probably need fleet management software."

Conciencia:

1. Parse objective
2. Determine geography
3. Search
4. Deduplicate
5. Enrich
6. Analyze websites
7. Detect fleet-related signals
8. Score
9. Rank
10. Present results
11. Optionally send to CRM

LeadHunter becomes an executable intelligence workflow.

---

# 46. PRODUCT PRINCIPLE

The product should answer:

"What can Conciencia do for me?"

not:

"Which menu should I open?"

Therefore modules, agents and data should converge around:

OBJECTIVE → PLAN → EXECUTION → RESULT

instead of:

FORM → SUBMIT → TABLE

---

# 47. IMPORTANT SCOPE CONTROL

DO NOT:

* rewrite the entire project
* replace the stack unnecessarily
* introduce microservices unnecessarily
* introduce Kubernetes
* introduce multiple databases without need
* create dozens of abstractions without implementation value
* build CRM/ERP now
* build a complete IDE now
* build autonomous agents before LeadHunter works
* break existing functionality
* remove working features without evidence

DO:

* inspect first
* preserve working code
* refactor incrementally
* isolate domain boundaries
* improve LeadHunter
* build reusable application services
* add tests
* document architecture
* expose reusable services to CLI/API/UI

---

# 48. REQUIRED AUDIT BEFORE CHANGES

Before modifying code, produce:

## Current architecture

frontend
backend
database
search
scraping
providers
AI
authentication
settings

## Current LeadHunter flow

Input
→ filters
→ API
→ provider
→ database
→ ranking
→ frontend

## Current problems

Identify:

bugs
inconsistencies
duplicated logic
hardcoded geography
provider coupling
missing caching
poor data modeling
missing deduplication
poor ranking
UI confusion
missing validation

## Proposed architecture

Show:

BEFORE

and

AFTER

Do not implement the future architecture until identifying exactly which current components require modification.

---

# 49. IMPLEMENTATION PRIORITY

Priority 0

Audit.

Priority 1

LeadHunter correctness.

Priority 2

Geographic scoping.

Priority 3

Search/filter consistency.

Priority 4

Data normalization and deduplication.

Priority 5

Ranking/scoring.

Priority 6

Semantic search foundation.

Priority 7

CLI.

Priority 8

Core module boundaries.

Priority 9

Agent abstractions.

Priority 10

CRM/ERP/software-engineering modules later.

---

# 50. DEFINITION OF DONE

LeadHunter is considered improved only when:

[ ] Search works end-to-end.

[ ] Country defaults correctly to Paraguay.

[ ] Geographic scope is configurable.

[ ] User cannot accidentally query the entire world.

[ ] Natural language query works.

[ ] Structured filters remain editable.

[ ] Search and filters do not contradict each other.

[ ] OpenStreetMap/provider access is abstracted.

[ ] Provider limits are respected.

[ ] Results are normalized.

[ ] Duplicates are reduced.

[ ] Search relevance is ranked.

[ ] Lead Score is independent from search relevance.

[ ] Data quality is visible.

[ ] Source/provenance is preserved.

[ ] Semantic search foundation exists.

[ ] Search can eventually be reused by agents.

[ ] CLI uses the same application services.

[ ] API and UI use the same search logic.

[ ] Tests cover critical behavior.

[ ] Existing functionality is not unnecessarily broken.

---

# 51. FINAL ARCHITECTURAL TARGET

The long-term system should conceptually become:

```
                     CONCIENCIA
                          │
                ┌─────────┴─────────┐
                │   CONCIENCIA CORE │
                └─────────┬─────────┘
                          │
    ┌──────────────┬──────┼──────┬──────────────┐
    │              │      │      │              │
  DATA          SEARCH   AGENTS WORKFLOWS     MODULES
    │              │      │      │              │
    │              │      │      │       ┌──────┼────────┐
    │              │      │      │       │      │        │
```

PostgreSQL      Hybrid   Runtime Events  CRM  ERP   LEADHUNTER

* pgvector      Search
  │
  ├── Companies
  ├── Contacts
  ├── Businesses
  ├── Sources
  ├── Knowledge
  └── Embeddings

Interfaces:

WEB
CLI
API
AGENTS
WORKFLOWS

Everything should converge into the same domain/application layer.

---

# 52. MOST IMPORTANT PRODUCT TEST

After implementation, ask:

Can a user type:

"Find vehicle dealerships in Alto Paraná that have a website, phone number and appear to be active businesses."

and have Conciencia:

1. Understand the request.
2. Infer Paraguay from workspace settings.
3. Convert it into structured filters.
4. Search available sources.
5. Normalize results.
6. Deduplicate companies.
7. Rank them.
8. Explain why each result matches.
9. Show data quality.
10. Allow enrichment.
11. Save them to LeadHunter.
12. Send them to CRM later.
13. Execute the exact same operation through CLI.
14. Allow an agent to perform the same operation through tools.

If this works, LeadHunter is no longer merely a scraper.

It is the first real manifestation of the Conciencia platform.

---

# 53. EXECUTION MODE

Now inspect the existing repository.

DO NOT immediately rewrite code.

First identify:

* stack
* current architecture
* current LeadHunter implementation
* search pipeline
* geographic provider
* database schema
* settings implementation
* API endpoints
* frontend filters
* CLI status
* existing tests

Then generate:

1. Architecture audit.
2. Problems found.
3. Minimal-change implementation plan.
4. Files/components to modify.
5. Database migrations required.
6. API changes.
7. UI changes.
8. CLI changes.
9. Tests.
10. E2E validation.

Only after that implement the changes.

The objective is not to make Conciencia theoretically impressive.

The objective is to make LeadHunter work exceptionally well while creating the correct foundation for the larger Conciencia system.

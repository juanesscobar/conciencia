# CONCIENCIA — WORKSPACE INTELLIGENCE, SEMANTIC WORK SEARCH & REPORTING

We have completed another real CLI dogfooding cycle.

Do NOT perform a broad rewrite.

The next product objective is to make Conciencia useful as a persistent operational workspace capable of answering questions about the user's own work, producing evidence-backed work summaries/reports, and later delivering approved reports to external systems such as LINTEAM.

---

## 0. Current observed state

The CLI now successfully exposes:

```text
Workspace home
Projects
Missions
Approvals
Runtimes
Models
Doctor
Teams
Harnesses
Signals
Context Packs
WebMCP
Economics
```

Runtime/model health semantics have improved significantly.

Current semantic capability is still effectively disabled for workspace use:

```text
Embeddings: disabled
```

Current semantic search appears oriented mainly toward LeadHunter.

This phase must make semantic retrieval a CORE workspace capability.

Do not remove LeadHunter semantic search. Reuse/generalize its infrastructure where appropriate.

---

# 1. PRODUCT OBJECTIVE

Conciencia should answer questions such as:

```text
"What did I develop since August 27?"

"What did we implement for the WebMCP Challenge?"

"What changed in Conciencia this week?"

"Show me the most important architecture decisions."

"What deployments did we perform?"

"What work remains unfinished?"

"Prepare a complete report of everything developed for LIN Group."
```

These are NOT necessarily new Research Missions.

They should normally retrieve and synthesize existing workspace evidence first.

Architecture:

```text
User Question
     ↓
Intent Classification
     ↓
Workspace Retrieval
     ↓
Semantic + Temporal + Structured Search
     ↓
Relevant Evidence
     ↓
Context Pack
     ↓
Answer / Summary / Report
```

Only create an external Research Mission when the request genuinely requires new external research.

---

# 2. WORK AS A FIRST-CLASS DOMAIN

Add a lightweight `Work` domain.

Do NOT use `Team` for this.

Team remains a group of Agents.

Conceptually:

```text
Workspace
 ├── Projects
 ├── Work
 ├── Missions
 ├── Knowledge
 ├── Reports
 └── Connections
```

Work represents what actually happened across technological activity.

---

# 3. WORK ACTIVITY LEDGER

Introduce a durable Work Activity / Activity Ledger abstraction.

Minimum model:

```text
WorkActivity

id
workspace_id
project_id optional
type
title
summary
timestamp
source_type
source_ref
metadata
entities
tags
evidence_refs
created_at
```

Initial event types may include:

```text
git.commit
git.branch
mission.created
mission.completed
mission.failed
run.completed
run.failed
approval
decision
finding
signal
evidence
deployment
test.result
report.created
document.created
work.note
```

Do not automatically store noisy low-value events.

Prefer meaningful, traceable work events.

---

# 4. ACTIVITY INGESTION

Create an extensible ingestion layer.

Initial sources:

```text
Git history
Mission database
Mission runs
Signals
Evidence
Approvals
Reports/documents already managed by Conciencia
Project metadata
```

For Git, support date-bounded extraction:

```text
since
until
project/repository
branch
author when useful
```

Do not fabricate work from Git commits.

Preserve commit hash as evidence/provenance.

Future sources may include OpenClaw/Codex history or external systems, but DO NOT overbuild those integrations now.

---

# 5. CORE SEMANTIC INDEX

Generalize semantic retrieval beyond LeadHunter.

Create/reuse one interface such as:

```text
SemanticIndex
EmbeddingProvider
SemanticDocument
SemanticSearchResult
```

Semantic documents may represent:

```text
Project
Mission
MissionRun
WorkActivity
Evidence
Signal
Decision
Document
Report
GitCommit
Knowledge item
```

Required metadata:

```text
entity_type
entity_id
workspace_id
project_id
timestamp
source
provenance
```

Semantic results must always retain a link to their original source.

---

# 6. EMBEDDING PROVIDERS

Do not hard-code OpenAI.

Use provider abstraction.

Support at least:

```text
real provider when configured
safe local/simulated fallback where already supported
```

Evaluate existing embedding infrastructure before creating anything new.

If pgvector already exists or is planned in the current architecture, reuse it.

Do not create a second vector architecture.

Expose readiness in:

```bash
conciencia doctor
conciencia health
```

Example:

```text
Semantic search
provider     ...
index        ready
documents    1,284
status       READY
```

---

# 7. HYBRID RETRIEVAL

Workspace retrieval should combine:

```text
semantic similarity
keyword/full-text search
time filters
project filters
entity filters
structured metadata
```

Example:

```text
query = "WebMCP work"
since = 2026-08-27
project = Conciencia
```

Do not rely solely on vector similarity.

---

# 8. WORK CLI

Add a coherent command family:

```bash
conciencia work
conciencia work timeline
conciencia work search "webmcp"
conciencia work summarize
conciencia work inspect <activity>
```

Useful flags:

```text
--since
--until
--project
--type
--limit
--json
```

Example:

```bash
conciencia work summarize \
  --since 2026-08-27
```

Natural language must also work:

```bash
conciencia ask
> resumime todo lo que desarrollé desde el 27 de agosto hasta hoy
```

---

# 9. WORK SUMMARY

Create a WorkSummary service.

The summary must be evidence-backed.

Possible structure:

```text
Period
Projects touched
Major accomplishments
Features implemented
Architecture changes
Bugs/failures discovered
Bugs/failures resolved
Tests/validation
Deployments
Documents/deliverables
Important decisions
Pending work
Risks
Next steps
Evidence
```

Do NOT invent counts or achievements.

If evidence is incomplete, explicitly say so.

---

# 10. ASK INTENT ROUTING

Improve `conciencia ask`.

Distinguish at least:

```text
workspace_query
workspace_summary
external_research
mission_request
action_request
```

Example:

```text
"How are we doing with the WebMCP missions?"
→ workspace_query

"What did we build for WebMCP?"
→ workspace_summary / retrieval

"Research the current official WebMCP Challenge requirements"
→ external_research

"Implement WebMCP support"
→ mission_request
```

Workspace questions should not automatically create new Research Missions.

---

# 11. REPORTS

Add/reuse a first-class Report concept.

CLI target:

```bash
conciencia report list
conciencia report create
conciencia report inspect <id>
conciencia report export <id>
```

Support generation from WorkSummary.

Example:

```bash
conciencia report create \
  --from-work \
  --since 2026-08-27 \
  --project conciencia
```

Possible formats initially:

```text
markdown
json
```

Add PDF only if an existing safe report/PDF path can be reused without scope explosion.

Report must preserve supporting Evidence references.

---

# 12. LINTEAM — ARCHITECTURE ONLY / MINIMAL CONNECTOR FOUNDATION

Prepare a generic Connection / Connector abstraction.

Do NOT hard-code LINTEAM into Mission core.

Concept:

```text
Connection
Connector
Credentials reference
Capabilities
Tools
```

Potential connector types:

```text
rest-api
mcp
webmcp
webhook
```

LINTEAM may later expose tools such as:

```text
linteam.pipeline.list
linteam.pipeline.get
linteam.ticket.create
linteam.ticket.update
linteam.deliverable.create
linteam.comment.create
```

For this phase:

1. Inspect whether a generic connector abstraction already exists.
2. Reuse MCP/Tool Registry patterns where possible.
3. Define the minimal extension point.
4. Do NOT call production LINTEAM until API contract/auth is explicitly configured.
5. Never expose API tokens.

---

# 13. FUTURE TARGET FLOW

The architecture must support:

```text
Work Activity
     ↓
Workspace Retrieval
     ↓
Work Summary
     ↓
Report Mission
     ↓
Report
     ↓
Human Approval
     ↓
LINTEAM Connector
     ↓
Pipeline / Deliverable
     ↓
Evidence
```

Publishing externally MUST require approval by default.

---

# 14. WORKSPACE HOME

Evolve root `conciencia` minimally.

Do not build a giant TUI.

Add only useful Work visibility, for example:

```text
Current workspace
Current project

Active missions
Pending approvals

Work this week
12 meaningful activities
3 projects
1 deployment

Recent work
...

Actions
ask | work | mission | reports | approvals
```

Only show counts that can be reliably derived.

---

# 15. CONTEXT MODEL

Keep strict separation:

```text
Knowledge
= durable reference information

Work
= what actually happened

Memory
= reusable decisions/corrections/preferences/history

Context Pack
= bounded subset assembled for one Mission
```

Do not merge all four into one storage model.

---

# 16. SECURITY & PROVENANCE

Every synthesized claim should be traceable where practical.

Sources may include:

```text
commit
mission
run
signal
evidence
report
document
project metadata
```

External publication must require approval.

Secrets must never be placed into semantic documents, embedding payloads, reports, logs, Evidence or CLI output.

Apply secret redaction before indexing.

---

# 17. DOGFOOD TEST

After implementation run this against Conciencia itself.

### Test A

```bash
conciencia work summarize --since 2026-08-27
```

It must produce an evidence-backed summary of actual work.

### Test B

```bash
conciencia ask
```

Prompt:

```text
resumime todo lo que desarrollé desde el 27 de agosto hasta hoy
```

Expected:

```text
workspace retrieval
NOT unnecessary external research mission
```

### Test C

```bash
conciencia work search "WebMCP Challenge"
```

It should find relevant Missions, commits, Evidence, reports/documents and activity even when exact wording differs.

### Test D

Ask:

```text
¿Qué hicimos para integrar WebMCP?
```

Answer must cite/refer to workspace evidence.

### Test E

Ask:

```text
Investigá los requisitos oficiales actuales del WebMCP Challenge
```

This SHOULD resolve to an external research Mission.

---

# 18. IMPLEMENTATION ORDER

Proceed incrementally:

```text
A. Audit existing search/context/embedding infrastructure
B. WorkActivity domain
C. Git + Mission activity ingestion
D. Core SemanticIndex abstraction
E. Workspace hybrid retrieval
F. work CLI
G. ask workspace-query routing
H. WorkSummary
I. Reports
J. Connector extension point
```

Do not implement LINTEAM production writes yet.

First prove:

```text
WORK → SEARCH → SUMMARY → REPORT
```

---

# DEFINITION OF DONE

This phase is complete when I can run:

```bash
conciencia ask
```

and ask:

```text
"Resumime lo más completo posible todo lo que desarrollé
desde el 27 de agosto hasta hoy."
```

and Conciencia:

1. understands that this is a workspace-history request;
2. searches actual work across projects;
3. uses semantic + temporal retrieval;
4. retrieves Missions, Git history, Evidence and relevant documents;
5. produces a structured evidence-backed summary;
6. clearly distinguishes known facts from gaps;
7. can persist the result as a Report;
8. does not create a pointless external Research Mission;
9. does not expose secrets;
10. keeps the architecture ready for an approved LINTEAM delivery connector.

Before implementation, report:

* existing components to reuse;
* schema changes;
* semantic-index strategy;
* ingestion strategy;
* CLI changes;
* migration risks;
* test plan.

Then implement in small coherent increments.

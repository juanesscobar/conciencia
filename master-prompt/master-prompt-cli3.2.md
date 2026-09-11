# CONCIENCIA — OPERATIONAL WORKSPACE HOME

We are changing the CLI from a collection of commands into the operational entry point for the user's entire AI/software workspace.

Do NOT rebuild existing capabilities.

Existing capabilities already include:

* Projects
* Work history
* workspace retrieval
* Ask routing
* Reports
* Missions / Runs
* Agents
* Teams
* Harnesses
* ContextPacks
* Approvals
* Runtimes
* Models
* Tools / MCP
* WebMCP
* Economics
* Git discovery
* Work → ContextPack
* runtime detection/readiness

Reuse them.

The problem is PRODUCT COHERENCE.

Running:

```bash
conciencia
```

must answer:

1. What am I working on?
2. What projects exist?
3. What AI runtimes/tools are available?
4. What is running?
5. What requires my attention?
6. What did I recently accomplish?
7. What should I do next?
8. What external systems are connected?
9. How can Conciencia automate my work?

---

# 1. WORKSPACE HOME

Replace the current root behavior with a real Workspace Home.

It must work from:

```text
~
any project
any repository
outside a repository
```

Do NOT require `.conciencia/project.yaml` to show the global workspace.

Local project context is additive.

Target information architecture:

```text
CONCIENCIA
Workspace status

CURRENT CONTEXT

PROJECTS

AI WORKFORCE

ACTIVE WORK

NEEDS ATTENTION

RECENT WORK

CONNECTIONS

RECOMMENDED

QUICK ACTIONS
```

Keep it concise.

Do not dump Work summaries, raw evidence, UUIDs or logs.

---

# 2. CURRENT CONTEXT

When inside a registered project show:

```text
Current
Conciencia
branch: v2-refactor
dirty/clean
last activity
active Missions
```

When outside a project:

```text
Current
Global workspace
```

Do NOT show "Not initialized" as if Conciencia cannot operate globally.

Initialization is a project capability, not a prerequisite for Workspace Home.

---

# 3. PROJECT PORTFOLIO

Show recent/active projects.

Each project may expose:

```text
name
short description
status
last activity
active Mission count
attention indicator
```

Descriptions must come from existing Project metadata/context when available.

Do not invent descriptions.

If description is unavailable:

```text
description unavailable
```

Keep root output to approximately 3–5 projects.

Full list:

```bash
conciencia project
```

---

# 4. AI WORKFORCE

Surface the existing runtime readiness system directly on Home.

At minimum show detected/configured state for:

```text
Codex
Claude Code
OpenClaw
Generic
MCP
```

Example:

```text
AI WORKFORCE

Codex        ready
Claude Code  detected · disabled
OpenClaw     ready
Generic      DeepSeek · ready
```

Use the canonical Runtime/Model readiness services.

DO NOT create a second readiness implementation.

Never infer ready merely because a binary exists.

---

# 5. ACTIVE WORK

Show a small operational view of:

```text
active Missions
running Runs
waiting approvals
failed/recently blocked work
```

Maximum ~5 entries.

Prioritize:

```text
running
waiting approval
blocked
failed
draft
```

Do not display historical noise.

---

# 6. NEEDS ATTENTION

Build a deterministic recommendation/attention service.

Start with rules, NOT an LLM.

Possible signals:

```text
pending approvals
failed Mission
blocked Runtime
dirty repository
tests failing
semantic embeddings unavailable
Mission without success criteria
Mission waiting too long
recent work without report
project inactive with pending Mission
```

Return:

```text
severity
reason
source
recommended_action
command
```

Levels:

```text
INFO
RECOMMENDED
WARNING
```

No silent mutations.

---

# 7. RECOMMENDATIONS

Recommendations must be actionable.

Bad:

```text
Improve your workflow.
```

Good:

```text
4 approvals are waiting.
→ conciencia approvals
```

Good:

```text
Workspace retrieval is lexical because embeddings are unavailable.
→ conciencia doctor
```

Good:

```text
Conciencia has recent work not included in today's report.
→ conciencia report create --today --project Conciencia
```

Recommendations should explain WHY.

Maximum 3–5 recommendations.

---

# 8. QUICK ACTIONS

Provide discoverability without making root an interactive TUI yet.

Example:

```text
QUICK ACTIONS

Ask             conciencia ask
Work            conciencia work
Projects        conciencia project
Missions        conciencia mission
Runtimes        conciencia runtime
Approvals       conciencia approvals
Connections     conciencia connection
```

Do not implement a large TUI.

A future command palette can come later.

---

# 9. INTRODUCE CONNECTIONS AS FIRST-CLASS ABSTRACTION

Create a minimal generic Connection/Connector registry.

Do NOT hardcode LINTEAM into core orchestration.

Concept:

```text
Connection

id
name
type
status
capabilities
config_reference
last_check
```

Initial connection types may represent:

```text
REST API
MCP
WebMCP
Webhook
```

Credentials must remain outside Work, Reports, logs and semantic indexes.

Never print secrets.

CLI:

```bash
conciencia connection
conciencia connection inspect <name>
conciencia connection doctor <name>
```

If `connections` or equivalent infrastructure already exists, extend it instead of duplicating it.

---

# 10. LINTEAM ADAPTER — CONTRACT FIRST

Do NOT perform production writes yet.

Create the connector boundary necessary for a future LINTEAM adapter.

Desired capabilities:

```text
linteam.task.create
linteam.task.update
linteam.report.publish
linteam.deliverable.create
linteam.comment.create
```

But only implement these if an actual LINTEAM API contract exists.

Otherwise expose:

```text
LINTEAM
status: contract_required
```

Do not invent endpoints.

Do not invent authentication.

Do not modify LINTEAM.

---

# 11. EXTERNAL WRITE GOVERNANCE

All external writes must pass through existing approval/governance infrastructure.

Target:

```text
Work
 ↓
Report
 ↓
External Action Proposal
 ↓
Human Approval
 ↓
Connector
 ↓
External System
 ↓
Evidence
```

Example future command:

```bash
conciencia report publish latest --to linteam
```

must preview:

```text
destination
action
payload summary
risk
```

before external mutation.

No external write during this phase unless explicitly using a test/mock connector.

---

# 12. REPORT UX

Improve report ergonomics using existing Report implementation.

Support, if consistent with current architecture:

```bash
conciencia report today
conciencia report week
conciencia report create --since ...
```

Do not implement PDF unless there is already a safe document-generation path.

Markdown/TXT/JSON are enough for CLI-first dogfood.

Reports should summarize outcomes, not dump evidence.

Evidence remains linked/provenanced.

---

# 13. ASK AS WORKSPACE COMMAND BAR

Update help text and behavior conceptually.

`ask` is no longer accurately described only as:

"Texto natural → propuesta de misión."

It already routes workspace queries without creating Missions.

Represent it as the natural-language command bar for Conciencia.

Possible intents:

```text
workspace_query
workspace_summary
project_inspect
work_search
report_request
status_query
recommendation_query
mission_request
external_action_request
```

Do NOT turn Ask into an unrestricted chatbot.

Every actionable request must map to a Conciencia capability.

---

# 14. NATURAL LANGUAGE OPERATIONS

Dogfood these examples:

```bash
conciencia ask "¿En qué estoy trabajando?"
```

Expected:
workspace state.

```bash
conciencia ask "¿Qué terminé hoy?"
```

Expected:
Work retrieval.

```bash
conciencia ask "¿Qué necesita mi atención?"
```

Expected:
attention/recommendation service.

```bash
conciencia ask "¿Qué herramientas de IA tengo disponibles?"
```

Expected:
runtime/model readiness.

```bash
conciencia ask "Generá un informe de lo que hice hoy"
```

Expected:
report proposal/create flow, not generic research.

```bash
conciencia ask "Prepará este informe para enviarlo a LINTEAM"
```

Expected:
external-action proposal.

If LINTEAM is not configured:

```text
Blocked: LINTEAM connection not configured.
```

Do NOT create a fake successful action.

---

# 15. ROOT UX QUALITY

The root output must be:

```text
operational
compact
beautiful
coherent
predictable
fast
```

Do not print huge Rich tables.

Prefer sections with short status lines.

Avoid exposing:

```text
raw UUIDs
raw Evidence
JSON payloads
stack traces
irrelevant historical Missions
```

unless explicitly requested.

Target normal terminal height:

approximately 30–45 lines.

---

# 16. PERFORMANCE

`conciencia` should feel immediate.

Do not:

* generate embeddings on every launch;
* call an LLM on every launch;
* perform external network calls synchronously;
* scan huge Git histories every launch.

Use existing local state and bounded queries.

Expensive checks belong in:

```bash
conciencia doctor
```

or explicit refresh operations.

---

# 17. ARCHITECTURE

Prefer:

```text
WorkspaceHomeService
    ├── ProjectService
    ├── WorkService
    ├── MissionService
    ├── ApprovalService
    ├── RuntimeReadinessService
    ├── ConnectionService
    └── RecommendationService
```

Home is an aggregator.

It must NOT own business logic already implemented elsewhere.

Likewise:

```text
CLI
 ↓
WorkspaceHomeService
 ↓
existing canonical services
```

---

# 18. TESTS

Add tests for:

* Home from `~`;
* Home from registered project;
* Home from unregistered Git repo;
* no workspace DB;
* runtime display uses canonical readiness;
* pending approval surfaced;
* failed Mission surfaced;
* recent Work surfaced;
* recommendations deterministic;
* recommendations link to valid commands;
* no raw secrets;
* no raw evidence payloads;
* no huge history dump;
* LINTEAM unconfigured state truthful;
* Ask "what needs attention";
* Ask "what AI tools are available";
* Ask report request;
* no unnecessary Mission creation.

Run targeted tests.

Then:

```bash
python -m compileall backend
git diff --check
```

Run real CLI dogfood from both:

```text
~
mission-control/
```

---

# 19. REAL DOGFOOD

Run:

```bash
conciencia
```

from home.

Run:

```bash
conciencia
```

inside Mission Control.

Run:

```bash
conciencia ask "¿En qué estoy trabajando?"
```

Run:

```bash
conciencia ask "¿Qué necesita mi atención?"
```

Run:

```bash
conciencia ask "¿Qué herramientas de IA tengo disponibles?"
```

Run:

```bash
conciencia ask "Generá un informe de lo que hice hoy"
```

Run:

```bash
conciencia connection
```

Return the actual outputs.

---

# STOP CONDITION

Stop when Conciencia feels like an operational workspace rather than a command catalog.

Specifically:

```text
Terminal
   ↓
Conciencia Home
   ├── Projects
   ├── Work
   ├── Missions
   ├── AI Workforce
   ├── Attention
   ├── Recommendations
   └── Connections
```

Do NOT proceed into:

* real LINTEAM production writes;
* Nebius integration;
* Tavily;
* marketplace;
* billing;
* large TUI;
* new agent catalog;
* frontend overhaul.

At completion return:

1. architecture changed;
2. files changed;
3. real root output;
4. runtime/tool visibility;
5. recommendations generated;
6. connection state;
7. tests/results;
8. known limitations;
9. one next recommended step.

Do not start that next step automatically.

Continue from the current verified state.

Current state is confirmed by real CLI dogfood:

* `work` and `ask` query the full workspace by default.
* `--project` applies explicit filtering.
* SQLite paths resolve relative to `backend/`, avoiding accidental empty databases.
* `"¿Qué hicimos para WebMCP?"` routes to `workspace_query`.
* lexical ranking removes functional words and correctly prioritizes WebMCP-related items.
* `ask` does not create unnecessary Missions for workspace questions.
* report create/list/inspect work.
* real report persisted under `.conciencia/reports/`.
* current evidence coverage:

  * 83 evidence-backed Work items
  * 46 Git commits
  * coverage: full
* current retrieval mode: lexical.
* verification:

  * 35 targeted tests passed
  * compileall passed
  * git diff --check passed.

Do NOT rewrite the existing Work, Ask, Project or Report implementation.

The next milestone is:

```text
WORK
 ↓
HYBRID RETRIEVAL
 ↓
ASK
 ↓
CONTEXT PACK
```

Do not add unrelated capabilities.

# 1. CANONICAL WORKSPACE RETRIEVAL SERVICE

Establish one canonical workspace retrieval service used by both:

```text
conciencia work search
conciencia ask
```

Do not keep separate ranking implementations.

Target conceptual API:

```python
retrieve_workspace(
    query,
    project_id=None,
    since=None,
    until=None,
    entity_types=None,
    limit=20,
)
```

Result objects should preserve:

```text
entity_type
entity_id
title
content/summary
timestamp
project_id
source_type
source_ref
tags
metadata
provenance
lexical_score
semantic_score
final_score
retrieval_mode
```

Presentation may omit detailed scores unless `--verbose` or `--json`.

# 2. REUSE EXISTING EMBEDDING INFRASTRUCTURE

Reuse:

```text
embeddings.py
InMemoryBackend
PgVectorBackend
workspace_semantic.py
```

Do NOT create another vector/search architecture.

The semantic layer must be workspace-generic, not LeadHunter-specific.

Convert Work items into neutral semantic documents.

Minimum supported entities:

```text
Mission
MissionRun
Signal
Evidence
GitCommit
Deliverable
Report
WorkActivity
```

Each document must preserve provenance back to the source record.

# 3. REAL VS SIMULATED EMBEDDINGS

Be explicit about backend truth.

Possible states:

```text
embedding_backend = real
embedding_backend = simulated
embedding_backend = unavailable
```

Possible retrieval modes:

```text
lexical
semantic
hybrid
hybrid-simulated
```

Never report `semantic` or `hybrid` as production semantic retrieval if only simulated embeddings were used.

Expose this in CLI output or JSON.

Example:

```text
Retrieval mode: hybrid
Embedding backend: real
```

or:

```text
Retrieval mode: hybrid-simulated
Embedding backend: simulated
```

# 4. HYBRID RANKING

Combine:

```text
lexical relevance
semantic similarity
recency
project scope
entity quality
structured metadata
```

Exact lexical matches must remain strong.

Semantic similarity should add recall, not destroy precision.

Use a deterministic weighted score initially.

Document chosen weights.

Avoid a complex learned ranker at this stage.

# 5. KEY DOGFOOD TEST

This is the most important requirement.

Today:

```bash
conciencia work search "WebMCP"
```

works because the keyword exists.

Now prove semantic value with:

```bash
conciencia work search \
  "herramientas para que agentes interactúen con páginas web"
```

The query intentionally does NOT contain `WebMCP`.

Expected relevant results should include actual WebMCP-related:

```text
Missions
Signals
Evidence
Git commits
```

Then test:

```bash
conciencia ask \
  "¿Qué hicimos para que nuestros agentes pudieran actuar sobre páginas web?"
```

Expected route:

```text
workspace_query
```

Expected behavior:

```text
hybrid workspace retrieval
→ evidence-backed response
```

It MUST NOT create a new Research Mission.

# 6. BASELINE COMPARISON

For the semantic dogfood query, compare:

```text
lexical-only top results
vs
hybrid top results
```

Report whether hybrid retrieval actually improved relevance.

Do not declare the semantic phase successful merely because embeddings executed.

Success means the semantically phrased query retrieves the correct historical WebMCP work better than lexical-only search.

# 7. CONTEXTPACK ADAPTER

Once hybrid retrieval passes, reuse the existing ContextPack subsystem.

Do not redesign ContextPack.

Add the smallest adapter required to turn retrieved workspace history into bounded mission context.

Target:

```text
Mission intent
   ↓
Workspace retrieval
   ↓
Top relevant Work items
   ↓
ContextPack
   ↓
Agent / Team / Harness
```

The ContextPack must preserve:

```text
source refs
project
timestamps
provenance
retrieval scores where useful
```

Respect:

```text
top_k
token/context budget
project scope
time scope
```

Never dump the full workspace into a Mission.

# 8. CONTEXT DOGFOOD

Test preparation for:

```text
"Implementá la siguiente mejora del sistema de búsqueda del workspace."
```

Before any execution, Conciencia should be able to retrieve relevant historical context such as:

```text
previous Work implementation
workspace retrieval decisions
semantic infrastructure
recent related commits
tests/results
known limitations
```

Then construct a bounded ContextPack.

For this phase, execution of the Mission is NOT required.

We are validating intelligent context preparation.

# 9. KEEP WORK, KNOWLEDGE AND MEMORY DISTINCT

Preserve current semantics:

```text
Work
= what actually happened

Knowledge
= durable reference information

Memory
= reusable preferences, corrections and historical learning

ContextPack
= bounded context assembled for one execution
```

Do not merge these stores.

# 10. TESTS

Add focused tests for:

* lexical fallback;
* real semantic backend;
* simulated backend labeling;
* hybrid ranking;
* exact keyword preservation;
* semantic retrieval without keyword overlap;
* project filter;
* temporal filter;
* provenance preservation;
* Ask and Work using the same retrieval service;
* no Mission creation for workspace queries;
* ContextPack creation from retrieved Work;
* bounded context size.

Run targeted tests.

Also run:

```bash
python -m compileall backend
git diff --check
```

Do not claim full suite success unless it was actually executed.

# REQUIRED REAL DOGFOOD

Run:

```bash
conciencia work search "WebMCP"
```

Run:

```bash
conciencia work search \
  "herramientas para que agentes interactúen con páginas web"
```

Run:

```bash
conciencia ask \
  "¿Qué hicimos para que nuestros agentes pudieran actuar sobre páginas web?"
```

Then build a ContextPack for:

```text
"Implementá la siguiente mejora del sistema de búsqueda del workspace."
```

Return:

```text
retrieval mode
embedding backend
lexical baseline
hybrid results
whether semantic retrieval improved ranking
top source refs
ContextPack item count
ContextPack approximate size/budget
provenance coverage
```

# STOP CONDITION

Stop after:

```text
Work History
    ↓
Hybrid Retrieval
    ↓
Ask
    ↓
ContextPack
```

Do NOT continue into:

```text
LINTEAM
Nebius
Tavily
new agents
new runtimes
billing
marketplace
UI overhaul
```

At completion report only:

1. root architecture changes;
2. files changed;
3. retrieval mode/backend;
4. tests/results;
5. real dogfood comparison;
6. ContextPack result;
7. known limitations;
8. one recommended next step.

Do not start that next step automatically.

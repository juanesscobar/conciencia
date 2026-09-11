# CONCIENCIA — WORKSPACE-WIDE PROFESSIONAL REPORTS

Continue from the current Report implementation.

IMPORTANT:

Do NOT rebuild:

* Work
* WorkItem
* Project
* Report persistence
* report list
* report inspect
* report reference resolver
* existing project reports
* workspace retrieval
* ContextPack

The current Report system works but is still too project-centric.

We now need first-class WORKSPACE REPORTS.

---

# PROBLEM

Current professional report example:

```text
Professional work report - Conciencia
Project: Conciencia
```

This only summarizes one project.

Conciencia is intended to operate as a multi-project workspace.

A user may simultaneously work on:

* Conciencia
* LINTEAM
* Sys Créditos
* logistics software
* other registered projects

We need a professional report spanning ALL relevant projects.

---

# CORE SEMANTICS

There are now two scopes:

```text
PROJECT REPORT
WORKSPACE REPORT
```

A report with an explicit project:

```bash
conciencia report create \
  --since 2026-08-27 \
  --until 2026-09-05 \
  --project Conciencia
```

means:

```text
scope = project
```

A report without `--project`:

```bash
conciencia report create \
  --since 2026-08-27 \
  --until 2026-09-05
```

means:

```text
scope = workspace
```

Do NOT implicitly resolve the current directory to a project when
the user intentionally requests a workspace report.

---

# COMMANDS

Support:

```bash
conciencia report today
conciencia report week
```

Default these to workspace scope.

Also support:

```bash
conciencia report today --project Conciencia
conciencia report week --project Conciencia
```

And explicit periods:

```bash
conciencia report create \
  --since YYYY-MM-DD \
  --until YYYY-MM-DD
```

---

# WORKSPACE REPORT MODEL

A workspace report must include:

```text
title
scope = workspace
period_from
period_to
executive_summary

projects[]
    project
    status
    completed_work
    major_results
    technical_changes
    validation
    deployments
    problems_resolved
    pending_work
    next_steps

workspace_results
workspace_blockers
workspace_next_priorities
evidence_summary
provenance_refs
```

Do not duplicate Project or Work models.

This is a report projection.

---

# PROJECT DISCOVERY

Determine projects from WorkItems inside the requested period.

Do NOT blindly include every registered project.

Include a project only when it has relevant work in the period,
unless explicitly requested otherwise.

Historical WorkItems with `project_id = null` must remain truthful.

Do not silently assign them to a project.

Place them under:

```text
Unassigned / workspace-level work
```

when relevant.

---

# PROFESSIONAL AGGREGATION

For every project:

```text
WorkItems
 ↓
deterministic classification
 ↓
deduplication
 ↓
professional project summary
```

Then:

```text
project summaries
 ↓
workspace aggregation
 ↓
executive workspace report
```

Do not simply concatenate project reports.

Workspace-level summaries should identify meaningful cross-project outcomes.

Do not invent claims.

---

# WORKSPACE METRICS

When supported by evidence, include:

```text
projects touched
work items
git commits
missions completed
missions failed
runs
reports
deployments
tests/validation records
```

Only include metrics available from structured sources.

Do not estimate missing values.

---

# BLOCKERS

Aggregate real blockers such as:

* pending approvals
* failed missions
* unavailable runtime
* disabled embeddings
* connector contract required
* failed validation
* pending deployment

Reuse existing canonical services.

Do NOT duplicate RecommendationService or RuntimeReadinessService.

---

# NEXT PRIORITIES

Generate deterministic priorities from:

```text
pending work
failed missions
approvals
project priority
connections
recommendations
recent work
```

Do not use an LLM initially.

Maximum:

```text
3–7 priorities
```

---

# CANONICAL `latest`

There is currently inconsistent behavior where:

```bash
conciencia report inspect latest
```

can resolve to a professional report, while:

```bash
conciencia report export latest --format txt
```

may say:

```text
Latest report has no canonical professional representation.
```

This must be fixed.

Create ONE canonical resolver:

```python
resolve_report_ref(...)
```

or reuse the existing one.

The same report reference MUST resolve identically for:

```bash
report inspect
report export
future report publish
```

Supported:

```text
latest
short ID
full UUID
```

If `latest` means the newest final Report, every command must use that same semantic.

---

# REPORT TYPES

Distinguish metadata cleanly:

```text
scope: project | workspace
kind: professional | technical
```

Do not infer report kind from title strings.

Avoid breaking existing reports.

Use backward-compatible defaults where necessary.

---

# EXPORT

These must work for workspace reports:

```bash
conciencia report export latest --format txt
conciencia report export latest --format md
conciencia report export latest --format json
conciencia report export latest --format pdf
```

If PDF exists, reuse the renderer.

Do NOT create another PDF architecture.

---

# EXAMPLE

Target:

```text
PROFESSIONAL WORKSPACE REPORT

Period
2026-08-27 → 2026-09-05

Executive summary
...

Projects

Conciencia
  Completed work
  Results
  Validation
  Pending

LINTEAM
  Completed work
  Results
  Pending

Sys Créditos
  Completed work
  Validation
  Pending

Workspace results
...

Current blockers
...

Next priorities
...

Evidence coverage
...
```

No raw Evidence payload dumps.

No secret values.

No large UUID lists in professional output.

---

# DOGFOOD

Run:

```bash
conciencia report create \
  --since 2026-08-27 \
  --until 2026-09-05
```

Then:

```bash
conciencia report inspect latest
conciencia report export latest --format txt
conciencia report export latest --format pdf
```

Verify that the report includes every project that actually has WorkItems
inside that period.

Then compare:

```bash
conciencia report create \
  --since 2026-08-27 \
  --until 2026-09-05 \
  --project Conciencia
```

The two reports must have clearly different scopes.

---

# TESTS

Add tests for:

* workspace report
* project report
* multiple projects
* inactive project with no period activity excluded
* unassigned WorkItems
* deterministic classification
* workspace aggregation
* blocker aggregation
* project metrics
* workspace metrics
* canonical latest resolver
* inspect/export same reference
* short ID
* full UUID
* no raw secrets
* no Evidence dump
* TXT export
* PDF export if supported

Run targeted tests.

Then:

```bash
python -m compileall backend
git diff --check
```

STOP after workspace-wide professional reporting is proven.

Do NOT implement LINTEAM writes yet.

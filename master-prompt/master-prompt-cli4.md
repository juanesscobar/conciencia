# CONCIENCIA — PROFESSIONAL WORK INTELLIGENCE

The Report pipeline already exists.

Do NOT rebuild:

* Work
* Report model
* report list
* report inspect
* report export
* report reference resolution
* ContextPack
* Workspace retrieval

Current problem:

A real professional report for Conciencia covering 2026-08-27 → 2026-09-04 correctly finds 47 WorkItems, but produces:

* Completed work: None recorded
* Major results: None recorded
* Tests and validation: None recorded
* Deployments: None recorded

while many Git commits clearly represent completed features, validation, deployments and meaningful outcomes.

This is now a WORK INTELLIGENCE / CLASSIFICATION problem.

## GOAL

Transform:

```text
raw WorkItems
    ↓
deterministic classification
    ↓
professional accomplishments
    ↓
structured Report
```

The report should communicate what the developer accomplished, not merely reproduce Git commit messages.

## CLASSIFICATION

Create or extend a canonical deterministic Work classification layer.

Classify WorkItems into:

* completed_work
* major_results
* technical_changes
* architecture_decisions
* tests_and_validation
* deployments
* problems_resolved
* problems_discovered
* pending_work
* next_steps

Use existing WorkItem fields:

* type
* title
* summary
* source_type
* source_ref
* metadata
* tags
* timestamp
* project
* provenance

Do not create a duplicate Work model.

## GIT SEMANTICS

Interpret conventional commit prefixes when available:

* `feat` → completed_work / technical_changes
* `fix` → problems_resolved / technical_changes
* `test` → tests_and_validation
* `docs` → technical_changes or documentation
* `deploy` / deployment metadata → deployments
* `refactor` → architecture/technical changes
* `chore` → technical change only when meaningful

Recognize common semantic indicators such as:

* deploy
* release
* production
* test
* passed
* validation
* architecture
* migration
* integration
* fix
* bug
* feature
* implementation

Keep the rules deterministic initially.

Do NOT add an LLM classifier yet unless an existing configured summarization path can be reused safely as an optional enhancement.

## DEDUPLICATION

Current Work output repeats commit title and summary.

Normalize and deduplicate:

```text
"title — title"
```

into one useful statement.

Do not expose encoding corruption such as:

```text
Â§
â€”
```

in professional output when safely normalizable.

Preserve original source text in provenance.

## OUTCOME LANGUAGE

Convert technical events into concise professional accomplishments without inventing claims.

Example source:

```text
feat(cli): master-prompt-cli fase UX 1 — onboard, dashboard raiz,
run logs/watch, workflow tree, readiness
```

Professional representation:

```text
Implemented the first operational CLI UX phase, including runtime onboarding,
workspace dashboard, run monitoring and readiness visibility.
```

Only make transformations supported by source evidence.

## TESTS / VALIDATION

If Work history or Git records explicitly contain successful test-suite results, classify them under validation.

Do not invent a test count.

If test results are not present in Work history, say:

```text
No structured validation result recorded.
```

rather than simply `None recorded`.

## DEPLOYMENTS

Recognize existing deployment-related Work such as:

```text
feat(devpost): deploy WebMCP demo app en Hetzner...
docs: RC deploy...
```

as deployment activity when supported.

## REPORT QUALITY

Target output:

```text
Professional work report — Conciencia
27 Aug 2026 → 04 Sep 2026

Executive summary
...

Completed work
- ...
- ...

Major results
- ...

Technical changes
- ...

Tests and validation
- ...

Deployments
- ...

Problems resolved
- ...

Pending work
- ...

Next steps
- ...

Evidence coverage
47 WorkItems
N Git commits
...
```

Keep the report professional and readable.

Do NOT dump raw UUIDs or Evidence payloads.

## DOGFOOD

Rebuild a professional report for:

```bash
conciencia report create \
  --since 2026-08-27 \
  --until 2026-09-04 \
  --project Conciencia
```

Then run:

```bash
conciencia report inspect latest
conciencia report export latest --format txt
conciencia report export latest --format pdf
```

Compare the old and new report.

The new report must materially improve:

* Completed work
* Major results
* Validation
* Deployments
* Problems resolved

without hallucinating unsupported accomplishments.

## TESTS

Add targeted tests for:

* feat classification
* fix classification
* test classification
* deploy classification
* deduplication
* encoding cleanup
* no unsupported claims
* provenance retained
* professional report sections

Then run:

```bash
python -m compileall backend
git diff --check
```

STOP after report quality is proven.

Do NOT implement LINTEAM writes in this phase.

# CONCIENCIA — PROFESSIONAL WORK REPORTS & EXPORT

Continue from the current operational Workspace state.

The existing system already provides:

* Work history
* Work summaries
* Reports
* Evidence/provenance
* Project filtering
* Ask routing
* `.conciencia/reports`
* Connection registry
* LINTEAM state = `contract_required`

Do not rebuild Work or Reports.

## Goal

Turn the existing internal Work history into professional, portable work reports.

Target:

```text
Work
 ↓
Structured Professional Report
 ├── TXT
 ├── Markdown
 ├── JSON
 └── PDF
```

The structured Report is canonical.

TXT/PDF are representations.

## Report structure

Support:

* title
* responsible person if configured
* project
* period_from
* period_to
* executive_summary
* completed_work
* major_results
* technical_changes
* tests_and_validation
* deployments
* problems_resolved
* pending_work
* next_steps
* evidence_summary
* provenance_refs

Do NOT dump raw evidence.

Do NOT expose internal UUID noise in professional output.

Do NOT expose secrets.

## Commands

Implement or extend:

```bash
conciencia report today
conciencia report week

conciencia report create \
  --since YYYY-MM-DD \
  --until YYYY-MM-DD \
  --project <project>

conciencia report export latest --format txt
conciencia report export latest --format md
conciencia report export latest --format json
conciencia report export latest --format pdf
```

If safe PDF infrastructure does not already exist, isolate PDF rendering behind a renderer interface.

Do not contaminate ReportService with PDF-specific logic.

## Temporal correctness

Fix/verify date parsing before relying on report generation.

Explicit input such as:

```text
27.08.26
27/08/2026
2026-08-27
```

must resolve deterministically to August 27, 2026.

Never silently interpret 27.08.26 as August 5 or another date.

Add regression tests.

## Professional summary

A report should prioritize outcomes over raw commits.

Example categories:

```text
Executive summary
Completed work
Results
Validation
Pending
Next steps
Evidence coverage
```

Git commits and Evidence remain provenance sources.

## Export

Store exports under a predictable workspace path, e.g.:

```text
.conciencia/reports/exports/
```

Do not overwrite existing exports without explicit intent.

## Connector readiness

Add a connector-neutral serialization method:

```python
report.to_external_payload()
```

or equivalent.

Do NOT implement LINTEAM-specific payload fields inside the core Report model.

## Tests

Test:

* explicit date ranges
* day/week reports
* project filtering
* professional summary generation
* TXT export
* Markdown export
* JSON export
* PDF export if available
* no secrets
* no raw Evidence payload dump
* provenance retained
* connector-neutral serialization

Run real dogfood:

```bash
conciencia report create \
  --since 2026-08-27 \
  --until 2026-09-04 \
  --project Conciencia

conciencia report export latest --format txt
conciencia report export latest --format pdf
```

Return actual generated paths and a short preview.

STOP after professional report/export works.

Do not implement LINTEAM production integration yet.

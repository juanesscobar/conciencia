Fix the Report CLI UX consistently.

Current verified behavior:

* `conciencia report list` works.
* `conciencia report` crashes because the root alias passes a Typer `OptionInfo`.
* `conciencia report inspect a92e91f4` crashes because short IDs are passed directly to `uuid.UUID`.
* `conciencia report export` only supports `latest`.
* The CLI already displays short IDs in `report list`, so all report commands should accept them consistently.

Required behavior:

```bash
conciencia report
```

must behave exactly like:

```bash
conciencia report list
```

These must all work:

```bash
conciencia report inspect latest
conciencia report inspect a92e91f4
conciencia report inspect <full-uuid>
```

These must also work:

```bash
conciencia report export latest --format txt
conciencia report export a92e91f4 --format txt
conciencia report export <full-uuid> --format txt
```

Use one canonical report reference resolver.

Suggested concept:

```python
resolve_report_ref(db, ref)
```

Supported refs:

* `latest`
* full UUID
* unique short UUID prefix

For short IDs, query by prefix safely instead of attempting `uuid.UUID(short_id)`.

If the prefix is ambiguous, return a clear error:

```text
Ambiguous report reference: a92e
```

Do not silently choose one.

If no report exists:

```text
Report not found: ...
```

Do not expose stack traces for normal user input.

Also fix the `conciencia report` root alias by routing both root and `list` through one plain internal implementation rather than invoking Typer-decorated command functions directly.

Add regression tests for:

* root report alias
* list
* inspect latest
* inspect short ID
* inspect full UUID
* invalid report ref
* ambiguous short prefix
* export latest
* export short ID
* export full UUID

Run targeted tests, compileall and git diff --check.

Do not change Report domain semantics.

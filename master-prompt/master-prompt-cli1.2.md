# CONCIENCIA — RUNTIME / MODEL READINESS SEMANTICS

Dogfooding confirmed that current health semantics are incorrect.

Observed:

```text
conciencia model
→ deepseek/deepseek-chat registered

conciencia runtime
→ generic enabled + ready

conciencia doctor
→ everything ✓
→ "Todo ok"
```

But actual Mission execution immediately failed:

```text
research: LLM no configurado
```

Additionally, Conciencia correctly detects local binaries for:

```text
Claude Code
Codex
OpenCode
OpenClaw
```

but all are currently disabled.

## Objective

Establish one canonical capability/readiness model across:

```text
Models
Providers
Runtimes
Tools
Doctor
Mission Planner
Mission Executor
```

Do not patch only CLI presentation.

---

## State semantics

Distinguish:

```text
registered
detected
configured
enabled
ready
disabled
unavailable
misconfigured
error
```

`ready` MUST mean:

> The capability has passed the same minimum preflight required for real execution.

Finding a runtime adapter is not readiness.

Finding a binary is not readiness.

Registering a model is not readiness.

Having a model name configured is not readiness.

---

## Generic runtime

For generic LLM execution, readiness must validate at least:

```text
provider selected
model selected
provider adapter exists
required credentials are available
base URL/configuration is valid
executor can resolve the same configuration
```

Do not expose secret values.

---

## External runtimes

For:

```text
codex
claude_code
opencode
openclaw
```

separate:

```text
adapter registered
binary detected
enabled by Conciencia
health/preflight
ready
```

A detected but disabled runtime should NOT be represented as an error.

Example:

```text
Codex
detected
disabled
```

---

## Runtime vs Model

Preserve the architectural distinction:

```text
Mission
  ↓
Execution Runtime
  ↓
Model Provider / Model when applicable
  ↓
Tools
```

Examples:

```text
runtime = generic
provider = deepseek
model = deepseek-chat
```

versus:

```text
runtime = codex
model = runtime-managed
```

Do not conflate runtime selection with model selection.

---

## Doctor

`conciencia doctor` must become the canonical operational preflight.

It must never output:

```text
Todo ok
```

when a basic Mission using the selected default runtime would immediately fail.

Use overall states such as:

```text
READY
READY WITH LIMITATIONS
BLOCKED
```

Separate core requirements from optional capabilities.

Example:

```text
Core
database        ready
missions        ready
workflows       ready

LLM Execution
generic         blocked
DeepSeek        credentials unavailable

External runtimes
Codex           detected · disabled
Claude Code     detected · disabled
OpenCode        detected · disabled
OpenClaw        detected · disabled

Optional
Embeddings      disabled

Overall
READY WITH LIMITATIONS
```

If no usable execution runtime exists:

```text
Overall
BLOCKED FOR MISSION EXECUTION
```

---

## Model UX

Improve `conciencia model` so registration does not imply availability.

Show:

```text
Provider
Model
Configured
Credentials
Health
```

Never display credential values.

---

## Onboarding integration

Because external runtime binaries are already detected successfully, prepare the architecture for:

```bash
conciencia onboard
```

to offer configuration of detected runtimes.

Example:

```text
Detected AI runtimes

✓ Codex
✓ Claude Code
✓ OpenCode
✓ OpenClaw

4 detected runtimes are disabled.

Configure them? [Y/n]
```

Do not automatically enable capabilities without user consent.

Do not copy or expose runtime secrets.

---

## Planner integration

Mission proposal readiness must use this exact same readiness service.

If:

```text
runtime=generic
provider=deepseek
```

cannot actually execute, proposal must show:

```text
Execution readiness
BLOCKED
```

before Mission creation/execution.

---

## Required regression

After implementation:

```bash
conciencia model
conciencia runtime
conciencia doctor
```

must agree about capability state.

Then:

```bash
conciencia ask "investigar los requisitos del WebMCP Challenge"
```

must either:

A. report READY and successfully execute the research step;

or

B. report BLOCKED before execution with the exact actionable reason.

There must be no state where:

```text
doctor = OK
planner = READY
executor = LLM NOT CONFIGURED
```

Run relevant tests and report the root cause.

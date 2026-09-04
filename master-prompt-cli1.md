# CONCIENCIA CLI DOGFOODING — ITERATION 2

We performed another real manual CLI dogfooding session.

Do not add unrelated features.

This iteration is about closing the gap between:

```text
Intent → Mission
```

and:

```text
Mission → executable Plan
```

while improving the interactive CLI UX.

---

## OBSERVED SESSION

The following successfully worked:

```bash
conciencia health
conciencia agents
conciencia --install-completion
conciencia ask "crear deploy de conciencia a devpost en el thewebmcp challenge de open ai"
```

`conciencia ask` produced:

```text
Mission type: deployment
Runtime: openclaw
Suggested agent: OpsBot
Workflow:
  research
  synthesis
  approval
Estimated cost: $0.0011
```

Mission creation succeeded.

Then:

```bash
conciencia mission plan 4be54afd-4063-4444-970c-a36319ff3472
```

failed with:

```text
Error: No hay workflow por defecto para tipo 'deployment'
```

This is a product-level orchestration inconsistency.

---

# P0 — MISSION TYPES MUST BE PLAN-VALID

A Mission type detected by `conciencia ask` must not silently create a Mission that the planner cannot resolve.

Audit:

```text
intent classifier
mission type enum/registry
mission creation
workflow registry
workflow planner
mission planner
template registry
```

Create a capability matrix:

```text
Mission Type
Recognized by ask?
Creatable?
Workflow available?
Agents available?
Runtime available?
Executable?
```

Identify every mismatch.

Fix the architecture rather than special-casing only `deployment`.

---

# 1. WORKFLOW RESOLUTION

Implement or improve a central workflow resolution mechanism.

Conceptually:

```text
Mission
   ↓
Mission Type
   ↓
Requirements
   ↓
Workflow Resolver
   ↓
Compatible Workflow
```

Prefer existing services if equivalent functionality already exists.

Do NOT create duplicate planner logic.

A Mission should only be considered immediately executable if a compatible workflow can be resolved.

---

# 2. PRE-CREATION VALIDATION

Before `conciencia ask` offers:

```text
¿Crear la misión?
```

validate that the proposed Mission can be planned.

Check at least:

```text
mission type
workflow
agents/team
runtime
required capabilities
```

If some parts are unavailable, expose this in the proposal.

Example:

```text
MISSION PROPOSAL

Type
deployment

Runtime
openclaw ✓

Agent
OpsBot ✓

Workflow
deployment ✕

Issue
No compatible deployment workflow is installed.

Options:
> Save as draft
  Create compatible workflow
  Change Mission type
  Cancel
```

Never pretend a Mission is executable when it is not.

---

# 3. IMPLEMENT BASE `deployment` WORKFLOW

`deployment` is a legitimate technological Mission type.

Implement a safe default workflow using existing Workflow/DAG primitives.

Suggested stages:

```text
project-context
      ↓
deployment-discovery
      ↓
preflight
      ↓
tests/build
      ↓
deployment-plan
      ↓
approval 🔒
      ↓
deploy
      ↓
health-check
      ↓
smoke-test
      ↓
evidence
      ↓
outcome
```

Where useful:

```text
tests ───────┐
build ───────┼→ deployment-plan
config-check ┘
```

Deployment must NEVER bypass human approval for production-impacting actions.

Reuse current approval infrastructure.

---

# 4. DEPLOYMENT MODES

Support at minimum conceptually:

```text
readiness
plan
execute
```

or map them to existing Mission modes if already available.

Examples:

```text
deployment-readiness
→ inspect + validate + report
```

```text
deployment-plan
→ inspect + validate + generate plan
```

```text
deployment
→ inspect + validate + approval + execute + verify
```

Avoid unnecessary new enums if current architecture can express this with policies/modes.

---

# 5. BETTER INTENT CLASSIFICATION

The dogfooding prompt was:

```text
crear deploy de conciencia a devpost en el thewebmcp challenge de open ai
```

It was classified as:

```text
deployment
```

But Devpost is not necessarily a deployment target.

Audit intent classification quality.

Distinguish concepts such as:

```text
deploy application to Hetzner
→ deployment

deploy frontend to Vercel
→ deployment

prepare project for Devpost
→ project-delivery / submission-preparation

submit project to Devpost
→ submission / external action
```

Do NOT build a giant taxonomy.

Improve semantic planning so intent is based on objective/context rather than keyword matching.

If confidence is low, express uncertainty in the Mission proposal.

Example:

```text
Detected objective:
Hackathon submission preparation

Suggested Mission type:
project-delivery

Confidence:
82%

Alternative:
deployment
```

---

# 6. `conciencia ask` INTERACTIVE MODE

Currently:

```bash
conciencia ask
```

fails with:

```text
Missing argument 'TEXT'
```

Improve UX.

Both should work:

```bash
conciencia ask "audit this project"
```

and:

```bash
conciencia ask
```

Interactive form:

```text
What do you want to accomplish?

> _
```

Then continue through the existing Mission proposal service.

No duplicate natural-language processing path.

---

# 7. ROOT `conciencia` EXPERIENCE

Current:

```bash
conciencia
```

only displays Typer help.

Begin evolving it toward the first-run/command-center UX.

Do not overbuild a TUI yet.

For an interactive TTY, show a compact dashboard:

```text
CONCIENCIA
Mission Control for Autonomous Work

Project
<detected project or none>

System
healthy

Missions
2 active · 1 approval

Runtimes
4 ready

What do you want to do?

> Ask Conciencia
  Continue Mission
  Start Mission
  Audit project
  Approvals
  Doctor
  Commands
```

If implementing this cleanly is too large for this phase, implement the foundation and document the next step.

`conciencia --help` must retain normal CLI help.

---

# 8. COMMAND HIERARCHY CLEANUP

Current command tree contains historical inconsistencies:

```text
agents
agent

workflow
workflow-inspect
workflow-run

run
run-watch
```

Target:

```text
agent list
agent inspect
agent run

workflow list
workflow inspect
workflow run

run list
run inspect
run logs
run watch
```

Maintain backwards-compatible aliases where practical:

```text
agents
workflow-inspect
workflow-run
run-watch
```

Mark aliases as deprecated in help if supported cleanly.

Do not break existing scripts unnecessarily.

---

# 9. AGENT HEALTH / ERROR EXPLANATION

Dogfooding revealed:

```text
ProjectManager | pm | error
```

Audit why.

`agent list` should not merely expose an unexplained error state.

Implement useful inspection:

```bash
conciencia agent inspect ProjectManager
```

Expected information:

```text
status
role
capabilities
runtime
model
tools
last error
health reason
suggested remediation
```

Do not leak secrets.

If the error indicates a genuine configuration defect, fix it only if safe and within scope.

---

# 10. STATUS LANGUAGE

Review status semantics across:

```text
agents
runtimes
missions
runs
tools
```

Prefer stable states such as:

```text
ready
idle
running
waiting
blocked
unavailable
misconfigured
disabled
error
```

Avoid ambiguous state names.

---

# 11. MISSION PROPOSAL MUST SHOW RESOLVABILITY

Improve proposal UX:

```text
MISSION PROPOSAL

Objective
Prepare Conciencia for WebMCP Challenge submission

Type
project-delivery

Confidence
91%

Team
OpsBot
ResearchBot

Runtime
OpenClaw

Workflow
submission-preparation ✓

Approval gates
1

Execution readiness
READY

Estimated cost
$0.001 – $0.004
```

If not ready:

```text
Execution readiness
BLOCKED

Reason
No compatible workflow.
```

This should happen BEFORE Mission creation.

---

# 12. WORKFLOW REGISTRY COVERAGE

Audit the current Mission types and provide default coverage for the types already officially supported.

Do not add dozens of workflows.

Prioritize the technological Mission types we have explicitly decided are core:

```text
research
software-development
code-review
debugging
architecture
testing
devops
deployment
technical-audit
agent-design
workflow-design
automation
integration
data-analysis
product-research
competitive-research
technical-discovery
lead-research
technical-proposal
```

If the project already uses slightly different canonical names, map/document rather than duplicating them.

For this phase, only implement missing workflows necessary for coherent current behavior.

Produce the complete gap matrix for the remainder.

---

# 13. GENERIC FALLBACK WORKFLOW

Evaluate whether a safe generic planning workflow should exist:

```text
discover
↓
plan
↓
execute
↓
validate
↓
approval/outcome
```

However:

A generic fallback must NOT hide missing specialized workflow support.

If used, clearly mark:

```text
Workflow
generic-mission@1

Reason
No specialized workflow exists for deployment.
```

For high-risk mission types such as deployment, production operations, external communication or destructive actions, do NOT use an unsafe generic execution fallback.

---

# 14. RUNTIME SELECTION VALIDATION

The Mission selected:

```text
openclaw
```

for deployment.

Validate why.

Expose runtime selection reason.

Example:

```text
Runtime
OpenClaw

Why selected
✓ operations capability
✓ tool execution
✓ available locally
✓ compatible with deployment Mission
```

If a runtime is unavailable after Mission creation, planner should resolve an allowed fallback or block clearly.

---

# 15. SHELL COMPLETION UX

Completion installation worked:

```bash
conciencia --install-completion
```

Keep this.

Add onboarding hint when completion is absent if detectable, but do not nag repeatedly.

The user accidentally tried:

```text
--install-completion
conciencia--install-completion
```

Do not try to compensate for arbitrary malformed shell commands.

Documentation should simply make actual commands unmistakably copyable.

---

# 16. TESTS

Add regression coverage for:

```text
ask → deployment → workflow resolution
ask cannot mark unresolved Mission as ready
deployment workflow planning
deployment approval gate
intent classification ambiguity
interactive ask
agent error inspection
legacy command aliases
workflow resolution matrix
runtime compatibility
```

Also preserve all existing tests.

---

# 17. REQUIRED DOGFOOD AFTER IMPLEMENTATION

Run exactly:

```bash
conciencia health
conciencia agent list
conciencia runtime list
conciencia ask
```

Enter:

```text
crear deploy de conciencia en un entorno de staging
```

Confirm:

```text
deployment
compatible workflow
runtime resolution
approval gate
```

Create Mission.

Then run the exact generated next command.

Continue:

```text
plan
inspect
run/readiness
```

Do not execute a real production deployment as part of automated testing.

Then test:

```bash
conciencia ask "preparar Conciencia para presentarlo en Devpost para el WebMCP Challenge"
```

Verify this is not blindly classified as infrastructure deployment unless evidence/context genuinely supports that interpretation.

---

# DEFINITION OF DONE

This iteration is complete when:

1. `ask` does not create apparently executable Missions with no workflow.
2. `deployment` can resolve a safe workflow.
3. deployment contains a human approval gate.
4. `conciencia ask` works interactively with no TEXT argument.
5. runtime selection can explain itself.
6. ProjectManager's error can be inspected.
7. command hierarchy cleanup begins without breaking compatibility.
8. relevant tests pass.
9. existing A–L functionality remains intact.
10. the manual dogfooding path works from intent through Mission plan.

Before modifying code, output:

* root cause;
* Mission Type ↔ Workflow capability matrix;
* files involved;
* proposed minimal implementation;
* risks;
* test plan.

Then implement the smallest coherent solution.

# CONCIENCIA CLI — PRODUCT-GRADE UX / RUNTIME ORCHESTRATION PASS

We have completed the first real manual CLI dogfooding session.

The underlying capabilities work, especially:

```text
conciencia ask
→ intent detection
→ Mission proposal
→ cost estimation
→ Team matching
→ Agent matching
→ workflow
→ approval gate
→ Mission creation
```

However, the CLI still behaves too much like a collection of framework commands.

The next objective is:

> Make the Conciencia CLI feel like a polished mission operating environment for technological work.

Do NOT redesign the domain architecture.

Do NOT create parallel orchestration logic.

The CLI must remain a client/interface over the existing Mission, Agent, Team, Harness, Workflow, Runtime, Tool, Context, Evidence, Signal, Approval and Economics services.

---

# P0 — SECURITY INCIDENT FOUND DURING DOGFOODING

The current:

```bash
conciencia config get
```

printed secret values including API credentials and SMTP credentials.

This is unacceptable.

Immediately audit all CLI/config/logging paths for secret leakage.

By default:

```text
DEEPSEEK_API_KEY   sk-••••••••••69992
SMTP_PASS          ••••••••••••
OPENAI_API_KEY     sk-••••••••••82d
```

Never expose complete secrets in:

* CLI tables
* logs
* doctor output
* exceptions
* JSON output
* traces
* Mission evidence
* runtime diagnostics

Implement a reusable secret-redaction utility.

Detect likely sensitive keys including:

```text
*_KEY
*_TOKEN
*_SECRET
*_PASSWORD
*_PASS
AUTH_*
API_KEY
PRIVATE_KEY
```

and provider-specific credentials.

If explicit secret reveal is ever supported, require an intentional flag and warning.

Add regression tests.

Security first.

---

# 1. FIRST-RUN EXPERIENCE

Implement:

```bash
conciencia
```

as a useful entry point.

If the current directory is not initialized, show onboarding rather than an empty help screen.

Example:

```text
CONCIENCIA

Mission Control for Autonomous Work

Current directory
C:\Users\juan\project

Detected
✓ Git repository
✓ Python
✓ FastAPI
✓ Docker
✓ pytest

Conciencia project
Not initialized

❯ Initialize this project
  Inspect without initializing
  Connect to existing workspace
  Run doctor
  Exit
```

Provide:

```bash
conciencia onboard
```

and:

```bash
conciencia init
```

They may share services.

Do not duplicate project detection.

---

# 2. OPENCLAW-QUALITY ONBOARDING

Take inspiration from high-quality modern CLI onboarding patterns such as OpenClaw:

* progressive disclosure
* environment detection
* actionable diagnostics
* safe defaults
* interactive selections
* clear success/failure states
* useful next actions
* no requirement to read documentation before first success

Do NOT copy branding or implementation.

Apply the interaction principles to Conciencia.

Goal:

A new developer should go from:

```bash
git clone ...
cd ...
conciencia
```

to their first useful Mission without manually understanding the entire architecture.

---

# 3. ZERO-TO-MISSION FLOW

Target:

```text
conciencia
    ↓
project detection
    ↓
runtime detection
    ↓
configuration health
    ↓
what do you want to do?
    ↓
natural language intent
    ↓
Mission proposal
    ↓
human confirmation
    ↓
execution
    ↓
watch
    ↓
outcome
```

Example:

```text
What do you want to do?

> audit this repository and identify the highest-risk problems
```

Then:

```text
MISSION PROPOSAL

Technical Audit — conciencia

Mode
semi-assisted

Team
Architecture
Security
QA

Runtime policy
automatic

Execution
3 parallel stages
2 sequential stages

Approval gates
1

Estimated cost
$0.03 – $0.12

Start Mission?

❯ Start
  Edit plan
  Change runtime
  Change budget
  Save draft
  Cancel
```

---

# 4. COMMAND UX CONSISTENCY

Audit every current command.

Commands should follow consistent grammar.

Recommended hierarchy:

```text
conciencia

conciencia status
conciencia doctor
conciencia onboard
conciencia init
conciencia map

conciencia ask

conciencia project
conciencia project inspect

conciencia mission list
conciencia mission create
conciencia mission inspect
conciencia mission plan
conciencia mission run
conciencia mission watch
conciencia mission pause
conciencia mission resume
conciencia mission cancel

conciencia run list
conciencia run inspect
conciencia run logs
conciencia run watch

conciencia agent list
conciencia agent inspect
conciencia agent run

conciencia team list
conciencia team inspect
conciencia team run

conciencia harness list
conciencia harness inspect

conciencia workflow list
conciencia workflow inspect
conciencia workflow run

conciencia runtime list
conciencia runtime inspect
conciencia runtime doctor

conciencia tool list
conciencia tool inspect

conciencia model list

conciencia knowledge search
conciencia memory search
conciencia context inspect

conciencia approvals
conciencia approve
conciencia reject

conciencia signals
conciencia evidence

conciencia cost

conciencia template list
conciencia template inspect

conciencia audit .
```

Preserve backwards compatibility where reasonable through aliases.

---

# 5. NEVER SHOW FAKE COPY-PASTE COMMANDS

Current documentation contained constructs such as:

```text
conciencia mission create|plan|run|inspect
conciencia agents · conciencia modules
conciencia lead inspect <id>
```

These caused real shell errors.

Do not display shell pseudo-syntax in copyable command blocks.

Documentation must distinguish:

```text
COMMAND FAMILY
```

from:

```bash
actual executable command
```

When displaying placeholders, prefer:

```bash
conciencia mission inspect MISSION_ID
```

and explicitly label `MISSION_ID` as a placeholder.

Better yet, when a real ID exists, print the actual executable command:

```bash
conciencia mission inspect 6998bc52-08b6-42d6-9024-321a95dbcb00
```

Every “Next” suggestion produced by the CLI should be directly copyable.

---

# 6. NEXT ACTIONS

Every successful action should produce relevant next actions.

Current good example:

```text
Mission created.
Next:
conciencia mission plan <id>
```

Improve it.

Example:

```text
✓ Mission created

investigar el mercado de logística
6998bc52-08b6-42d6-9024-321a95dbcb00

Status
draft

Next

❯ Plan mission
  Run mission
  Inspect mission
  Open approvals
```

In non-interactive terminals:

```text
Next:
  conciencia mission plan 6998bc52...
```

Never require users to remember the next command.

---

# 7. CONTEXT-AWARE SHORTCUTS

The CLI should understand current context.

Allow:

```bash
conciencia mission inspect
```

when exactly one current/active Mission exists.

Potential context:

```text
current project
current mission
current run
current branch
current runtime
```

Support explicit selection when ambiguous.

Example:

```text
3 recent Missions found.

❯ Audit conciencia
  WebMCP challenge submission
  Research logistics market
```

Avoid forcing UUID copy/paste everywhere.

---

# 8. SHORT IDS

Display human-friendly short IDs while preserving full UUID internally.

Example:

```text
M-6998bc52
```

Allow:

```bash
conciencia mission inspect M-6998bc52
```

Resolve uniquely.

Full UUID continues to be canonical storage ID.

---

# 9. INTERACTIVE AND SCRIPTABLE MODES

Every important operation should work both ways.

Interactive:

```bash
conciencia mission create
```

Automation:

```bash
conciencia mission create \
  --name "Research logistics" \
  --type research \
  --objective "..." \
  --runtime automatic \
  --yes
```

Machine-readable:

```bash
conciencia mission list --json
```

Maintain deterministic exit codes.

Do not let beautiful CLI output break scripting.

---

# 10. GLOBAL FLAGS

Consider consistent global options:

```text
--json
--quiet
--verbose
--debug
--no-color
--yes
--project
--profile
```

Do not implement flags that have no immediate use.

---

# 11. DOCTOR AS A REAL DIAGNOSTIC SYSTEM

Upgrade:

```bash
conciencia doctor
```

It should inspect:

```text
Conciencia installation
Project initialization
Backend/API
Database
Redis
configuration
secret safety
models
provider credentials
MCP
WebMCP
runtimes
Docker
Git
filesystem permissions
network dependencies
pending migrations
```

Output:

```text
Conciencia Doctor

Core
✓ CLI                0.6.x
✓ Project            conciencia
✓ API                reachable
✓ PostgreSQL         ready
✓ Redis              ready

Models
✓ DeepSeek           configured
○ OpenAI             not configured
○ Anthropic          not configured

Runtimes
✓ Codex              detected
✓ Claude Code        detected
✓ OpenCode           detected
✓ OpenClaw           detected

Tools
✓ MCP                4 servers
✓ WebMCP             available

Security
✓ CLI secret redaction
! SMTP credentials should use app password

Result
READY WITH 1 WARNING
```

Diagnostics must be actionable.

For each failure:

```text
How to fix:
...
```

---

# 12. RUNTIME REGISTRY

Make external coding/agent runtimes first-class capabilities.

Current/planned candidates include:

```text
native
generic
codex
claude-code
opencode
openclaw
```

Other systems such as Hermes, Orca, Utopia or future runtimes must only become runtime adapters when they expose a stable executable/API/protocol suitable for execution.

Do not hard-code product names throughout Mission logic.

Use:

```text
RuntimeRegistry
       ↓
RuntimeAdapter
```

Suggested interface conceptually:

```python
class RuntimeAdapter:
    id
    capabilities
    availability()
    inspect()
    execute()
    stream()
    cancel()
    health()
    estimate_cost()
```

Adapt to existing architecture instead of blindly introducing this exact class.

---

# 13. CAPABILITY-BASED RUNTIME SELECTION

A Mission should request capabilities, not brand names whenever possible.

Example:

```text
requires:
  code_read: true
  code_write: true
  shell: true
  git: true
  mcp: optional
  long_running: true
```

Then:

```text
Runtime Resolver

Codex
96% match

Claude Code
94%

OpenCode
91%

OpenClaw
87%
```

Automatic selection should account for:

```text
capabilities
availability
user preference
Mission type
policy
cost
context
latency
previous success
```

Always expose why a runtime was selected.

---

# 14. `conciencia runtimes`

Make runtime visibility excellent.

```bash
conciencia runtime list
```

Example:

```text
RUNTIMES

● Codex
  coding · shell · git
  ready

● Claude Code
  coding · shell · MCP
  ready

● OpenCode
  coding · multi-provider
  ready

● OpenClaw
  agents · tools · messaging · MCP
  ready

○ Hermes
  unavailable
  adapter not installed
```

Then:

```bash
conciencia runtime inspect codex
```

Show capabilities, executable, version, health and policy.

---

# 15. RUNTIME DISCOVERY

During:

```bash
conciencia onboard
```

or:

```bash
conciencia runtime doctor
```

detect installed runtimes.

On Windows check relevant:

```text
PATH
PowerShell
Git Bash
WSL
```

Do not assume Unix-only environments.

This dogfooding session occurred in Git Bash on Windows and exposed shell-specific UX issues.

Treat Windows + Git Bash + WSL as first-class supported developer environments.

---

# 16. TOOLS ARE DIFFERENT FROM RUNTIMES

Maintain clean distinction:

```text
Mission
  ↓
Agent
  ↓
Harness
  ↓
Runtime
  ↓
Tools
```

Examples:

Runtime:

```text
Codex
Claude Code
OpenCode
OpenClaw
```

Tool/protocol:

```text
MCP
WebMCP
filesystem
Git
browser
database
HTTP
search
```

Do not mix everything into an “agents” list.

---

# 17. AGENT UX

Current:

```bash
conciencia agents
```

should migrate toward:

```bash
conciencia agent list
```

while preserving alias.

Example:

```text
AGENTS

Researcher
  research · synthesis · evidence

Software Engineer
  coding · debugging · implementation

Architect
  architecture · design · review

QA
  tests · validation · regression

Security Reviewer
  security · risk analysis
```

Then:

```bash
conciencia agent inspect researcher
```

should expose:

```text
role
capabilities
default harness
compatible runtimes
tools
permissions
recent Missions
success metrics when available
```

---

# 18. COMMAND PALETTE EXPERIENCE

When running:

```bash
conciencia
```

provide a keyboard-navigable command/task selector if supported safely by the current CLI library.

Think in terms of intent:

```text
What do you want to do?

❯ Ask Conciencia
  Audit project
  Build feature
  Fix bug
  Research topic
  Review code
  Run Mission
  Continue previous Mission
  View approvals
  Explore agents
  Explore tools
  Diagnose system
```

This should call existing commands/services.

Do not create duplicate business logic.

---

# 19. NATURAL LANGUAGE IS A FIRST-CLASS CLI INTERFACE

`conciencia ask` worked well in the first dogfooding run.

Promote it.

Support:

```bash
conciencia ask "investiga el mercado logístico paraguayo"
```

Eventually allow:

```bash
conciencia "investiga el mercado logístico paraguayo"
```

only if command ambiguity can be handled safely.

Natural language should resolve into a Mission proposal.

Never immediately perform destructive work.

---

# 20. MISSION PROPOSAL UX

Improve current proposal.

Example:

```text
╭─ Mission Proposal ─────────────────────╮
│ Research Paraguayan Logistics Market  │
╰───────────────────────────────────────╯

Type
research

Team
Research Squad
2 agents

Agents
Researcher          100%
Lead Researcher     100%

Runtime
DeepSeek via generic
why: research capability + lowest estimated cost

Workflow
1  Research
2  Synthesis
3  Approval 🔒

Estimated usage
~2,100 tokens
~$0.0013

Success criteria
✓ documented result
✓ evidence attached

Create this Mission?

❯ Create
  Edit
  Change team
  Change runtime
  Change budget
  Cancel
```

Avoid overwhelming users with internals unless requested.

Progressive disclosure.

---

# 21. MISSION WATCH

One of the flagship CLI experiences should be:

```bash
conciencia mission watch M-1234
```

or:

```bash
conciencia watch
```

Example:

```text
MISSION  Research logistics market

RUNNING  00:01:42

Research
████████████████████  complete

Synthesis
████████████░░░░░░░░  running

Approval
░░░░░░░░░░░░░░░░░░░░ waiting

Agents

Researcher       ✓ 42s
Lead Researcher  ✓ 51s
Synthesizer      ● running

Evidence
12 items

Signals
4

Usage
7,842 tokens
$0.018

Press:
a approve
p pause
l logs
e evidence
q detach
```

Use terminal capabilities conservatively.

Must degrade gracefully in non-interactive environments.

---

# 22. ERROR UX

Never expose framework-style errors as the primary user experience when the failure is predictable.

Instead of:

```text
Missing argument 'NAME'
```

prefer:

```text
Mission name is missing.

Example:
conciencia mission create "Audit API" \
  --objective "Review architecture and security"

Or run interactively:
conciencia mission create
```

Underlying Typer/Click errors may remain as fallback.

Add friendly validation before common failures.

---

# 23. EMPTY STATES

Current:

```text
Sin resultados.
```

is too weak.

Example:

```text
No leads matched:

"empresas logísticas"

Filters
country: PY
online: website

835 leads exist locally.

Try:
  remove --online website
  search "logística"
  run a new hunt

conciencia hunt --industry logistics --country PY
```

Empty states should teach the system.

---

# 24. SEARCH EXPLANATION

For:

```bash
conciencia search
```

when semantic embeddings are disabled, expose that when relevant.

Example:

```text
Search mode
structured + lexical

Semantic search
disabled

Enable with:
conciencia config set embeddings.provider openai
```

Do not pretend semantic retrieval was used.

---

# 25. `conciencia status`

Make it a useful mission-control overview.

Example:

```text
CONCIENCIA

Project
conciencia · v2-refactor

Missions
2 active
1 awaiting approval
14 completed

Runs
1 running
0 failed

Agents
11 available

Runtimes
4 / 5 ready

Tools
MCP 4
WebMCP ready

Knowledge
835 leads
embeddings disabled

Costs today
$0.12

System
healthy

Next
1 Mission requires your approval
```

---

# 26. `conciencia map`

Turn it into a powerful inspectability command.

Potential output:

```text
Mission
 ├── Team
 │    ├── Researcher
 │    └── Lead Researcher
 │
 ├── Harness
 │
 ├── Workflow
 │    ├── research
 │    ├── synthesis
 │    └── approval
 │
 ├── Runtime
 │    └── DeepSeek
 │
 └── Tools
      ├── Search
      ├── MCP
      └── WebMCP
```

Support project/system/mission scopes.

---

# 27. LOCAL VS REMOTE EXECUTION

The CLI may connect to:

```text
local Conciencia
remote Conciencia deployment
```

Make active target obvious.

Example:

```text
Target
local · http://localhost:8000
```

or:

```text
Target
production · mc.example.com
```

Never let users accidentally believe they are operating locally when pointed at production.

Production actions must be visually explicit.

---

# 28. PROFILES

Support eventual profiles without overbuilding:

```text
local
development
production
```

Potential:

```bash
conciencia --profile production status
```

Store no secrets in plaintext configuration if avoidable.

---

# 29. BEAUTIFUL BUT FUNCTIONAL

Use Rich/Typer capabilities where already available.

Style principles:

```text
green    success
yellow   warning
red      failure / destructive
cyan     active information
dim      secondary metadata
```

But respect:

```text
NO_COLOR
non-TTY
CI
--json
```

Do not make the CLI dependent on emoji.

Unicode should degrade gracefully.

---

# 30. PERFORMANCE

CLI startup should feel instant.

Avoid loading:

```text
LLMs
database-heavy state
embedding models
remote runtimes
```

unless necessary.

Use lazy discovery/caching where appropriate.

Target common informational commands to respond rapidly.

---

# 31. INSTALLATION UX

The manual test:

```bash
pip install -e backend/
```

was executed outside the repository and failed.

Improve documentation.

From repository root use explicit instructions.

Also evaluate providing a cleaner developer install:

```bash
pip install -e ./backend
```

and eventually a root-level install experience if architecture permits.

Do not restructure packaging purely for cosmetics unless justified.

`conciencia doctor` should detect broken/multiple installations.

---

# 32. SHELL SUPPORT

Test:

```text
Git Bash
PowerShell
cmd
WSL/bash
Linux/bash
```

Important shell syntax must behave consistently.

Never output copy-paste examples containing accidental shell metacharacters.

Test documentation snippets where feasible.

---

# 33. DOCUMENTATION TESTING

Add a mechanism to prevent bad CLI examples.

At minimum maintain CLI smoke tests for documented commands.

Potentially create:

```text
tests/cli/test_documented_commands.py
```

Validate parsing of examples.

Do not execute dangerous commands.

---

# 34. RUNTIME INSPIRATION POLICY

We are studying tools/ecosystems including:

```text
Codex
Claude Code
OpenCode
OpenClaw
Hermes
Orca
Utopia
and future systems
```

Do not clone them.

For each system ask:

```text
What interaction pattern is valuable?
What capability does it expose?
Can Conciencia orchestrate it?
Is it a Runtime, Tool, MCP server, Agent provider or Knowledge source?
```

Create an architecture note:

```text
docs/RUNTIME_ECOSYSTEM.md
```

with a capability matrix.

Example:

```text
System       Type        Integration path
Codex        runtime     CLI/runtime adapter
Claude Code  runtime     CLI/runtime adapter
OpenCode     runtime     CLI/runtime adapter
OpenClaw     runtime     CLI/API/MCP adapter
...
```

Only classify systems after verifying actual integration capabilities.

Never invent support.

---

# 35. PLUGIN-LIKE EXTENSIBILITY

Runtime and Tool integrations should eventually be discoverable without modifying Mission Core.

Concept:

```text
Conciencia Core
      │
Registries
 ┌────┴─────┐
Runtime    Tools
Adapters   Adapters
```

Mission Core should depend on capabilities/interfaces.

Not product-specific branching:

```python
if runtime == "codex":
...
elif runtime == "claude":
...
```

Avoid this architecture.

---

# 36. FIRST DOGFOOD SCENARIOS

After implementation test manually.

### Scenario A

```bash
conciencia
```

from outside a project.

Must provide useful onboarding.

### Scenario B

```bash
conciencia
```

inside Conciencia repository.

Must detect project.

### Scenario C

```bash
conciencia ask "investigar el mercado de logística"
```

Must produce Mission proposal.

### Scenario D

Create and execute the Mission.

### Scenario E

Approval flow.

### Scenario F

Runtime discovery.

### Scenario G

Secret redaction.

### Scenario H

Unknown command / missing arguments.

### Scenario I

No search results.

### Scenario J

Windows Git Bash.

---

# 37. TESTS

Add tests for:

```text
secret redaction
onboarding
project detection
next-action generation
short IDs
runtime discovery
runtime capability resolution
interactive/noninteractive behavior
JSON behavior
empty states
friendly errors
shell-safe examples
Mission proposal
approval UX
```

Do not snapshot huge ANSI outputs unnecessarily.

Test semantic behavior.

---

# 38. IMPLEMENTATION ORDER

P0

```text
SECRET REDACTION
```

Then:

```text
CLI audit
↓
command consistency
↓
shell-safe docs
↓
first-run experience
↓
doctor
↓
status
↓
Mission proposal UX
↓
next actions
↓
runtime registry UX
↓
runtime discovery
↓
mission watch
↓
short IDs/context
↓
error/empty states
↓
documentation
↓
cross-shell tests
```

Do not attempt everything in one uncontrolled rewrite.

Commit by coherent phase.

---

# 39. DO NOT BREAK

Preserve current working capabilities:

```text
LeadHunter
Missions
Agents
Teams
Harnesses
Signals
Evidence
Context Packs
WebMCP
Economics
Approvals
existing API
existing database
```

No database destructive migration for CLI cosmetics.

No parallel services.

---

# 40. SUCCESS CRITERION

The CLI is successful when a developer can install Conciencia, enter a repository and work without studying the internal architecture.

The desired mental model is:

```text
I have work to accomplish
        ↓
I open Conciencia
        ↓
I describe the objective
        ↓
Conciencia creates the Mission
        ↓
It chooses appropriate capabilities
        ↓
I supervise execution
        ↓
I approve important actions
        ↓
I receive evidence and outcome
```

Not:

```text
I need to understand 40 commands
before I can use Conciencia.
```

The CLI is not merely an administrative interface.

It is the primary operational interface to the Conciencia Mission Control Plane.

---

# REQUIRED FIRST RESPONSE

Before modifying code:

1. inspect the complete current CLI implementation;
2. identify the CLI framework and command tree;
3. reproduce the dogfooding problems;
4. locate the credential leak;
5. audit current runtime adapters;
6. audit documentation examples;
7. produce a prioritized CLI UX gap analysis;
8. propose the smallest coherent implementation phase;
9. list files expected to change;
10. provide tests that will validate the phase.

Then implement **P0 security + the first coherent CLI UX phase only**.

Run the relevant test suite before proceeding.

# LONG-TERM CLI DIRECTION — USER WORKSPACE & GUIDED OPERATING ENVIRONMENT

Conciencia CLI should gradually evolve beyond a command dispatcher into a lightweight operating workspace for autonomous technological work.

This is a long-term product direction.

Do NOT implement a large TUI now.

Build the underlying concepts incrementally.

## 1. Workspace Layer

Introduce the concept:

```text
Workspace
```

A Workspace is above an individual Project.

Conceptually:

```text
Workspace
├── Projects
├── Missions
├── Mission Templates
├── Harnesses
├── Agents / Teams
├── Saved items
├── Knowledge
├── History
├── Runtime preferences
├── Tool connections
└── User preferences
```

Do not duplicate Project-specific state.

Projects remain independent first-class objects.

A Workspace provides navigation and reusable context across them.

---

## 2. Root `conciencia` as Home

Eventually:

```bash
conciencia
```

should act as the user's operational home.

Example:

```text
CONCIENCIA

Workspace
Juan / Software

Current project
conciencia

Active
1 Mission running
1 approval waiting

Recent projects
Conciencia
LINTEAM
Cargo
LeadHunter

Runtimes
Codex       ready
Claude Code ready
OpenCode    ready
OpenClaw    ready

Actions
> Ask Conciencia
  Continue Mission
  Open Project
  Search Workspace
  Start Mission
  Approvals
  Tools
  Doctor
```

Do not require the current working directory to be a Conciencia project for the CLI to be useful.

---

## 3. Keyboard-Oriented Navigation

Design interactions so power users can operate primarily from the keyboard.

Potential conventions:

```text
a    Ask
m    Missions
p    Projects
r    Runtimes
t    Tools
w    Workspace
h    History
/    Search
?    Help
q    Exit
```

Only implement shortcuts where the underlying terminal interaction remains reliable.

Always preserve standard CLI commands.

---

## 4. Command Palette

Explore a lightweight command palette.

Conceptually:

```text
Search actions...

> test

Run tests
Inspect recent test failures
Create QA Mission
Open test evidence
Run project validation
```

This palette should dispatch existing domain actions.

Do not introduce duplicate orchestration.

---

## 5. Global Workspace Search

Eventually support search across:

```text
Projects
Missions
Runs
Evidence
Signals
Knowledge
Decisions
Saved items
Files/metadata when indexed
```

Example:

```text
/webmcp
```

could surface:

```text
Mission
WebMCP Challenge

Evidence
Browser action successful

Signal
WebMCP failure handling missing

Decision
WebMCP remains a Conciencia Tool Adapter

Document
DEVPOST_SUBMISSION.md
```

Search must preserve provenance.

---

## 6. Saved Items

Allow users to save reusable operational assets such as:

```text
Mission Templates
Harnesses
Searches
Useful resources
Context Packs
Agent Teams
Commands
Decisions
```

Do not turn Conciencia into a generic notes application.

A Saved Item should improve future Missions or workspace navigation.

---

## 7. Contextual Guidance

Conciencia may surface useful recommendations based on observable workspace state.

Examples:

```text
Git working tree is dirty
→ suggest checkpoint before write-enabled Mission

No tests detected
→ suggest QA setup

Production Mission without approval policy
→ warn

Repeated workflow
→ suggest Mission Template

Repeated user correction
→ suggest updating Harness

High context/token usage
→ suggest tighter Context Pack

Runtime repeatedly failing
→ suggest compatible alternative

Multiple related findings
→ suggest remediation Mission
```

Recommendations must be explainable and grounded in actual state.

Never fabricate best practices.

---

## 8. Guidance Levels

Use clear severity:

```text
INFO
RECOMMENDED
WARNING
```

Example:

```text
RECOMMENDED

You have repeated this workflow 4 times.

Why:
The Mission stages and agents were nearly identical.

Suggestion:
Create a reusable Mission Template.

[Create] [Later] [Don't suggest again]
```

Allow users to dismiss or disable individual recommendation types.

---

## 9. Learning from Usage

Conciencia should learn from explicit operational history without uncontrolled self-modification.

Observe:

```text
Mission
→ execution
→ correction
→ approval
→ outcome
```

Possible derived preferences:

```text
preferred runtime by Mission type
preferred Team
frequently used tools
frequent Project pairs
common approval policy
repeated workflow
```

Do not silently rewrite Agents, Harnesses, policies or Templates.

Instead suggest changes.

Human-controlled learning.

---

## 10. Workspace Context

Potential context hierarchy:

```text
User Workspace Context
        ↓
Project Context
        ↓
Mission Context
        ↓
Context Pack
        ↓
Agent Runtime
```

Keep each layer bounded.

Do not indiscriminately inject global workspace history into every Mission.

---

## 11. Developer Tool Surface

The Workspace should provide discoverability for connected capabilities.

Example:

```text
TOOLS

Development
Git
Docker
pytest
npm

Runtimes
Codex
Claude Code
OpenCode
OpenClaw

Protocols
MCP
WebMCP

Data
PostgreSQL
Redis

Knowledge
Repository
Docs
Previous Missions
```

The list should be capability-driven and detected dynamically.

---

## 12. Best-Practice Engine

Do not create a generalized AI coach.

If implemented, keep the scope strictly operational and technological.

The engine can inspect:

```text
Project state
Mission history
Runs
Failures
Costs
Evidence
Git
Tests
Runtime health
Approvals
Context usage
```

and produce grounded recommendations.

Example:

```text
Signal:
3 implementation Missions failed during deployment validation.

Evidence:
Runs M-102, M-108, M-111.

Recommendation:
Introduce deployment-readiness validation before production deploy Missions.
```

This may itself create a Signal.

---

## 13. Workspace Without Project

Running:

```bash
conciencia
```

from `~` should eventually be valid.

Example:

```text
No active project.

Recent projects:

> Conciencia
  LINTEAM
  Cargo
  LeadHunter

Actions:

Open project
Search workspace
Ask Conciencia
Create project
Doctor
```

This is preferable to displaying only framework help.

---

## 14. Product Boundary

Conciencia Workspace is NOT:

```text
an IDE
a file manager
a generic personal assistant
an ERP
a notes application
another terminal emulator
```

It is:

> The operational workspace from which a user creates, supervises, reuses and learns from technological Missions.

Every feature should strengthen that purpose.

---

## 15. IMPLEMENTATION STRATEGY

Do not build this entire vision now.

Incremental order:

```text
Root CLI home
↓
Recent projects
↓
Current/recent Missions
↓
Interactive actions
↓
Runtime/tool overview
↓
Workspace persistence
↓
Global search
↓
Saved assets
↓
Contextual recommendations
↓
Usage-derived suggestions
```

CLI fundamentals and Mission execution remain higher priority than a sophisticated TUI.

---

## NORTH STAR

The long-term experience should feel like:

```text
I open Conciencia.

Conciencia knows:
what I am working on,
what tools are available,
what Missions are active,
what needs my approval,
what happened previously,
and what may improve the next execution.

I remain in control.
```

The system should make complex agentic tooling easier to operate without hiding important execution details.

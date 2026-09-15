# MASTER PROMPT — CONCIENCIA TERMINAL / WORKSPACE EXPERIENCE V1

You are working on the existing Conciencia repository.

Conciencia is an agentic workspace/control plane. It already has substantial production code and MUST NOT be redesigned from scratch.

The goal of this task is to evolve the current Conciencia CLI into a lightweight, fast, intuitive and progressively powerful workspace interface, while laying the architecture for a future Web CLI and persistent background execution.

This is NOT a request to build another Claude Code, Codex or OpenCode clone.

Conciencia should orchestrate those runtimes/tools when useful.

Core product idea:

    "Conciencia is not another AI chat.
     It is the workspace that understands the work."

The experience should make it easy to:

- understand the current workspace;
- find relevant work/context;
- see what needs attention;
- navigate projects;
- inspect missions/runs;
- interact with approvals;
- ask questions;
- create structured work;
- delegate to agents/runtimes;
- inspect evidence/artifacts;
- understand what happened;
- progressively automate the workspace.

The interface must be:

- lightweight;
- fast;
- keyboard-first;
- clean;
- intuitive;
- discoverable;
- scriptable;
- progressively learnable;
- pleasant enough for daily use;
- powerful enough that advanced users can master it over time.

Do NOT sacrifice existing CLI scripting capabilities for interactive UX.

============================================================
0. NON-NEGOTIABLE ENGINEERING RULE
============================================================

DO NOT START IMPLEMENTING IMMEDIATELY.

First inspect the repository and map the existing architecture.

We already have concepts/features around:

- CLI `conciencia`
- workspace dashboard
- projects
- missions
- workflows
- runs
- approvals
- agents
- runtimes
- harnesses
- tools
- ContextPacks
- retrieval
- WorkItems
- reports
- deliverables
- evidence
- signals
- economics
- connections
- configuration/settings
- observability
- `conciencia ask`
- `conciencia work`
- `conciencia project`
- `conciencia mission`
- `conciencia runtime`
- `conciencia approvals`
- `conciencia report`
- `conciencia doctor`

Reuse existing domain/application services.

Do NOT create duplicate parallel abstractions such as:

TerminalMission
TerminalProject
TerminalApproval
WebMission
CLIWorkItem

Presentation layers must consume the canonical existing domain/application layer.

Preserve Clean Architecture.

Target:

              PRESENTATION
       ┌──────────┬──────────┐
       │          │          │
      CLI        TUI      future Web CLI
       │          │          │
       └──────────┼──────────┘
                  │
           APPLICATION LAYER
                  │
      Commands / Queries / Events
                  │
                DOMAIN
                  │
 Mission / Run / Approval / Project
 WorkItem / Agent / Harness / Evidence
 ContextPack / Deliverable / Report
                  │
           INFRASTRUCTURE
                  │
 DB / Retrieval / Git / Queue / APIs
                  │
              RUNTIMES
                  │
 Codex / Claude / OpenClaw / MCP / LLM

CLI/TUI must NOT contain business logic.

============================================================
1. FIRST DELIVERABLE — REPOSITORY AUDIT
============================================================

Before modifying code, inspect:

- CLI entry points;
- Typer/Click command hierarchy;
- presentation modules;
- application services;
- mission services;
- approval services;
- project services;
- runtime registry;
- WorkItem services;
- report services;
- retrieval/context services;
- settings;
- persistence;
- event/run architecture;
- frontend only to understand future integration boundaries.

Find:

1. what already exists;
2. what can be reused;
3. UX inconsistencies;
4. architectural gaps;
5. commands that unnecessarily fail because a subcommand/argument is missing;
6. places where UUIDs leak unnecessarily into UX;
7. places where presentation logic contains business logic;
8. existing mechanisms that could support interactive mode;
9. existing mechanisms that could later support detached/background execution;
10. tests protecting current behavior.

Produce:

docs/terminal/TERMINAL_V1_AUDIT.md

Include:

- existing architecture;
- reusable services;
- proposed minimal changes;
- risks;
- migration strategy;
- explicit list of things we should NOT rewrite.

Only after this audit should implementation begin.

============================================================
2. CURRENT DOGFOOD PROBLEMS
============================================================

These are real UX problems observed while using Conciencia.

Current:

    conciencia mission

returns:

    Missing command.

Current:

    conciencia config

returns:

    Missing command.

Current:

    conciencia approve <mission_id>

requires STEP_INDEX even when the user may have only one pending approval.

Current:

    conciencia approvals

shows pending approvals but does not make the next action sufficiently obvious/interactive.

Current mission IDs often expose long UUIDs.

The root `conciencia` command already gives useful workspace status including:

CURRENT CONTEXT
PROJECTS
AI WORKFORCE
ACTIVE WORK
NEEDS ATTENTION
RECENT WORK
CONNECTIONS
RECOMMENDED
QUICK ACTIONS

This is useful and MUST NOT be discarded.

Improve it rather than replacing it blindly.

============================================================
3. PHASE A — CLI UX HARDENING
============================================================

Implement a coherent CLI UX before building a large TUI.

### 3.1 Smart command defaults

Commands that represent useful resources should produce useful information when invoked without subcommands.

Examples:

    conciencia mission

should behave approximately like a concise mission overview/list instead of only throwing "Missing command".

    conciencia config

should display current configuration, equivalent or similar to:

    conciencia config get

when safe.

Likewise inspect other command groups for sensible defaults.

Do NOT introduce surprising destructive defaults.

### 3.2 Human-friendly IDs

Keep UUIDs internally.

Introduce/use stable short human references where architecture permits:

    M-83F1
    R-29C2
    A-104

Do NOT replace canonical UUID primary keys.

Implement a resolver capable of accepting:

- full UUID;
- existing short ID if already supported;
- canonical human reference.

Commands should increasingly allow:

    conciencia mission M-83F1
    conciencia approve M-83F1
    conciencia watch M-83F1

Avoid breaking existing UUID usage.

### 3.3 Approval ergonomics

Improve:

    conciencia approve <mission>

If exactly ONE pending approval exists for that mission:

- resolve its step automatically;
- show what is being approved;
- request confirmation if appropriate;
- execute through the canonical approval service.

If multiple approval steps are pending:

show them and ask/select, or tell the user exactly which references are available.

Explicit step syntax must remain supported:

    conciencia approve M-83F1 3

Rejection must remain explicit and safe.

Example desired UX:

    $ conciencia approve M-83F1

    Mission
    Research con harness

    Approval
    Step 3 · External research

    Approve? [Y/n]

Never bypass approval policy.

### 3.4 Actionable errors

Errors should teach the interface.

Avoid only:

    Missing STEP_INDEX

Prefer:

    This mission has 2 pending approval steps:

    3  External research
    6  External communication

    Run:
    conciencia approve M-83F1 3

Do the same where appropriate across the CLI.

### 3.5 Consistent output hierarchy

Establish presentation primitives/styles for:

- title;
- context;
- status;
- attention;
- success;
- warning;
- error;
- recommendation;
- command hint.

Do NOT overdecorate.

Conciencia should feel technical, calm and premium.

Avoid excessive emoji.

Optimize for terminal readability.

### 3.6 Machine-readable mode

Interactive improvements must NOT compromise scripting.

Existing or new relevant commands should preserve/support structured output such as:

    --json

where architecturally appropriate.

TTY detection should distinguish interactive human usage from pipes/scripts where necessary.

============================================================
4. PHASE B — CONCIENCIA NAVIGATOR / LIGHTWEIGHT TUI
============================================================

Do NOT build a giant terminal application.

Build the smallest useful interactive shell/navigation experience.

The existing:

    conciencia

currently shows workspace status.

Preserve fast startup.

Determine during audit whether:

A) `conciencia` should enter interactive mode when running in a TTY;

or

B) interactive mode should initially be:

    conciencia shell

or:

    conciencia ui

Prefer the migration path with least regression risk.

The eventual desired experience is:

    CONCIENCIA

    Global workspace

    Attention
      4 approvals
      1 failed mission
      git dirty

    Active
      Contactar lead logistik       approval
      Mision WebMCP E2E             approval
      research theweb...            failed

    Recent
      Professional workspace report
      Professional work report

    ------------------------------------------------

    /  navigate/search
    >  ask/instruct
    @  agent/harness
    #  project/context
    !  attention/actions

    ? help
    q quit

This does NOT need to be visually complex.

Performance and usability are more important than animation.

============================================================
5. UNIVERSAL INTERACTION LANGUAGE
============================================================

Introduce a small interaction grammar.

Target concepts:

    /     navigate / search
    >     ask / instruct
    @     agent or harness
    #     project/context
    !     attention/action

Examples:

    / webmcp

    / approvals

    / failed missions

    > qué requiere mi atención?

    > resumime qué hicimos esta semana

    @codex inspect frontend

    @claude analyze architecture

    @media create launch campaign

    @growth find B2B opportunities

    #conciencia

    #linteam

    ! approvals

Do NOT implement all natural language semantics with an LLM.

Use deterministic routing first.

Priority:

1. exact command;
2. known alias;
3. fuzzy navigation/search;
4. lexical/hybrid retrieval;
5. LLM interpretation only when useful.

Fast deterministic paths should remain fast.

============================================================
6. `/` — WORKSPACE NAVIGATOR
============================================================

Implement a first useful version of `/`.

It should search/navigate canonical workspace resources such as:

- projects;
- missions;
- runs;
- WorkItems;
- reports/deliverables;
- evidence where supported;
- commands/actions.

Example:

    / webmcp

could return:

    PROJECT
      Conciencia

    MISSIONS
      Mision WebMCP E2E
      crear deploy de conciencia a Devpost

    REPORTS
      Professional workspace report

Do not invent resources that cannot currently be queried reliably.

Use existing retrieval/search services.

If embeddings are unavailable, lexical retrieval must continue working.

The current system already reports:

    Workspace retrieval is lexical because embeddings are unavailable.

This should be treated as graceful degradation, not failure.

============================================================
7. `>` — CONVERSATION WITH THE WORKSPACE
============================================================

This is NOT intended to become a generic chatbot.

`>` represents a conversation with Conciencia about the workspace.

Example:

    > qué requiere mi atención?

Expected response should derive from canonical workspace state:

    4 approvals are waiting.
    1 mission failed.
    repository has uncommitted changes.
    ...

Then offer actions where useful.

The important conceptual transformation is:

    conversation
        ↓
    structured intent
        ↓
    query OR proposed work
        ↓
    mission/work item when necessary
        ↓
    agent/runtime
        ↓
    evidence/artifacts
        ↓
    result

Do NOT automatically convert every question into a Mission.

Queries remain queries.

Work becomes structured work.

============================================================
8. RUNTIME DIFFERENTIATION
============================================================

Do NOT recreate Codex, Claude Code or OpenCode.

Treat external coding/agent runtimes as workers/providers.

Conciencia should be the orchestration/control layer.

Conceptually:

                  USER
                    │
                CONCIENCIA
                    │
        ┌───────────┼───────────┐
        │           │           │
      Codex       Claude     OpenClaw
        │           │           │
        └───────────┼───────────┘
                    │
                 Evidence
                    │
                  Mission
                    │
                  Report

Conciencia's value is:

- workspace context;
- orchestration;
- structured work;
- runtime selection;
- approvals;
- evidence;
- history;
- reports;
- economics;
- governance;
- cross-project understanding.

Do not hide the runtime used.

But users should primarily think in terms of WORK, not provider/model selection.

============================================================
9. `@` — AGENT / HARNESS ROUTING
============================================================

Build the interaction boundary, not necessarily every future harness.

Examples:

    @codex inspect frontend

    @claude analyze this architecture

    @openclaw deploy staging

The router must reuse the existing runtime registry.

Do NOT hardcode providers throughout presentation code.

Design it so future harness packs can expose capabilities such as:

    @media
    @growth
    @research
    @audit
    @collections

without changing the core shell architecture.

============================================================
10. HARNESS PACKS — EXTENSION MODEL
============================================================

Prepare architecture/documentation for future capability packs.

Examples:

Conciencia Media:

    research
      → concept
      → copy
      → visual
      → review
      → approval
      → schedule
      → publish
      → measure

Conciencia Growth:

    signals
      → research
      → qualification
      → evidence
      → CRM
      → outreach approval
      → measurement

These should NOT become separate duplicated applications.

Model them as extensions/capability packs around existing primitives:

- agents;
- harnesses;
- workflows;
- missions;
- tools;
- evidence;
- approvals.

For V1, architecture + extension contracts may be enough.

Do not prematurely implement complete Media/Growth systems.

Create:

docs/terminal/HARNESS_PACKS.md

============================================================
11. COMMAND PALETTE
============================================================

Design a reusable command registry.

The registry should allow presentation layers to discover commands/actions instead of hardcoding menus separately.

Potential conceptual structure:

CommandDefinition
- id
- name
- aliases
- description
- category
- arguments
- interactive
- machine_safe
- handler/application command reference

Do NOT create this abstraction if an equivalent registry already exists.

Audit first.

This registry should eventually serve:

- CLI help;
- interactive shell;
- `/` navigator;
- future Web CLI;
- command palette.

============================================================
12. KEYBOARD-FIRST UX
============================================================

For interactive mode consider:

    /
        search

    ?
        help

    q
        quit/back when safe

    ↑ ↓
        navigation

    Enter
        inspect/select

    a
        approve where contextually safe

    r
        reject where contextually safe

    Esc
        cancel/back

Do not implement obscure keybindings.

Everything important should remain discoverable.

============================================================
13. PERFORMANCE BUDGET
============================================================

Conciencia should feel instant.

Do NOT:

- call an LLM during startup;
- initialize every runtime during startup;
- perform network calls unnecessarily;
- load full reports;
- perform embedding generation synchronously;
- scan entire repositories without need.

Prefer:

- lazy loading;
- cached summaries;
- bounded queries;
- deterministic commands;
- asynchronous/background work.

Measure startup/runtime where practical.

Add performance regression tests or benchmarks where useful, without creating brittle CI.

============================================================
14. PHASE C — BACKGROUND EXECUTION DESIGN
============================================================

IMPORTANT:

Do not automatically implement a large queue system before auditing existing run/execution infrastructure.

First design the minimal persistent execution architecture.

Target behavior:

    conciencia work "audit frontend"

returns quickly:

    ✓ Mission created M-29AF
    ✓ Context packed
    ✓ Worker: Codex
    ✓ Running in background

    conciencia watch M-29AF

Closing the terminal must NOT conceptually mean the work is cancelled if it has been explicitly submitted as background work.

Desired architecture:

CLI / Web CLI
      │
      ▼
Application API
      │
      ▼
Persistent Job / Run
      │
      ▼
Worker
      │
      ├── Codex
      ├── Claude
      ├── OpenClaw
      └── Internal Harness
      │
      ▼
Events
      │
      ├── Evidence
      ├── Artifacts
      └── Logs

Design for:

- queued;
- running;
- waiting_approval;
- completed;
- failed;
- cancelled;

and ideally:

- retry;
- attach/watch;
- resume where semantics permit.

DO NOT silently run long-lived foreground Docker commands.

Long-lived processes must be explicit.

Development examples could include:

    conciencia worker start

but this command should clearly communicate that it remains running.

Production should be compatible with a process manager such as systemd or the deployment architecture already used by the project.

Do NOT introduce Docker as a mandatory runtime dependency merely for background execution.

============================================================
15. EVENT STREAM
============================================================

Design an event model that can eventually feed both terminal and web.

Example conceptual events:

MissionCreated
RunQueued
RunStarted
StepStarted
ToolStarted
ToolCompleted
EvidenceCreated
ApprovalRequested
ApprovalResolved
ArtifactCreated
RunCompleted
RunFailed

Reuse existing event/audit abstractions if available.

Avoid building another duplicate event system.

The same event stream should eventually support:

    conciencia watch M-29AF

and future:

    /cli

via SSE/WebSocket or another appropriate transport.

============================================================
16. FUTURE WEB CLI BOUNDARY — DO NOT OVERBUILD YET
============================================================

We want a future authenticated route approximately:

    /cli

or:

    /workspace

Conceptually:

┌──────────────────┬─────────────────────────────────────┐
│ conciencia       │ Global workspace                    │
│                  │                                     │
│ WORKSPACES       │ 4 approvals · 1 failed             │
│ ● Global         │                                     │
│   Conciencia     │ > what needs my attention?          │
│   LinTeam        │                                     │
│                  │ Conciencia                          │
│ MISSIONS         │ ...                                 │
│                  │                                     │
│ AGENTS           │ [inspect] [retry]                   │
│ Codex      ready │                                     │
│ Claude     ready │ ----------------------------------  │
│ OpenClaw   ready │ / search   > ask   @ agent          │
└──────────────────┴─────────────────────────────────────┘

BUT:

Do NOT implement a fake browser terminal.

Do NOT expose unrestricted Bash to the browser.

Web CLI should be a semantic client of the Conciencia Application API.

It must eventually consume the SAME:

- commands;
- queries;
- missions;
- approvals;
- event stream;
- runtime registry;

as CLI/TUI.

For this implementation cycle:

focus on architecture boundary and backend contracts.

Only make minimal frontend changes if necessary.

============================================================
17. CURRENT FRONTEND
============================================================

Do NOT redesign the current frontend.

If touched, changes must be subtle and additive.

Possible future navigation:

Dashboard
Projects
Missions
Reports
────────────
Terminal

Potential global shortcut:

Ctrl+K / Cmd+K

for a Conciencia command/navigator palette.

Do not implement visual changes unless they are justified by reusable backend/application capability.

Keep current visual identity.

============================================================
18. SECURITY
============================================================

Critical.

Never allow natural language input to bypass:

- approval gates;
- permissions;
- runtime boundaries;
- tool policies;
- project/workspace isolation.

`@agent do X`

must go through exactly the same policies as equivalent API/CLI operations.

The interactive shell is a presentation adapter, NOT a privileged execution path.

Do not expose secrets through:

    conciencia config

The current redaction behavior must remain or improve.

Never log raw secrets.

Do not expose unrestricted shell execution in Web CLI.

============================================================
19. OBSERVABILITY
============================================================

Interactive actions should remain observable through existing mechanisms.

Preserve/extend:

- mission attribution;
- run attribution;
- runtime used;
- evidence;
- approval decisions;
- timestamps;
- errors;
- artifacts;
- costs/economics where supported.

A beautiful terminal that bypasses observability is unacceptable.

============================================================
20. TESTING
============================================================

Protect current behavior.

The project previously reached a large green regression suite. Do not assume the exact current count without running the repository's current suite.

Add focused tests for:

- command defaults;
- ID resolver;
- approvals with one pending step;
- approvals with multiple steps;
- explicit step backwards compatibility;
- actionable errors;
- command registry if implemented;
- search/navigation;
- TTY vs non-TTY behavior;
- structured output;
- runtime routing boundary;
- permissions/approval preservation;
- lexical retrieval fallback;
- shell parser;
- no-LLM deterministic commands.

Do not create tests tied to ANSI rendering unnecessarily.

Test semantics separately from presentation.

Run:

- focused tests;
- full relevant regression;
- compile/type checks;
- frontend build only if frontend is touched;
- git diff --check.

============================================================
21. IMPLEMENTATION ORDER
============================================================

Follow this order.

PHASE A1
Repository audit.

STOP and document architecture before major modifications.

PHASE A2
CLI UX:
- defaults;
- human IDs/resolution;
- approvals;
- actionable errors;
- consistent presentation.

PHASE A3
Reusable command/action registry if justified.

PHASE B1
Minimal interactive shell.

PHASE B2
`/` workspace navigator.

PHASE B3
`>` workspace conversation using existing ask/retrieval services.

PHASE B4
`@` runtime/agent routing boundary.

PHASE C1
Background execution architecture audit/design.

PHASE C2
Implement only the minimal persistent execution changes that fit the existing architecture safely.

PHASE C3
watch/event stream.

Do NOT build Web CLI before these contracts are stable.

============================================================
22. DOGFOOD SCENARIOS
============================================================

After implementation test real scenarios.

SCENARIO 1

    conciencia

User immediately understands:

- workspace;
- attention;
- active work;
- recent work;
- next actions.

SCENARIO 2

    conciencia mission

must provide useful output without forcing --help.

SCENARIO 3

    conciencia config

must provide safe useful output.

SCENARIO 4

    conciencia approvals

must clearly expose pending decisions.

SCENARIO 5

    conciencia approve <mission-with-one-pending-approval>

must not require unnecessary STEP_INDEX.

SCENARIO 6

Interactive:

    / webmcp

must search/navigate workspace resources.

SCENARIO 7

    > qué requiere mi atención?

must use workspace state and not fabricate information.

SCENARIO 8

    @codex inspect current frontend

must route through canonical runtime/work abstractions, not directly spawn arbitrary behavior from presentation code.

SCENARIO 9

Embeddings disabled.

`/` must remain useful using lexical retrieval.

SCENARIO 10

Pipe/script usage must remain usable.

============================================================
23. PRODUCT EXPERIENCE PRINCIPLES
============================================================

Use these principles to resolve ambiguous implementation choices.

1. FAST BEFORE CLEVER

Deterministic operations should not invoke AI.

2. SIMPLE ENTRY, DEEP MASTERY

A beginner can type:

    > what needs attention?

An advanced user can type:

    conciencia mission list --status waiting_approval --json

Both are first-class.

3. WORK BEFORE CHAT

The primary abstraction is work, not conversation.

4. CONTEXT IS AN ASSET

Conversations should connect to projects, missions, evidence and history where relevant.

5. PROVIDERS ARE REPLACEABLE

Codex/Claude/OpenClaw are workers.

Conciencia remains the control plane.

6. HUMAN CONTROL

Important actions remain gated.

7. ONE DOMAIN MODEL

CLI/TUI/Web must not create separate business models.

8. GRACEFUL DEGRADATION

No embeddings?
Use lexical.

No external runtime?
Use available capabilities.

No network?
Local deterministic navigation should still work where possible.

9. CLEAN INTERFACE

Do not flood the user with internal implementation details.

10. EVERYTHING IMPORTANT SHOULD BE INSPECTABLE

Conciencia should make work understandable, not magical.

============================================================
24. DOCUMENTATION
============================================================

Create/update:

docs/terminal/TERMINAL_V1_AUDIT.md
docs/terminal/TERMINAL_ARCHITECTURE.md
docs/terminal/INTERACTION_LANGUAGE.md
docs/terminal/HARNESS_PACKS.md
docs/terminal/BACKGROUND_EXECUTION.md

Keep docs concise and architectural.

Do not produce huge speculative documents disconnected from implementation.

============================================================
25. RETURN FORMAT
============================================================

At the end return:

# CONCIENCIA TERMINAL V1 — IMPLEMENTATION REPORT

## Audit
- existing components reused
- architectural findings

## Implemented
- exact capabilities added

## UX before → after
- concrete examples

## Architecture
- new components
- reused components
- dependency direction

## Background execution
- current state
- implemented state
- remaining work

## Web CLI readiness
- contracts now available
- remaining blockers

## Tests
- focused tests
- regression result
- build/type/compile result

## Performance
- startup observations
- deterministic paths
- LLM/network calls avoided

## Security
- approval behavior
- permissions
- secret handling

## Files changed
- concise list

## Dogfood
Show actual output for:

    conciencia
    conciencia mission
    conciencia approvals
    conciencia approve <test mission>
    interactive /
    interactive >
    interactive @

## Remaining work
Only genuine remaining items.

============================================================
26. IMPORTANT SCOPE CONTROL
============================================================

Do not turn this into a months-long rewrite.

Prefer small vertical slices.

If during audit you discover that implementing Phase C correctly requires a significant architectural migration:

DO NOT hack around it.

Complete A/B cleanly and document the exact C migration required.

Likewise, do not implement the full Web CLI merely because frontend code exists.

The immediate objective is:

    make Conciencia terminal dramatically better
                 +
    establish the shared interaction architecture
                 +
    dogfood it
                 +
    prepare persistent execution

without compromising the existing system.

============================================================
27. FINAL NORTH STAR
============================================================

The desired feeling is not:

    "I opened an AI chatbot."

It is:

    "I entered my workspace."

Conciencia should progressively become the place where the user can understand:

- what exists;
- what changed;
- what is happening;
- what needs attention;
- what agents are doing;
- why something happened;
- what evidence exists;
- what should happen next;

and then act on it.

Start with the repository audit.

Do not make major code changes until the existing architecture and reusable services are understood.
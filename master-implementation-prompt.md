# MASTER IMPLEMENTATION PROMPT

# Conciencia — Mission Orchestration Control Plane

## From existing platform to daily-use technological mission orchestrator

You are working inside the existing **Conciencia** repository, currently derived from the `mission-control` project.

Your job is NOT to redesign the project from scratch.

Your job is to carefully inspect the current implementation, preserve working architecture, identify gaps, and evolve Conciencia into a professional open-source **Mission Orchestration Control Plane for technological work**.

---

# 0. PRODUCT DEFINITION

Conciencia is:

> **An open control plane for orchestrating technological missions across AI agents, coding runtimes, tools, workflows, knowledge and human approvals.**

Primary concept:

# Mission

Everything meaningful in Conciencia should eventually connect to a Mission.

A Mission represents an objective that may require:

* research
* planning
* reasoning
* software engineering
* code review
* testing
* architecture
* debugging
* infrastructure
* DevOps
* automation
* AI-agent design
* harness engineering
* MCP
* integrations
* data analysis
* technical audits
* product research
* technical commercial discovery
* opportunity research
* proposal preparation
* validation

Conciencia is NOT intended to become a generic assistant for arbitrary personal tasks.

It should remain focused on technology, software, AI systems, digital products and related business workflows.

---

# 1. CORE PRODUCT PRINCIPLE

The system should progressively support this operating model:

```text
User Intent
    ↓
Mission
    ↓
Context Assembly
    ↓
Mission Plan
    ↓
Agent / Team Selection
    ↓
Runtime Selection
    ↓
Workflow / DAG
    ↓
Tools
    ↓
Execution
    ↓
Human Approvals
    ↓
Evidence
    ↓
Outcome
    ↓
Observability
    ↓
Learning / Memory
```

A Mission is not merely a prompt.

A Mission is a governed unit of technological work.

---

# 2. HARD ARCHITECTURAL BOUNDARY

Conciencia MUST NOT become:

* another Claude Code
* another Codex
* another OpenClaw
* another generic chatbot
* another workflow builder clone
* another IDE
* another full ERP
* another generic CRM
* another autonomous-agent toy

Conciencia must orchestrate those systems when useful.

Example:

```text
                Conciencia
                    │
               Mission Layer
                    │
      ┌─────────────┼─────────────┐
      │             │             │
   Claude Code    Codex       OpenClaw
      │             │             │
      └─────────────┼─────────────┘
                    │
            Tools / MCP / APIs
```

Conciencia determines:

* objective
* context
* agents
* permissions
* workflow
* runtime
* tools
* budget
* approvals
* success criteria

The runtime performs specialized execution.

---

# 3. FIRST TASK: AUDIT BEFORE MODIFYING

Before implementing anything:

Inspect the full repository.

Specifically inspect:

* README
* architecture
* API
* domain models
* services
* CLI
* existing agents
* workflows
* runtime adapters
* MCP
* memory
* knowledge
* observability
* approvals
* LeadHunter
* authentication
* database
* frontend
* Docker
* tests
* migrations
* configuration
* documentation

Create an internal implementation matrix:

```text
CAPABILITY
STATUS
CURRENT IMPLEMENTATION
QUALITY
MISSING PIECES
RECOMMENDED ACTION
```

Use:

* KEEP
* IMPROVE
* REFACTOR
* DEPRECATE
* BUILD

Do NOT duplicate capabilities that already exist.

Do NOT introduce a parallel architecture.

Prefer extending existing domain services.

---

# 4. MISSION AS THE CENTRAL DOMAIN OBJECT

Audit the current Mission implementation.

A professional Mission should eventually support:

```yaml
mission:
  id:
  name:
  description:
  objective:

  project:
  type:

  status:

  requester:

  context:
  agents:
  team:
  workflow:
  runtime:
  tools:

  permissions:
  approval_policy:

  budget:
  cost_limit:
  token_limit:
  runtime_limit:

  success_criteria:

  inputs:
  outputs:

  evidence:

  signals:

  outcome:

  created_at:
  started_at:
  completed_at:
```

Do NOT implement all fields blindly.

Map them against what already exists.

Extend only where useful.

---

# 5. MISSION TYPES

Support varied but technologically coherent missions.

Initial categories:

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

The system must remain extensible.

Do not hard-code business logic unnecessarily.

---

# 6. CLI AS A FIRST-CLASS INTERFACE

Conciencia CLI must become a complete operational interface.

The web application must NOT be required for ordinary mission execution.

Target commands:

```bash
conciencia
conciencia status
conciencia init
conciencia doctor

conciencia project
conciencia project inspect

conciencia mission list
conciencia mission create
conciencia mission inspect
conciencia mission plan
conciencia mission run
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
conciencia team run

conciencia workflow list
conciencia workflow inspect
conciencia workflow run

conciencia tool list
conciencia runtime list
conciencia model list

conciencia context inspect
conciencia knowledge search
conciencia memory search

conciencia approvals
conciencia approve
conciencia reject

conciencia cost
conciencia signals

conciencia modules
conciencia mcp

conciencia ask
```

Reuse existing CLI foundations.

Do not create another disconnected CLI codebase.

CLI → domain services → API/shared domain.

---

# 7. CONCIENCIA INIT

Implement or improve:

```bash
conciencia init
```

When executed inside a repository, Conciencia should detect useful project context.

Possible detection:

* git repository
* branch
* remotes
* languages
* frameworks
* package managers
* Docker
* Compose
* tests
* README
* architecture files
* environment templates
* CI
* recent commits

Create:

```text
.conciencia/
```

Possible structure:

```text
.conciencia/
├── project.yaml
├── context.md
├── policies.yaml
├── agents.yaml
└── workflows/
```

Keep this minimal.

Do not generate unnecessary boilerplate.

---

# 8. PROJECT CONTEXT

Conciencia should understand the current technological project.

Example:

```bash
conciencia project inspect
```

Output:

```text
PROJECT

Cargo Platform

Repository
Git detected

Stack
FastAPI
React
PostgreSQL
Docker

Branch
feat/pricing-engine

Recent changes
...

Active missions
...

Known architecture
...

Relevant agents
...
```

Project context should be reusable by Missions.

---

# 9. NATURAL LANGUAGE MISSION CREATION

Implement a higher-level interface:

```bash
conciencia ask "investigate how to implement WebMCP in this project and create a mission"
```

Expected internal pipeline:

```text
Natural language
      ↓
Intent classification
      ↓
Project context
      ↓
Knowledge retrieval
      ↓
Available agent registry
      ↓
Tool registry
      ↓
Runtime registry
      ↓
Mission proposal
```

Before destructive or expensive execution, show a proposal.

Example:

```text
MISSION PROPOSAL

Objective
Implement WebMCP integration.

Agents
Research Agent
Software Engineer
QA Agent

Workflow

Research
   ↓
Architecture
   ↓
Human Approval
   ↓
Implementation
   ↓
Tests

Runtime
Codex

Estimated cost
...

Create Mission? [Y/n]
```

---

# 10. AGENT REGISTRY

Agents must remain reusable capabilities.

Agents are not Missions.

Mission:

> objective

Agent:

> capability

Examples:

```text
researcher
software-engineer
architect
qa
security-reviewer
devops
data-analyst
technical-product-researcher
automation-engineer
```

Agent definitions should describe:

```yaml
agent:
  name:
  role:
  capabilities:
  tools:
  supported_runtimes:
  default_model:
  permissions:
  context_requirements:
```

Avoid creating dozens of redundant agents.

Prefer a smaller high-quality registry.

---

# 11. TEAMS

Support reusable agent teams.

Example:

```yaml
team:
  name: software-delivery

  agents:
    - architect
    - software-engineer
    - qa

  workflow:
    - architecture
    - implementation
    - validation
```

CLI:

```bash
conciencia team run software-delivery
```

Teams should use the existing workflow/orchestration layer.

---

# 12. WORKFLOW / DAG

Mission workflows should support:

```text
sequential
parallel
conditional
approval-gated
retry
fallback
```

Example:

```text
Research
    ↓
Architecture
    ↓
Approval
    ↓
 ┌─────────────┐
Frontend     Backend
 └──────┬──────┘
        ↓
       QA
        ↓
     Outcome
```

Do not invent another workflow engine if one already exists.

Extend current DAG/workflow abstractions.

---

# 13. RUNTIME ORCHESTRATION

Keep runtime execution pluggable.

Existing or target runtimes may include:

```text
native
codex
claude-code
opencode
openclaw
mcp
```

Runtime selection should eventually support:

```text
Mission requirements
        ↓
runtime capabilities
        ↓
cost
        ↓
availability
        ↓
policy
        ↓
runtime selection
```

Do not deeply couple Missions to one vendor.

---

# 14. HARNESS ENGINEERING

Treat harnesses as first-class orchestration assets.

A harness may define:

```yaml
harness:

  instructions:
  agent:
  runtime:

  context_sources:

  tools:

  guardrails:

  validations:

  approval_policy:

  output_contract:
```

Goal:

Conciencia should help create, version, test and execute harnesses.

Possible structure:

```text
harnesses/
```

or registry-backed implementation.

First inspect whether existing agents/workflows already cover this responsibility.

Do not introduce duplication.

---

# 15. RUN OBSERVABILITY

A Mission creates one or more Runs.

CLI:

```bash
conciencia run watch
```

Example:

```text
MISSION M-184

Research
✓ completed

Architecture
✓ completed

Implementation
running

QA
waiting

Runtime
Codex

Elapsed
03:41

Tokens
42,381

Cost
$0.84

Approvals
0 pending
```

Logs must be structured.

Avoid excessive noise.

---

# 16. HUMAN APPROVALS

Keep human-in-the-loop as a first-class capability.

Examples requiring approval:

* code write
* deployment
* production operations
* sending communications
* destructive filesystem changes
* database migration
* expensive external API operation
* important architecture decisions

Mission workflow:

```text
Plan
 ↓
Approval
 ↓
Execute
```

CLI:

```bash
conciencia approvals

conciencia approve <id>

conciencia reject <id>
```

---

# 17. SIGNAL INTELLIGENCE LAYER

Introduce Signal carefully.

A Signal represents a meaningful observation discovered during work.

Example:

```yaml
signal:

  id:

  type:
    architecture-risk

  source:
    repository

  confidence:
    0.91

  evidence:
    - file
    - commit
    - test

  related_mission:

  created_by:
    agent
```

Examples:

```text
technical-debt
bug
security-risk
business-opportunity
integration-opportunity
customer-request
architecture-risk
performance-issue
lead-opportunity
```

CLI:

```bash
conciencia signals list
conciencia signals inspect
conciencia signals search
```

Important:

Signals should support Missions.

Do NOT turn Conciencia into BuildBetter.

---

# 18. EVIDENCE-FIRST EXECUTION

Mission outputs should preserve provenance.

Instead of:

```text
AI Recommendation
```

prefer:

```text
Recommendation
    ↓
Evidence
    ↓
Source
```

Evidence can include:

* files
* URLs
* repository lines
* logs
* test output
* API results
* database results
* tool outputs
* commits
* documents

This will later improve trust, auditability and learning.

---

# 19. CONTEXT PACKS

Create or formalize Context Pack.

Before an agent executes:

```text
Mission
   ↓
Project Context
   ↓
Relevant Knowledge
   ↓
Signals
   ↓
Previous Decisions
   ↓
Files
   ↓
Policies
   ↓
Context Pack
   ↓
Agent Runtime
```

Context Pack should minimize unnecessary token consumption.

Do not dump the entire repository into every agent.

---

# 20. KNOWLEDGE AND MEMORY

Maintain clear separation:

Knowledge:

```text
documents
technical references
architecture
project information
external research
```

Memory:

```text
previous missions
decisions
corrections
outcomes
execution history
```

Context:

```text
temporary subset assembled for current mission
```

Never collapse these into one generic vector database abstraction.

---

# 21. WEBMCP CHALLENGE

Implement WebMCP as a real Conciencia capability.

Do NOT create a disconnected hackathon repository.

Target architecture:

```text
Web Application
      ↓
WebMCP
      ↓
Conciencia Tool Adapter
      ↓
Mission
      ↓
Agent
      ↓
Action
      ↓
Evidence
      ↓
Outcome
```

Primary demo candidate:

```text
Research technological companies or prospects
        ↓
collect structured information
        ↓
qualify opportunity
        ↓
generate evidence
        ↓
human approval
        ↓
store result
```

Integrate with LeadHunter where appropriate.

The WebMCP integration should survive after the hackathon as a reusable connector/tool.

---

# 22. LEADHUNTER INTEGRATION

LeadHunter remains a module.

Do not make LeadHunter the core of Conciencia.

Relationship:

```text
Conciencia
   │
   └── Module
        │
        └── LeadHunter
```

LeadHunter can participate in Missions such as:

```text
research potential customers
technology market research
company intelligence
solution discovery
competitive research
technical commercial discovery
```

Mission example:

```text
Identify logistics companies in Paraguay
that may need custom logistics software.
```

Possible orchestration:

```text
LeadHunter
    ↓
Research
    ↓
Qualification
    ↓
Technical opportunity
    ↓
Proposal
```

---

# 23. SOFTWARE ENGINEERING DOGFOOD

Conciencia must be useful while developing Conciencia itself.

Target principle:

> Build Conciencia with Conciencia.

Examples:

```bash
conciencia ask \
"review the current branch and create a mission to fix the highest-impact issue"
```

```bash
conciencia mission create \
--type code-review
```

```bash
conciencia agent run architect \
"review current architecture"
```

```bash
conciencia team run software-delivery
```

Use the project itself as the main test environment.

---

# 24. ECONOMIC ARCHITECTURE

Do NOT build billing yet.

Build observability first.

Define:

```text
Mission
Run
Action
Tool Call
External Cost
Compute Cost
Outcome
```

Possible internal model:

```yaml
economics:

  mission_id:

  runs:

  actions:

  token_usage:

  model_cost:

  tool_cost:

  external_api_cost:

  compute_cost:

  total_cost:

  units:

  outcomes:
```

---

# 25. CONCIENCIA UNITS

Design but do not prematurely commercialize:

```text
Conciencia Units
```

CU should abstract infrastructure consumption.

Example:

```text
Model execution
Tool call
Web research
Agent runtime
Document processing
External API
```

Internal cost remains transparent to the platform.

The end user can eventually see:

```text
Mission

Internal cost
$1.42

Conciencia Units
34

Outcome
12 validated opportunities
```

Do NOT hard-code arbitrary pricing.

---

# 26. OUTCOMES

Mission success should increasingly be measured by Outcome.

Examples:

Software:

```text
feature implemented
tests passing
bug resolved
deployment successful
```

Research:

```text
validated findings
comparison completed
technical recommendation
```

Lead research:

```text
qualified opportunities
validated companies
```

Audit:

```text
risks found
anomalies identified
recommendations generated
```

Economic observability:

```text
cost / outcome
```

---

# 27. CLI ECONOMICS

Target:

```bash
conciencia cost mission M-142
```

Possible output:

```text
MISSION ECONOMICS

Runs
14

Actions
83

Tokens
184291

LLM
$1.21

External APIs
$0.38

Compute
$0.07

TOTAL
$1.66

Conciencia Units
61

Outcomes
23

Cost / outcome
$0.072
```

Do not fabricate costs.

Only calculate from recorded usage.

---

# 28. GITHUB / OPEN SOURCE PREPARATION

Repository should eventually be renamed:

```text
conciencia
```

Product:

```text
Conciencia Platform
```

Tagline:

> The Open Control Plane for Autonomous Work.

Alternative technical description:

> Open-source mission orchestration for AI agents, coding runtimes, workflows and tools.

Avoid:

```text
conciencia-agents
```

because agents are only one component.

Avoid making the public identity overly tied to:

```text
AI platform
```

because that is generic.

---

# 29. README EVOLUTION

README should answer in under one minute:

1. What is Conciencia?
2. What problem does it solve?
3. What is a Mission?
4. Why isn't it another agent framework?
5. What can I run?
6. How do I install it?
7. How do I run my first Mission?
8. Which runtimes does it support?
9. How does governance work?
10. How can I contribute?

Add a visual:

```text
Intent
 ↓
Mission
 ↓
Agents
 ↓
Workflow
 ↓
Runtime
 ↓
Tools
 ↓
Approval
 ↓
Outcome
```

---

# 30. ZERO-TO-MISSION TEST

Critical product KPI:

A new developer should be able to:

```bash
git clone ...
docker compose up
conciencia init
conciencia mission create
conciencia mission run
conciencia run watch
```

without assistance.

Target:

< 10 minutes.

Provide a simulation mode when API keys are unavailable.

Do not make real paid API credentials mandatory for the initial demo.

---

# 31. SOFTWARE DEMO

Implement or formalize:

```bash
conciencia demo software
```

Mission:

```text
Analyze this repository and propose one useful improvement.
```

Workflow:

```text
Repository Analysis
      ↓
Research
      ↓
Architecture Review
      ↓
Proposal
      ↓
Human Approval
```

Initially read-only.

This should work with arbitrary software repositories.

---

# 32. TESTING STRATEGY

Every new major capability should have tests.

Prioritize:

* mission lifecycle
* CLI commands
* workflow transitions
* approval gates
* runtime adapters
* context generation
* agent registry
* tool registry
* project detection
* signal creation
* economics calculations

Do not create superficial tests purely for coverage.

Test domain behavior.

---

# 33. SECURITY

Never expose:

* API keys
* credentials
* secrets
* private repository contents
* environment variables

Use:

```text
.env
secret store
runtime configuration
```

Commands should clearly distinguish:

```text
read-only
write
destructive
external
production
```

Require approval for dangerous operations.

---

# 34. FAILURE HANDLING

Mission executions must support:

```text
retry
timeout
pause
resume
cancel
fallback
partial failure
```

Do not treat every runtime failure as full mission failure.

Record failure evidence.

---

# 35. IMPLEMENTATION PHASES

Execute sequentially.

Do not attempt all features at once.

---

## PHASE A — Architecture Audit

Deliver:

```text
current architecture
capability matrix
technical debt
duplication risks
proposed changes
```

No large refactor yet.

---

## PHASE B — Identity & Domain Alignment

Confirm:

```text
Mission is central
Agent != Mission
Workflow != Mission
Run != Mission
Project != Mission
```

Rename only where safe.

Prepare repository naming migration.

---

## PHASE C — CLI Foundation

Complete:

```text
conciencia init
conciencia status
conciencia doctor

conciencia mission *
conciencia agent *
conciencia workflow *
conciencia run *
```

Definition of Done:

A mission can be created, executed and inspected entirely from CLI.

---

## PHASE D — Project Awareness

Implement:

```text
project detection
git context
stack detection
project metadata
.conciencia configuration
```

Definition of Done:

Conciencia understands the repository it is operating inside.

---

## PHASE E — Mission Planning

Implement:

```text
conciencia ask
intent → mission
mission proposal
agent selection
runtime suggestion
workflow suggestion
cost estimate
approval
```

Definition of Done:

Natural language can safely produce a structured Mission.

---

## PHASE F — Agent / Team Orchestration

Improve:

```text
agent registry
teams
runtime routing
workflow integration
parallel execution
```

Definition of Done:

A Mission can coordinate multiple specialized agents.

---

## PHASE G — Harness Layer

Formalize:

```text
agent instructions
context
tools
validation
guardrails
runtime
output contracts
```

Definition of Done:

Harnesses can be versioned and reused across Missions.

---

## PHASE H — Observability

Implement:

```text
run watch
structured logs
cost
runtime
tokens
actions
tool calls
failure state
```

Definition of Done:

An operator can understand exactly what a Mission is doing.

---

## PHASE I — Signals + Evidence

Implement minimally.

Definition of Done:

Mission findings can generate traceable Signals with Evidence.

---

## PHASE J — Context Packs

Implement efficient contextual retrieval.

Definition of Done:

Agents receive relevant context without loading unnecessary project data.

---

## PHASE K — WebMCP

Integrate WebMCP as a Conciencia tool/adapter.

Definition of Done:

A Mission can interact with a WebMCP-enabled web application and preserve evidence.

---

## PHASE L — Economics

Record:

```text
runs
actions
models
tokens
tools
external cost
outcomes
```

Definition of Done:

Mission economics can be inspected without implementing billing.

---

# 36. DO NOT BUILD YET

Do NOT prioritize:

* marketplace
* billing system
* complex enterprise tenancy
* huge agent catalog
* generic CRM
* generic ERP
* mobile app
* massive UI redesign
* autonomous company simulation
* dozens of integrations
* arbitrary business automation
* another chatbot

First prove Mission Orchestration.

---

# 37. PRIMARY DOGFOOD USE CASES

Optimize initially for these three.

### A. Technological Research

Example:

```text
Research the best architecture for implementing WebMCP.
```

---

### B. Software Development

Example:

```text
Analyze this repository, propose an implementation plan,
execute after approval, then run tests.
```

---

### C. Agent / Harness Engineering

Example:

```text
Design a reusable technical research agent,
create its harness,
test it,
measure its execution,
and register it.
```

These should be excellent before expanding elsewhere.

---

# 38. SECONDARY USE CASE

Technical Commercial Discovery.

Example:

```text
Research logistics companies,
identify likely software problems,
find technological opportunities,
and prepare a technical solution hypothesis.
```

This is allowed because it connects technological capability to real market demand.

Conciencia should NOT become a generic sales CRM.

---

# 39. SUCCESS CRITERIA FOR THIS DEVELOPMENT STAGE

The stage is successful when the repository owner genuinely prefers using Conciencia for a meaningful portion of daily technological work.

Target behavior:

```bash
conciencia ask ...
conciencia mission create ...
conciencia mission run ...
conciencia run watch ...
conciencia agent run ...
conciencia cost ...
```

Instead of manually coordinating each AI tool independently.

---

# 40. NORTH STAR

The key metric is not:

```text
number of agents
```

or:

```text
number of features
```

It is:

> **Useful technological Missions successfully completed through Conciencia.**

Supporting metrics:

```text
Mission success rate
Time to Mission
Cost per Mission
Human interventions
Agent failures
Retries
Outcome quality
Context reuse
External user installations
```

---

# 41. FINAL PRODUCT MODEL

The long-term architecture should converge toward:

```text
                     CONCIENCIA

                MISSION CONTROL PLANE

                        │
          ┌─────────────┼─────────────┐
          │             │             │

       CONTEXT        AGENTS       WORKFLOWS

          │             │             │
          └─────────────┼─────────────┘
                        │

                     HARNESS

                        │

              RUNTIME ORCHESTRATION

                        │

       ┌────────────────┼────────────────┐

     Codex         Claude Code       OpenClaw
     MCP            OpenCode          Native

       └────────────────┼────────────────┘
                        │

                      TOOLS

                        │

                   EXECUTION

                        │

                    EVIDENCE

                        │

                     SIGNALS

                        │

                    OUTCOME

                        │

                   ECONOMICS
```

---

# 42. ENGINEERING RULE

For every proposed implementation:

Ask:

```text
Does this improve the ability to create,
orchestrate,
execute,
govern,
observe,
or learn from Missions?
```

If NO:

do not prioritize it.

---

# 43. INITIAL EXECUTION INSTRUCTION

Start now.

Do NOT immediately modify major architecture.

First produce:

```text
1. Repository Audit
2. Existing Capability Matrix
3. Mission Orchestration Gap Analysis
4. CLI Gap Analysis
5. Architecture Risks
6. Reuse Opportunities
7. Proposed Phase B implementation
8. Files expected to change
9. Migration risks
10. Test plan
```

Then implement **only the next logical phase**.

After each phase:

```text
run tests
run type checks
run lint
verify Docker
verify CLI
verify migrations
document changes
```

Never claim success without executing available validation commands.

---

# FINAL PRINCIPLE

Conciencia should become:

> **the place where technological work is transformed from intent into governed, observable and reusable Missions.**

Not another AI chat.

Not another agent toy.

Not another coding model.

The orchestration layer above them.

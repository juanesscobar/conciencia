# CONCIENCIA PLATFORM
## Master Product + UX/UI + Control Plane Implementation Specification

VERSION: 2.0
STATUS: ACTIVE
PRODUCT: Conciencia Platform
FORMER NAME: Mission Control

---

# 0. CRITICAL EXECUTION RULE

DO NOT IMPLEMENT THIS ENTIRE SPECIFICATION IN ONE PASS.

This document defines the target product architecture, UX/UI direction and implementation roadmap.

Before modifying code:

1. Inspect the repository.
2. Identify the existing architecture.
3. Identify what already exists.
4. Identify what is functional.
5. Identify which requirements are UX-only.
6. Identify which requirements require backend changes.
7. Identify which requirements already exist under different names.
8. Produce an implementation plan.
9. Implement only the current phase.
10. Run the existing build/tests.
11. Verify the Definition of Done.
12. Only then continue to the next phase.

Never replace working functionality simply because the target architecture describes a different abstraction.

Prefer evolution over rewrite.

---

# 1. TARGET REPOSITORY

The primary target for this specification is:

mission-control/

The UX/UI application is expected to live conceptually under:

mission-control/frontend/

Do NOT modify the Conciencia marketing/landing website as the primary implementation target unless explicitly required.

If multiple repositories or applications exist:

1. Identify them.
2. Determine which one contains the actual Mission Control application.
3. Confirm the architecture before editing.
4. Keep the marketing website and application concerns separated.

Expected application stack may include:

- React
- TypeScript
- Vite
- Tailwind CSS
- existing component system
- existing API/service layer

Do NOT assume the exact stack.

Inspect the repository first.

---

# 2. ROLE

Act as a combination of:

- Senior Product Designer
- UX Architect
- Staff Frontend Engineer
- AI Product Architect
- Control Plane Architect
- Agent Orchestration Specialist
- Harness Engineering Specialist

with experience in:

- AI-native SaaS
- Agent orchestration
- autonomous systems
- AI Control Planes
- human-in-the-loop systems
- developer platforms
- observability
- governance
- context and memory systems
- multi-agent systems
- B2B SaaS UX

The goal is to evolve Conciencia into a coherent AI-native platform without unnecessary complexity.

---

# 3. PRODUCT VISION

Conciencia Platform should become:

> AI Control Plane for Autonomous Work

Conciencia connects, coordinates, governs, observes and preserves the context of an ecosystem of:

- agents
- models
- tools
- applications
- workflows
- knowledge
- memory
- humans

The platform should allow users to:

- define objectives
- create Missions
- coordinate agents
- execute workflows
- select models
- use tools
- supervise execution
- approve sensitive actions
- inspect execution traces
- govern agents/models/tools
- preserve project memory
- create Context Packs
- transfer context between AI systems
- measure cost
- measure outcomes
- interact with the Control Plane using natural language

---

# 4. WHAT CONCIENCIA IS NOT

Conciencia must NOT become:

- another ChatGPT
- another chatbot
- another IDE
- another Zapier
- another Jira
- another generic AI dashboard
- another project management application
- another agent marketplace

The product is not the chatbot.

The product is the Control Plane.

---

# 5. CORE PRODUCT MODEL

The central UX model is:

INTENT
↓
MISSION
↓
WORKFLOW
↓
AGENTS
↓
TOOLS / MODELS
↓
EXECUTION
↓
GOVERNANCE
↓
RESULT
↓
MEMORY / CONTEXT

And the persistent loop is:

CONTEXT
↓
MISSION
↓
EXECUTION
↓
RESULT
↓
DECISION
↓
MEMORY
↓
NEXT MISSION

---

# 6. HIGH-LEVEL ARCHITECTURE

The target conceptual architecture is:

                         CONCIENCIA PLATFORM
                                  |
              +-------------------+-------------------+
              |                                       |
           OPERATE                                   BUILD
              |                                       |
       Mission Control                             Agents
       Missions                                    Workflows
       Tasks                                       Tools
       Approvals                                   Models
       Results                                     Knowledge
       Reports                                     Context & Memory
                                                   Templates
              |                                       |
              +-------------------+-------------------+
                                  |
                             CONTROL PLANE
                                  |
          Identity · Policies · Governance · Audit
          Context · Memory · Observability · Cost
                                  |
                         EXTERNAL ECOSYSTEM
                                  |
       Claude · ChatGPT · Gemini · Qwen · OpenClaw
                                  |
             MCP · APIs · Apps · Repositories

The exact implementation must be derived from the existing repository.

---

# 7. CURRENT REPOSITORY AUDIT

Before implementation, inspect:

- repository structure
- package manager
- framework
- routing
- layouts
- state management
- components
- design system
- API layer
- backend services
- data models
- authentication
- existing integrations
- existing LeadHunter implementation
- existing Mission Control implementation
- tests
- build scripts
- environment configuration

Create an internal architecture map:

CURRENT:

Route
→ Component
→ State
→ Service
→ API
→ Data

Then create:

TARGET:

Route
→ UX Role
→ Component
→ Service
→ Control Plane
→ Data

Do not guess.

---

# 8. PRESERVE EXISTING FUNCTIONALITY

The existing application contains functionality that may already solve parts of the target architecture.

Do not rebuild existing capabilities merely to match new terminology.

Before replacing a component or feature:

1. Determine what it currently does.
2. Determine who uses it.
3. Determine its backend dependencies.
4. Determine whether it should be renamed, wrapped or evolved.
5. Preserve working behavior whenever possible.

The target architecture must be implemented as an evolution of the existing system.

---

# 9. PRODUCT LANGUAGE

Use the following conceptual vocabulary:

Mission
Agent
Workflow
Task
Tool
Model
Knowledge
Memory
Context
Context Pack
Approval
Policy
Execution
Trace
Result
Governance
Audit

However, terminology must not automatically imply a backend migration.

UX terminology and backend entities may temporarily differ.

---

# 10. MISSION VS PROJECT

IMPORTANT:

"Mission" is initially a UX/domain abstraction.

Do NOT automatically rename, delete or migrate the existing Project entity.

First inspect the existing backend.

A possible conceptual model is:

Project
├── Missions
│   ├── Tasks
│   ├── Workflows
│   ├── Agents
│   └── Results
│
├── Knowledge
├── Memory
└── Decisions

Possible interpretation:

Project = persistent workspace/container

Mission = autonomous objective/execution

If this distinction fits the existing architecture, preserve both.

Only modify the backend data model when there is a concrete architectural reason.

---

# 11. NAVIGATION

Target navigation:

CONCIENCIA

OPERATE
- Mission Control
- Missions
- Tasks
- Approvals
- Results
- Reports

BUILD
- Agents
- Workflows
- Tools
- Models
- Knowledge
- Context & Memory
- Templates

CONTROL
- Governance
- Policies
- Activity
- Traces
- Costs
- Audit

SYSTEM
- Integrations
- API
- Settings

GLOBAL
- Command Bar
- Ask Conciencia

Do not implement empty functionality solely to populate navigation.

Use appropriate placeholders when backend functionality does not exist.

---

# 12. MISSION CONTROL

The main dashboard should evolve into:

> Mission Control

It should answer within approximately five seconds:

1. Is the system operational?
2. What Missions are active?
3. Which agents are working?
4. What requires human intervention?
5. What failed?
6. What is the current cost?
7. What results were produced?

Information hierarchy:

LEVEL 1 — WHAT MATTERS NOW

- system status
- active Missions
- approvals
- failures
- outcomes

LEVEL 2 — WHAT IS HAPPENING

- agents
- workflows
- tasks
- progress
- activity

LEVEL 3 — TECHNICAL DETAIL

- traces
- logs
- tokens
- latency
- models
- API details

Do not give all three levels equal visual weight.

---

# 13. MISSION CONTROL EXAMPLE

Any numeric example in this specification is MOCK data.

Example:

System Operational

12 Agents [MOCK]
34 Tasks [MOCK]
3 Missions Running [MOCK]
2 Approvals Required [MOCK]
1 Failed Task [MOCK]
$18.42 Today's Cost [MOCK]

Never hardcode these values as production data.

---

# 14. MISSION

Mission should represent an autonomous objective.

Example:

Generate 100 qualified B2B leads in Brazil.

Mission detail should communicate:

OBJECTIVE

STATUS

PROGRESS

AGENTS

CURRENT STAGE

COST

DURATION

RESULT

APPROVALS

A Mission may contain:

- workflows
- tasks
- agents
- tools
- models
- approvals
- results
- context
- memory
- decisions

---

# 15. AGENT REGISTRY

Agents should evolve from a simple list into an Agent Registry.

Each Agent may expose:

Identity
Role
Capabilities
Models
Tools
Permissions
Memory
Current Mission
Current Task
Performance
Cost
Status

Example:

LeadHunter

ROLE
Lead Discovery

CAPABILITIES
Research
Enrichment
Verification

TOOLS
Google
Apollo
CRM

STATUS
Working

SUCCESS RATE
94.7% [MOCK]

AVG COST / TASK
$0.032 [MOCK]

All numeric examples are MOCK.

---

# 16. EXTERNAL AGENTS

Conciencia should eventually govern external agents.

Examples:

- Claude Code
- OpenClaw
- OpenCode
- Gemini-based agents
- Qwen-based agents
- custom agents
- MCP-connected agents

Conciencia does not need to control private internal reasoning.

It should control:

- identity
- permissions
- capabilities
- tools
- context
- Mission assignment
- policies
- execution
- observability
- cost
- audit

Prepare an abstraction:

Agent Adapter

Do not couple the architecture to one AI provider.

---

# 17. MODEL REGISTRY

Create a Model Registry abstraction.

Examples:

- Claude
- GPT
- Gemini
- Qwen
- local models
- custom models

Each model may expose:

- provider
- capabilities
- context window
- cost
- latency
- availability
- policy

Prepare for model routing.

Example:

Complex reasoning
→ approved reasoning model

Cheap classification
→ low-cost model

Sensitive data
→ approved local model

Production coding
→ approved coding model

Do not implement complex routing unless the existing backend supports it.

---

# 18. TOOL / APPLICATION REGISTRY

Tools should represent:

- MCP servers
- APIs
- applications
- repositories
- databases
- external services

Examples:

- GitHub
- Slack
- Google Drive
- CRM
- PostgreSQL
- AWS
- MCP servers

Each integration should eventually expose:

- permissions
- scopes
- credentials
- policies
- usage
- audit

---

# 19. WORKFLOWS

Workflows represent orchestration.

Do not create a Zapier clone.

Nodes may represent:

- Agent
- Tool
- Decision
- Condition
- Human Gate
- Model
- Data Source
- Output

Example:

MISSION
↓
Research Agent
↓
Enrichment
↓
Verification Agent
↓
Human Approval
↓
CRM Agent

Each node should expose, where applicable:

- status
- execution time
- cost
- input
- output
- errors
- responsible agent/tool

---

# 20. TASKS

Task = Execution Unit.

Task detail should expose:

- Mission
- Agent
- Workflow
- Status
- Progress
- Tools Used
- Model Used
- Cost
- Duration
- Current Action
- Next Action
- Execution Trace

---

# 21. APPROVALS

Create an explicit Human-in-the-Loop experience.

Example:

NEEDS YOUR APPROVAL

LeadHunter wants to send 48 emails.

MISSION
Brazil Lead Generation

AGENT
Outreach Agent

RECIPIENTS
48 [MOCK]

ESTIMATED COST
$2.40 [MOCK]

Actions:

[View Details]
[Reject]
[Approve]

Sensitive actions should follow:

Action
↓
Policy Engine
↓
Approval Required?
↓
Human Decision
↓
Execution
↓
Audit

---

# 22. GOVERNANCE

Governance is a first-class Control Plane capability.

Conceptually:

Identity
Permissions
Policies
Agent Policies
Model Policies
Tool Policies
Data Policies
Cost Policies
Approval Policies
Security
Audit

Example:

AGENT POLICY

LeadHunter

Allowed:
✓ Search Web
✓ CRM Read
✓ Database Read

Requires Approval:
⚠ Send Email
⚠ Modify CRM

Forbidden:
✕ Delete Customer
✕ Production Deployment

Policies should be enforceable by the execution layer, not merely visual UI decorations.

---

# 23. ACTIVITY AND EXECUTION TRACE

Create an observable execution history.

Example:

16:42:08 Agent started task
16:42:10 Tool → Search
16:42:11 Results retrieved
16:42:15 Tool → CRM
16:42:18 Data received
16:42:20 Verification failed
16:42:21 Fallback activated
16:42:26 Verification successful
16:42:28 Result stored

Show:

- goal
- input
- action
- tool
- result
- next action
- policy evaluation
- error
- outcome

Do NOT expose private chain-of-thought.

Use:

Execution Trace
Decision Trace
Action Trace

instead of exposing hidden reasoning.

---

# 24. KNOWLEDGE VS MEMORY VS CONTEXT

Keep these concepts separate.

## KNOWLEDGE

External information:

- documents
- databases
- web sources
- repositories
- datasets
- company knowledge

## MEMORY

Persistent information created or learned during work:

- decisions
- project state
- task history
- development history
- agent memory
- experiences

## CONTEXT

Information selected for a specific execution:

- current Mission
- current Task
- relevant Memory
- relevant Knowledge
- constraints
- relevant files
- current state

Model:

KNOWLEDGE
+
MEMORY
+
CURRENT STATE
↓
CONTEXT
↓
AGENT EXECUTION

---

# 25. PROJECT MEMORY

Project Memory should preserve persistent project knowledge.

Example:

PROJECT MEMORY

Architecture
Control Plane architecture

UX
Mission-first model

Technology
React
TypeScript
FastAPI
PostgreSQL

Business
B2B AI orchestration

Current Priorities
Context portability
Agent governance
Workflow orchestration

Do not fabricate project information.

Only display information actually stored or explicitly marked as MOCK.

---

# 26. DECISION MEMORY

Architecture and product decisions are first-class objects.

Example:

DECISION #042

Date:
2026-08-18

Decision:
Use Mission as the primary autonomous objective abstraction.

Reason:
Better represents autonomous execution.

Rejected:
Project
Job
Campaign

Impact:
UX
Data model
API
Workflow
Documentation

Decisions should be linkable to:

- Projects
- Missions
- Tasks
- Agents
- Files
- commits
- architecture
- Context Packs

---

# 27. DEVELOPMENT MEMORY

Conciencia should eventually preserve development context across AI coding environments.

Examples:

- architecture decisions
- implementation history
- unresolved issues
- current task
- relevant files
- recent changes
- known constraints
- rejected approaches
- open questions

The goal is:

> Project intelligence should not be trapped inside a single AI conversation.

---

# 28. CONTEXT PACK

Create:

> Context Pack

A Context Pack is a structured representation of relevant project context.

The prompt is NOT the canonical memory.

The canonical context should contain structured information such as:

- Project
- Mission
- Current Task
- Architecture
- Relevant Decisions
- Constraints
- Known Problems
- Open Questions
- Relevant Files
- Recent Activity
- Expected Output

Example:

CONCIENCIA CONTEXT PACK

PROJECT
Conciencia Platform

MISSION
Redesign Agent Governance UX

CURRENT STATE
...

ARCHITECTURE
...

DECISIONS
DEC-041
DEC-042
DEC-044

CONSTRAINTS
...

CURRENT TASK
...

RELEVANT FILES
...

OPEN QUESTIONS
...

Any example content must be clearly identified as MOCK unless it reflects real repository information.

---

# 29. CONTEXT TRANSFER

Provide a conceptual UX for:

Transfer Context

Example:

FROM
Claude Code

TO
Qwen Code

Include:

✓ Project Memory
✓ Architecture
✓ Decisions
✓ Current Task
✓ Repository Context
✓ Relevant Files

Optional:

○ Recent Conversation
○ Full Conversation History

[Generate Context Pack]

The actual implementation must use real available context.

Do not invent files, decisions or architecture.

---

# 30. CONTEXT ADAPTERS

The same canonical Context should be representable as:

- LLM Context
- Coding Agent Context
- Human Summary
- JSON Context
- System Prompt
- Task Prompt
- Repository Instructions

The canonical source remains:

Canonical Context

Different agents receive different representations.

Do not duplicate the underlying memory.

---

# 31. ASK CONCIENCIA

Conciencia should include an AI Assistant layer.

However:

IMPORTANT:

The Assistant is NOT a separate product.

It is NOT another chatbot.

It is NOT a second agent platform.

It is NOT a second memory system.

It is:

> Natural Language Interface → Control Plane

---

# 32. COMMAND BAR

Create a global Command Bar:

⌘ K

Possible commands:

- Create Mission
- Run Workflow
- Pause Agent
- Resume Agent
- Retry Task
- Approve Action
- Search Activity
- Inspect Failed Tasks
- Show Costs
- Transfer Context
- Create Context Pack
- Search Memory
- Ask Conciencia

The Command Bar should combine:

- navigation
- search
- commands
- actions

Do not create duplicate action systems.

---

# 33. ASK CONCIENCIA UI

Prefer a contextual side panel rather than a full-screen chat.

Example:

CONCIENCIA

User:
Why did LeadHunter fail?

Conciencia:

3 failures detected in the last 20 minutes. [MOCK]

The problem appears to be in Company Verification.

API returned a rate-limit response.

Fallback strategy activated.

Actions:

[View Trace]
[Retry]
[Change Model]

Input:

Ask about your system...

The exact data must come from the Control Plane.

---

# 34. ASSISTANT CAPABILITIES

The Assistant has three primary capabilities.

## OBSERVE

Examples:

- What is running?
- Which agents are active?
- What failed today?
- How much did we spend?
- Which Missions need approval?

## EXPLAIN

Examples:

- Why did this fail?
- Why was this model selected?
- What did this agent do?
- Which tools were used?
- Why does this task require approval?

## ACT

Examples:

- Retry failed tasks.
- Pause LeadHunter.
- Run this workflow.
- Approve this action.
- Create a Context Pack.
- Transfer this context to Qwen Code.

---

# 35. ASSISTANT MUST USE THE CONTROL PLANE

Architecture:

UI
+
Ask Conciencia
+
Command Bar
↓
CONTROL PLANE
↓
Agents
Workflows
Memory
Policies
Execution
Audit

The Assistant must use the same:

- APIs
- services
- permissions
- policies
- memory
- execution engine
- audit system

as the normal UI.

---

# 36. NO ASSISTANT-SPECIFIC ARCHITECTURE

Do NOT create:

Assistant Agents
Assistant Workflows
Assistant Memory
Assistant Tools

The Assistant must operate on the existing Control Plane.

Architecture:

Natural Language
↓
Intent
↓
Control Plane
↓
Policy
↓
Execution
↓
Audit

The Assistant is an interface.

It is not a second platform.

---

# 37. ASSISTANT ACTION SAFETY

The Assistant must not silently execute sensitive actions.

Example:

User:

Delete all duplicate CRM records.

Conciencia:

This action will modify 438 records. [MOCK]

Policy:
CRM-02 requires approval.

[Review Changes]

[Approve]

Flow:

User
↓
Assistant
↓
Intent
↓
Policy Engine
↓
Approval
↓
Execution
↓
Audit

Read-only queries can be executed directly when permitted.

Destructive or high-impact actions should respect policy and approval requirements.

---

# 38. CONTEXT-AWARE ASSISTANT

The Assistant should inherit UI context.

If the user is viewing:

Mission:
Brazil Lead Generation

and asks:

Why is it slow?

The Assistant should interpret the question in relation to that Mission.

If the user is viewing:

Agent:
LeadHunter

and asks:

What happened?

The Assistant should interpret the question in relation to that Agent.

Avoid unnecessary clarification questions when context is obvious.

---

# 39. ASSISTANT + MEMORY

The Assistant should eventually query:

- Project Memory
- Decision Memory
- Development Memory
- Context Packs
- Task History
- Execution History
- Knowledge
- Current State

Example:

User:
Why did we choose Mission instead of Project?

The Assistant should retrieve the relevant Decision Memory.

Example:

User:
Prepare the current development context for another coding agent.

The Assistant should create a Context Pack from real stored context.

---

# 40. CLIENT MODE VS OPERATOR MODE

Prepare two UX levels.

## CLIENT MODE

Show:

- Mission Control
- Missions
- Results
- Approvals
- Reports
- Costs
- Ask Conciencia

The client should think:

> What did Conciencia accomplish?

## OPERATOR MODE

Show:

- Agents
- Models
- Tools
- Workflows
- Memory
- Context
- Policies
- Traces
- Logs
- Infrastructure
- Costs
- Governance
- Ask Conciencia

The operator should be able to inspect the system deeply.

Do not necessarily implement both modes immediately.

---

# 41. REPORTS

Reports should prioritize outcomes.

Example:

MISSION REPORT

Brazil Lead Generation

RESULT
100 qualified companies [MOCK]

AGENTS
14 [MOCK]

TASKS
2,431 [MOCK]

HUMAN INTERVENTIONS
3 [MOCK]

TIME SAVED
31 hours [MOCK]

COST
$18.42 [MOCK]

ESTIMATED HUMAN COST
$620 [MOCK]

ESTIMATED ROI
33.7x [MOCK]

Information hierarchy:

Outcome
↓
Impact
↓
Cost
↓
Execution Details

Never present MOCK values as production metrics.

---

# 42. LEADHUNTER — EXISTING IMPLEMENTATION

LeadHunter is NOT a hypothetical future demo.

The existing Mission Control application contains real LeadHunter functionality.

Before modifying LeadHunter:

1. Inspect its frontend.
2. Inspect its backend.
3. Inspect APIs.
4. Inspect data models.
5. Inspect enrichment behavior.
6. Inspect scheduling.
7. Inspect execution lifecycle.
8. Identify existing UI.
9. Identify existing lead data.
10. Identify dependencies.

Do NOT rebuild LeadHunter from scratch.

The target conceptual representation is:

LeadHunter
↓
Mission Template
↓
Workflow
↓
Agents
↓
Tools / Models
↓
Execution
↓
Results
↓
Memory / Context

LeadHunter should become an early real-world demonstration of the new architecture.

---

# 43. LEADHUNTER IMPLEMENTATION RULE

Do not force LeadHunter into the new Mission architecture if doing so breaks existing functionality.

Prefer an incremental migration:

Existing LeadHunter
↓
Mission-compatible wrapper
↓
New UX
↓
New execution abstractions
↓
Future native Mission Template

Preserve:

- existing lead data
- enrichment
- scheduling
- existing API contracts
- working workflows

unless there is a clear reason to migrate them.

---

# 44. DESIGN SYSTEM

Consolidate existing design tokens.

Define/reuse:

- colors
- typography
- spacing
- borders
- radius
- shadows
- status colors
- icons
- tables
- cards
- panels
- modals
- command bar
- timeline
- traces
- workflow nodes
- agent cards
- mission cards
- approval cards

Preferred visual language:

- dark interface
- subtle borders
- technical density
- restrained accent colors
- clear hierarchy
- progressive disclosure

Avoid:

- excessive gradients
- excessive glow
- excessive animation
- oversized cards
- excessive rounding
- decorative UI without function

---

# 45. UI STATES

Every new or modified screen MUST define:

- loading state
- empty state
- error state
- success/active state
- permission-restricted state where applicable

Do not design only the happy path.

Example:

Loading:
Skeleton or contextual loading indicator.

Empty:
Explain what is missing and provide a useful next action.

Error:
Explain what failed and provide recovery options.

Permission restricted:
Explain why access is restricted.

---

# 46. ACCESSIBILITY

Every implementation should support:

- keyboard navigation
- visible focus states
- semantic HTML
- accessible labels
- sufficient contrast
- reduced motion where appropriate
- meaningful button labels
- logical heading hierarchy

Do not use color as the only indicator of status.

---

# 47. RESPONSIVE DESIGN

Desktop is the primary target for Mission Control.

However, layouts should remain usable across:

- desktop
- laptop
- tablet
- mobile where applicable

Do not simply shrink desktop layouts.

Prioritize:

Mobile:
- status
- Missions
- approvals
- critical actions

Desktop:
- full operational dashboard
- traces
- workflows
- governance
- technical inspection

---

# 48. UX INFORMATION HIERARCHY

Every screen should answer:

LEVEL 1
What matters now?

LEVEL 2
What is happening?

LEVEL 3
What are the technical details?

This hierarchy must guide:

- spacing
- typography
- visual weight
- card placement
- interactions
- progressive disclosure

---

# 49. DATA MODEL CONCEPT

Prepare conceptual interfaces/types for:

Mission
Agent
AgentCapability
AgentAdapter
Workflow
WorkflowNode
Task
Tool
Integration
Model
KnowledgeSource
Memory
Decision
Context
ContextPack
ContextTransfer
Approval
Policy
Execution
Trace
AuditEvent
CostRecord
Result

Do not implement every entity if the current application does not require it.

Use incremental evolution.

---

# 50. IMPLEMENTATION PHASES

## PHASE 1 — FOUNDATION

Goals:

- audit repository
- document architecture
- preserve existing functionality
- consolidate design tokens
- establish navigation
- evolve Dashboard → Mission Control

Definition of Done:

[ ] Repository audited
[ ] Existing routes documented
[ ] Existing components documented
[ ] Existing APIs documented
[ ] LeadHunter identified
[ ] Navigation implemented/refactored
[ ] Mission Control implemented
[ ] Existing functionality preserved
[ ] Loading states implemented
[ ] Empty states implemented
[ ] Error states implemented
[ ] Responsive behavior reviewed
[ ] Accessibility reviewed
[ ] Build passes
[ ] Existing tests pass
[ ] No unnecessary dependencies introduced

Do not continue until the applicable criteria are satisfied.

---

# 51. PHASE 2 — CORE EXECUTION UX

Implement/evolve:

- Missions
- Agents
- Tasks
- Workflows
- Approvals

Definition of Done:

[ ] Mission UX exists
[ ] Agent Registry exists
[ ] Task detail exists
[ ] Workflow visualization exists
[ ] Approval UX exists
[ ] Existing LeadHunter functionality remains operational
[ ] Core states exist
[ ] No duplicated business logic
[ ] Build passes
[ ] Existing tests pass

---

# 52. PHASE 3 — CONTROL PLANE UX

Implement/evolve:

- Governance
- Policies
- Activity
- Traces
- Costs
- Audit

Definition of Done:

[ ] Policies can be visualized
[ ] Governance hierarchy is understandable
[ ] Execution traces are inspectable
[ ] Activity timeline exists
[ ] Cost data has clear source
[ ] Audit events are distinguishable
[ ] Sensitive actions follow approval patterns
[ ] No private chain-of-thought exposed

---

# 53. PHASE 4 — CONTEXT FABRIC

Implement/evolve:

- Knowledge
- Memory
- Project Memory
- Decision Memory
- Development Memory
- Context
- Context Packs
- Context Transfer

Definition of Done:

[ ] Knowledge and Memory are clearly separated
[ ] Context is defined separately from Memory
[ ] Decisions can be represented
[ ] Context Packs have a defined structure
[ ] Context transfer UX exists
[ ] No duplicated memory systems are created
[ ] Real repository/project data can eventually populate the model
[ ] Mock data is clearly marked

---

# 54. PHASE 5 — EXTERNAL ECOSYSTEM

Prepare abstractions for:

- Agent Adapters
- Model Registry
- Tool Registry
- MCP
- APIs
- Applications
- Repositories
- external AI agents

Definition of Done:

[ ] Provider-neutral abstractions exist
[ ] External agent concept exists
[ ] Model Registry concept exists
[ ] Tool Registry concept exists
[ ] Permissions are considered
[ ] Policy boundaries are clear
[ ] Existing providers are not hardcoded into UI architecture

Do not implement integrations that are not actually available.

---

# 55. PHASE 6 — COMMAND CENTER

Implement:

- Command Bar
- Ask Conciencia
- contextual queries
- read-only observation
- explanation
- structured actions
- approval flows

Definition of Done:

[ ] Command Bar exists
[ ] Ask Conciencia exists
[ ] Assistant uses Control Plane services
[ ] Assistant has no independent memory
[ ] Assistant has no independent agent system
[ ] Assistant has no independent workflow system
[ ] Context awareness works
[ ] Read-only queries work where supported
[ ] Sensitive actions respect policies
[ ] Approval flows work
[ ] Audit records are created where supported

---

# 56. PHASE 7 — CLIENT EXPERIENCE

Create a simplified Client Mode.

Prioritize:

- outcomes
- Missions
- approvals
- reports
- costs
- status

Definition of Done:

[ ] Technical complexity is reduced
[ ] Business outcomes are emphasized
[ ] Operator-only details are hidden by default
[ ] Client can understand Mission status quickly
[ ] Client can approve relevant actions
[ ] Client can inspect results

---

# 57. PHASE 8 — OPERATOR EXPERIENCE

Create advanced Operator Mode.

Prioritize:

- agents
- workflows
- tools
- models
- memory
- context
- policies
- traces
- logs
- governance
- costs

Definition of Done:

[ ] Operator can inspect executions
[ ] Operator can inspect policies
[ ] Operator can inspect agents
[ ] Operator can inspect workflows
[ ] Operator can inspect context
[ ] Operator can inspect costs
[ ] Operator can investigate failures

---

# 58. ENGINEERING CONSTRAINTS

DO NOT:

- rewrite the entire application
- remove working functionality without replacement
- create duplicate architectures
- create Assistant-specific backend systems
- create Assistant-specific memory
- create Assistant-specific workflows
- create provider-specific UI architecture
- hardcode business logic into presentation components
- create fake integrations
- claim nonexistent backend functionality
- expose private chain-of-thought
- introduce unnecessary dependencies
- migrate backend entities without auditing them
- replace LeadHunter functionality without understanding it

Prefer:

UI
↓
Service
↓
API
↓
Control Plane
↓
Adapter
↓
External System

---

# 59. MOCK DATA RULE

All examples in this specification containing:

- dollar amounts
- percentages
- counts
- ROI
- task numbers
- agent numbers
- lead numbers
- performance metrics

are MOCK unless explicitly retrieved from the actual application/backend.

Never hardcode them into production UI.

If mock data is needed during implementation:

Use clearly identifiable mock fixtures/services.

Example:

mockMissionData
mockAgentData
mockExecutionData

Do not make mock data indistinguishable from production architecture.

---

# 60. NO FAKE FUNCTIONALITY

If a feature is UI-only because the backend does not yet support it:

Clearly separate:

UI prototype
from
Production functionality.

Use service interfaces where appropriate.

Example:

interface ContextTransferService

rather than embedding fake transfer logic directly into the component.

---

# 61. NO DUPLICATED SOURCE OF TRUTH

Conciencia must maintain one conceptual source of truth for:

- Missions
- Agents
- Workflows
- Policies
- Memory
- Context
- Execution
- Audit

The Command Bar, Assistant and normal UI must consume the same underlying services.

Never create:

Dashboard data
+
Assistant data
+
Agent data

as separate competing state systems.

---

# 62. CONTROL PLANE PRINCIPLE

The Control Plane is the central coordination layer.

It should conceptually govern:

Identity
+
Permissions
+
Agents
+
Models
+
Tools
+
Workflows
+
Execution
+
Policies
+
Context
+
Memory
+
Observability
+
Audit
+
Cost

The UI is an interface to this layer.

---

# 63. FINAL PRODUCT MODEL

The final conceptual architecture:

                         CONCIENCIA
                              |
              +---------------+---------------+
              |                               |
           OPERATE                          BUILD
              |                               |
        Mission Control                    Agents
        Missions                           Workflows
        Tasks                              Tools
        Approvals                          Models
        Results                            Knowledge
        Reports                            Context & Memory
              |                               |
              +---------------+---------------+
                              |
                        CONTROL PLANE
                              |
       Identity · Policies · Governance · Audit
       Context · Memory · Observability · Cost
                              |
              +---------------+---------------+
              |                               |
        COMMAND CENTER                    EXECUTION
              |                               |
        Command Bar                         Agents
        Ask Conciencia                      Workflows
        Natural Language                    Tools
        Search                              Models
              |                               |
              +---------------+---------------+
                              |
                     EXTERNAL ECOSYSTEM
                              |
        Claude · ChatGPT · Gemini · Qwen · OpenClaw
                              |
             MCP · APIs · Apps · Repositories

---

# 64. CORE UX PRINCIPLE

Conciencia should provide three complementary interfaces:

GUI
→ Observe

Command Bar
→ Act

Ask Conciencia
→ Understand + Explain + Act

All three operate on:

CONTROL PLANE
→ Source of Truth

CONTEXT & MEMORY
→ Persistent Project Intelligence

GOVERNANCE
→ Organizational / Human Control

EXECUTION ENGINE
→ Actual Work

---

# 65. FINAL UX TEST

After each major implementation phase, evaluate Conciencia as a first-time user.

Within approximately five seconds, the product should make it possible to understand:

1. What is Conciencia?
2. What is running?
3. What Missions are active?
4. What are agents doing?
5. What needs approval?
6. What failed?
7. What results were produced?
8. What did the system cost?
9. Where is project memory?
10. How is context transferred?
11. How are external agents governed?
12. What happened during execution?
13. Can I ask Conciencia what is happening?
14. Can I execute actions through Conciencia?
15. Does the Assistant use the same Control Plane?

The answer to #15 must be:

YES.

There must be no parallel Assistant architecture.

---

# 66. STRATEGIC DIFFERENTIATION

Conciencia should not compete primarily by having a better individual AI model.

Its differentiation should come from the system around the models.

The strategic layers are:

Agents
+
Models
+
Tools
+
Workflows
+
Governance
+
Observability
+
Context
+
Memory
+
Execution
+
Human Control

The product should make multiple AI systems work as a coherent system.

---

# 67. FINAL PRODUCT PRINCIPLE

The AI does not own the project.

The agent does not own the workflow.

The model does not own the context.

The chat does not own the memory.

The prompt does not own the project history.

Conciencia owns the:

- orchestration
- governance
- execution context
- persistent project intelligence
- auditability
- coordination layer

The ultimate product vision is:

> Conciencia is the control plane that allows humans, AI agents, models, tools and applications to work together as one observable, governable and context-aware system.

Do not optimize for building another AI assistant.

Optimize for building the infrastructure and experience that makes an ecosystem of AI systems coherent.
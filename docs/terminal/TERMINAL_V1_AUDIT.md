# Conciencia Terminal V1 Audit

## Existing Architecture

Conciencia already has a Clean Architecture shape:

- Presentation: `backend/cli.py`, FastAPI routers in `backend/app/routers`, React pages in `frontend/src/pages`.
- Application/services: mission, workflow, work ledger, reports, retrieval, recommendations, connection and runtime readiness live under `backend/app/services`.
- Domain/models: `Project`, `Mission`, `MissionRun`, `Workflow`, `WorkflowRun`, `Activity`, `Signal`, `Evidence`, `Deliverable`, `Agent`, `Harness`, `Setting`.
- Infrastructure/adapters: SQLAlchemy DB setup, runtime adapters, WebMCP client, Git-backed workspace history, provider/runtime readiness.

The CLI already reuses canonical services for most operations. The root `conciencia` command uses `workspace_home`, which aggregates current project context, projects, active work, recent work, connections, recommendations and AI workforce readiness without invoking LLMs.

## Reusable Services

- `mission_service`: creates, plans, runs and approves missions while synchronizing `MissionRun` with `WorkflowRun`.
- `workflow_engine`: canonical approval gates and event timeline through `WorkflowRun.step_results` and `WorkflowRun.events`.
- `workspace_service`: bounded workspace home and project context discovery.
- `work_service` and `workspace_semantic`: timeline, summaries and lexical/hybrid retrieval.
- `ask_service`: deterministic routing for workspace questions, reports, runtime/status queries and mission proposals.
- `capability_readiness` and `app.core.agent_runtime`: runtime registry/readiness.
- `connection_service`, `recommendation_service`, `report_service`: workspace integrations and deliverable/report flow.

## UX Findings

- `conciencia mission` lacked a callback/default even though `mission list` exists.
- `conciencia config` lacked a callback/default even though `config get` is safe and redacts secrets.
- `conciencia approvals` showed mission UUIDs and did not expose pending step choices.
- `conciencia approve <mission>` required `STEP_INDEX` even when there was exactly one pending approval.
- Long UUIDs leaked in mission tables and approval hints despite existing `_short_id` and `_resolve_uuid`.
- Several command groups already have sensible defaults (`project`, `work`, `report`, `connection`, `runtime`, `workflow`) and should be preserved.

## Architectural Gaps

- There was no reusable command/action registry for CLI, shell, navigator and future Web CLI discovery.
- Interactive grammar was not represented as a deterministic presentation adapter.
- Approval inspection logic was repeated or absent from presentation instead of using a small read-only helper over canonical `MissionRun`/`WorkflowRun` state.
- Background execution is partially modeled by `MissionRun`, `WorkflowRun` and events, but actual workers are still synchronous.

## Minimal Changes Proposed

- Add safe callbacks for `mission` and `config`.
- Add read-only pending approval extraction from canonical workflow state.
- Make `approve <mission>` infer the step only when exactly one approval is pending.
- Keep explicit `approve <mission> <step>` and `reject <mission> <step>` behavior.
- Add a lightweight command registry service for discoverability and shell routing.
- Add a small deterministic `conciencia shell` and `conciencia nav`/`/` search surface using existing work retrieval.

## Risks

- Typer nested callbacks can regress command parsing if defaults are too clever.
- Approval inference must not bypass workflow approval policy; it should only select the existing pending step then call `mission_service.approve_mission_step`.
- Shell grammar must not become a privileged execution path. It should route to existing commands/services.
- Full background execution needs a persistent worker migration; faking it in presentation would create misleading semantics.

## Migration Strategy

1. Harden existing CLI commands with safe defaults and actionable errors.
2. Introduce command/action registry as metadata, not business logic.
3. Build deterministic shell grammar over existing services.
4. Extend `MissionRun`/`WorkflowRun` event stream for `watch`.
5. Add persistent queued worker execution in a later migration once storage and process-manager boundaries are explicit.

## Do Not Rewrite

- Do not replace `Mission`, `MissionRun`, `Workflow` or `WorkflowRun`.
- Do not create terminal-specific mission/project/approval models.
- Do not bypass `mission_service` or `workflow_engine` for approvals.
- Do not replace `workspace_home`.
- Do not redesign the frontend.
- Do not introduce Docker as a required background runtime.
- Do not call LLMs during startup or deterministic navigation.

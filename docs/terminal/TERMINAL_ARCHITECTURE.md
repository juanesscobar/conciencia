# Terminal Architecture

## Boundary

Terminal V1 is a presentation adapter over the existing application services.
It must not create terminal-only domain objects.

CLI, shell and future Web CLI should share:

- command metadata from `app.services.command_registry`;
- workspace home from `workspace_service.workspace_home`;
- navigation from `workspace_semantic.retrieve_workspace`;
- questions from `ask_service.route_request`;
- missions and approvals from `mission_service`;
- runtime readiness from `capability_readiness` and `app.core.agent_runtime`;
- run/event state from `MissionRun` and `WorkflowRun`.

## Dependency Direction

`backend/cli.py` can import application services and models for rendering.
Services must not import CLI presentation code.

The command registry is metadata-only. It exposes action names, aliases,
arguments and safety hints, but does not execute business logic.

## Implemented V1 Slice

- `conciencia mission` defaults to mission listing.
- `conciencia config` defaults to safe redacted config display.
- `conciencia approvals` renders concrete pending workflow steps.
- `conciencia approve <mission>` resolves the step only when exactly one gate is pending.
- `conciencia actions` exposes discoverable commands.
- `conciencia nav <query>` searches commands and workspace evidence.
- `conciencia shell` provides deterministic `/`, `>`, `@`, `!` routing.

## Future Web CLI

A Web CLI should call the same semantic endpoints/services, not browser shell
commands. It should receive command definitions, submit application commands,
watch event streams, and preserve auth/permissions/approval gates.

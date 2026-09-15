# Interaction Language

Conciencia Terminal V1 uses a small deterministic grammar:

- `/ query`: navigate/search workspace resources and command actions.
- `> text`: ask Conciencia about workspace state or propose structured work.
- `@runtime text`: prepare runtime/agent routing through canonical services.
- `#project`: reserved for project/context switching.
- `!`: inspect attention items, currently pending approvals.
- `?`: list discoverable actions.
- `q`: quit interactive shell.

## Routing Order

1. Exact shell token.
2. Known command/action aliases from `command_registry`.
3. Workspace retrieval through `workspace_semantic`.
4. Existing `ask_service` deterministic routes.
5. LLM interpretation only as a future optional layer.

## Safety

The grammar never bypasses domain services. Approvals still go through
`mission_service.approve_mission_step`; runtime work must become a mission or
canonical agent execution rather than direct shell execution.

# Background Execution

## Current State

Conciencia already persists:

- `Mission`;
- `MissionRun`;
- `Workflow`;
- `WorkflowRun`;
- workflow events;
- logs, costs, tokens and errors.

However, `mission_service.run_mission` currently executes synchronously. Closing
the terminal can still interrupt foreground execution unless a separate process
manager is used.

## Implemented State

Terminal V1 improves the watch/approval/user-facing contract but does not fake
detached execution. `conciencia watch` and `run watch` remain poll-based views
over persisted run state.

## Minimal Migration

Add a persistent job/run queue that stores:

- job id;
- mission id;
- workflow run id;
- status: queued, running, waiting_approval, completed, failed, cancelled;
- worker/runtime;
- timestamps;
- retry count;
- last error.

Workers should claim queued jobs and call the same application services used by
the CLI. Production can run workers under systemd, a process manager, or the
existing deployment runtime. Docker must remain optional.

## Event Stream

Reuse `WorkflowRun.events` as the source for terminal/web watch streams. Future
transport can expose it via polling, SSE or WebSocket without changing the
domain model.

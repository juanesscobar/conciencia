"""Discoverable terminal command/action metadata.

This registry intentionally contains presentation metadata only. Handlers stay
in the CLI/API/application layer so future clients can discover actions without
creating a second business model.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class CommandDefinition:
    id: str
    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    category: str = "workspace"
    arguments: list[str] = field(default_factory=list)
    interactive: bool = True
    machine_safe: bool = True
    command: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


COMMANDS: tuple[CommandDefinition, ...] = (
    CommandDefinition(
        id="workspace.home",
        name="Workspace home",
        aliases=["home", "dashboard", "status"],
        description="Show current workspace, attention, active work and quick actions.",
        category="workspace",
        command="conciencia",
    ),
    CommandDefinition(
        id="mission.list",
        name="List missions",
        aliases=["missions", "mission"],
        description="Show recent missions with short IDs and statuses.",
        category="missions",
        command="conciencia mission",
    ),
    CommandDefinition(
        id="approvals.list",
        name="Pending approvals",
        aliases=["approval", "approvals", "attention"],
        description="Show approval gates waiting for a human decision.",
        category="approvals",
        command="conciencia approvals",
    ),
    CommandDefinition(
        id="work.search",
        name="Search workspace",
        aliases=["/", "search", "find", "nav"],
        description="Search projects, missions, reports, evidence and work history.",
        category="navigation",
        arguments=["query"],
        command="conciencia nav <query>",
    ),
    CommandDefinition(
        id="ask.workspace",
        name="Ask workspace",
        aliases=[">", "ask"],
        description="Ask deterministic questions about workspace state before proposing work.",
        category="conversation",
        arguments=["text"],
        command="conciencia ask <text>",
    ),
    CommandDefinition(
        id="agent.route",
        name="Route to runtime",
        aliases=["@", "agent", "runtime"],
        description="Prepare work for an agent/runtime through canonical mission/runtime paths.",
        category="runtimes",
        arguments=["runtime", "text"],
        machine_safe=False,
        command="conciencia shell then @codex inspect frontend",
    ),
    CommandDefinition(
        id="config.get",
        name="Read configuration",
        aliases=["config", "settings"],
        description="Display safe redacted configuration.",
        category="settings",
        command="conciencia config",
    ),
)


def list_commands() -> list[dict]:
    return [command.to_dict() for command in COMMANDS]


def search_commands(query: str) -> list[dict]:
    needle = (query or "").casefold().strip()
    if not needle:
        return list_commands()
    rows = []
    for command in COMMANDS:
        haystack = " ".join(
            [command.id, command.name, command.description, command.category, command.command]
            + command.aliases
        ).casefold()
        if needle in haystack:
            rows.append(command.to_dict())
    return rows

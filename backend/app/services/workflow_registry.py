"""Canonical workflow registry for official mission types."""

from copy import deepcopy
from dataclasses import dataclass

from app.models.mission import MISSION_TYPES


@dataclass(frozen=True)
class WorkflowResolution:
    mission_type: str
    resolvable: bool
    source: str
    steps: tuple[dict, ...]
    reason: str

    def to_dict(self) -> dict:
        return {
            "mission_type": self.mission_type,
            "resolvable": self.resolvable,
            "source": self.source,
            "steps": deepcopy(list(self.steps)),
            "reason": self.reason,
        }


def _step(name: str, capabilities: list[str], timeout: int = 300, retry: int = 1) -> dict:
    return {
        "name": name,
        "agent": None,
        "capabilities": capabilities,
        "timeout": timeout,
        "retry": retry,
    }


APPROVAL = {"name": "approval", "approval": True, "capabilities": [], "timeout": 0}

RESEARCH = [_step("research", ["research"]), _step("synthesis", ["research"]), APPROVAL]
DEVELOPMENT = [
    _step("plan", ["planning"]),
    APPROVAL,
    _step("implement", ["code"], 900, 2),
    _step("test", ["testing"], 600, 2),
]
DESIGN = [
    _step("analysis", ["research"]),
    _step("design", ["documentation"]),
    APPROVAL,
    _step("report", ["reporting"]),
]


WORKFLOW_REGISTRY: dict[str, list[dict]] = {
    "research": RESEARCH,
    "software-development": DEVELOPMENT,
    "code-review": [_step("review", ["code_review"], 600), _step("report", ["reporting"])],
    "debugging": DEVELOPMENT,
    "architecture": DESIGN,
    "testing": [_step("plan", ["testing"]), _step("test", ["testing"], 600, 2), _step("report", ["reporting"])],
    "devops": [
        _step("readiness", ["monitoring"]),
        _step("plan", ["ci_cd"]),
        APPROVAL,
        _step("implement", ["deploys"], 900, 2),
        _step("verify", ["monitoring"], 600, 2),
    ],
    "deployment": [
        _step("readiness", ["monitoring"]),
        _step("plan", ["deploys"]),
        APPROVAL,
        _step("deploy", ["deploys"], 900),
        _step("verify", ["monitoring"], 600, 2),
    ],
    "technical-audit": [_step("audit", ["research", "code_review"], 600), APPROVAL, _step("report", ["reporting"])],
    "agent-design": DESIGN,
    "workflow-design": DESIGN,
    "automation": DEVELOPMENT,
    "integration": DEVELOPMENT,
    "data-analysis": [_step("prepare", ["research"]), _step("analyze", ["research"], 600), _step("synthesis", ["reporting"])],
    "product-research": RESEARCH,
    "competitive-research": RESEARCH,
    "technical-discovery": RESEARCH,
    "lead-research": [
        {
            "name": "discovery",
            "parallel": True,
            "max_parallel": 2,
            "steps": [
                _step("discover-leads", ["leads.read", "search.execute"], 600, 2),
                _step("enrich-websites", ["website_fetch"], 600, 2),
            ],
        },
        _step("classify", ["classification"]),
        APPROVAL,
    ],
    "technical-proposal": DESIGN,
}


def resolve_workflow(mission_type: str, workflow_id: str | None = None) -> WorkflowResolution:
    """Resolve custom or official workflow without a silent generic fallback."""
    if workflow_id:
        return WorkflowResolution(mission_type, True, "custom", (), f"custom workflow {workflow_id}")
    steps = WORKFLOW_REGISTRY.get(mission_type)
    if steps:
        return WorkflowResolution(
            mission_type, True, "registry", tuple(deepcopy(steps)), "official workflow registered"
        )
    reason = "unknown mission type" if mission_type not in MISSION_TYPES else "official type has no workflow"
    return WorkflowResolution(mission_type, False, "none", (), reason)


def coverage() -> dict[str, bool]:
    return {mission_type: resolve_workflow(mission_type).resolvable for mission_type in MISSION_TYPES}


missing = [mission_type for mission_type, ready in coverage().items() if not ready]
if missing:
    raise RuntimeError(f"Official mission types without workflow: {', '.join(missing)}")

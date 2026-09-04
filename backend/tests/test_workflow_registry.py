"""Contract tests for intent-to-plan workflow resolution."""

import pytest

from app.models.mission import MISSION_TYPES
from app.services import mission_service
from app.services.workflow_registry import coverage, resolve_workflow


def test_all_official_mission_types_are_resolvable():
    assert coverage() == {mission_type: True for mission_type in MISSION_TYPES}


@pytest.mark.parametrize("mission_type", MISSION_TYPES)
def test_all_official_mission_types_can_be_created_and_planned(db, mission_type):
    mission = mission_service.create_mission(
        db,
        name=f"Plan {mission_type}",
        objective="Verify official workflow coverage",
        type=mission_type,
    )
    planned = mission_service.plan_mission(db, mission)
    assert planned.status == "planned"
    assert planned.workflow_id


def test_deployment_workflow_requires_approval_before_deploy():
    steps = list(resolve_workflow("deployment").steps)
    names = [step["name"] for step in steps]
    approval_index = next(i for i, step in enumerate(steps) if step.get("approval"))
    assert names[:2] == ["readiness", "plan"]
    assert approval_index < names.index("deploy") < names.index("verify")


def test_creation_fails_early_when_workflow_is_not_resolvable(db, monkeypatch):
    from app.services import workflow_registry

    monkeypatch.delitem(workflow_registry.WORKFLOW_REGISTRY, "deployment")
    with pytest.raises(ValueError, match="No hay workflow resoluble"):
        mission_service.create_mission(
            db,
            name="Unsafe deploy",
            objective="Deploy without a plan",
            type="deployment",
        )

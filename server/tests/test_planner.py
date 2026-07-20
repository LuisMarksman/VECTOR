from __future__ import annotations

from app.core.planner import HeuristicPlanner
from app.models.schemas import Capability


def test_single_step():
    plan = HeuristicPlanner().plan("what's the weather like?")
    assert len(plan.steps) == 1


def test_splits_on_and():
    plan = HeuristicPlanner().plan("turn on the lights and vacuum the floor")
    assert len(plan.steps) == 2
    assert plan.steps[0].capability == Capability.HOME_AUTOMATION
    assert plan.steps[1].capability == Capability.ROBOT


def test_arm_routing():
    plan = HeuristicPlanner().plan("pick up the red cup")
    assert plan.steps[0].capability == Capability.ROBOT_ARM


def test_reminder_routing():
    plan = HeuristicPlanner().plan("remind me to call mom")
    assert plan.steps[0].capability == Capability.REMINDER

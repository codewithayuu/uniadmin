"""Null agent test — verifies 0.0 score for do-nothing agent.

Run with: python -m pytest uniadmin/tests/test_null_agent.py -v
"""

import pytest

from uniadmin.models import UniAdminAction, TASK_CONFIGS
from uniadmin.server.uniadmin_environment import UniAdminEnvironment


@pytest.fixture
def env():
    e = UniAdminEnvironment()
    yield e
    e.close()


@pytest.mark.parametrize("task_id", list(TASK_CONFIGS.keys()))
def test_null_agent_scores_low(env, task_id):
    """Null agent: reset → submit empty → score should be near 0."""
    env.reset(task_id=task_id)
    obs = env.step(UniAdminAction(
        tool_name="submit_final_response",
        arguments={"message": "No action taken.", "resolution_summary": {}}
    ))
    assert obs.done is True
    assert obs.reward is not None
    assert obs.reward <= 0.20, f"Null agent scored {obs.reward} on {task_id} (expected ≤ 0.20)"
    print(f"  {task_id}: null_score={obs.reward:.3f}")

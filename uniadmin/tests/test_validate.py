"""Validation tests for OpenEnv spec compliance.

Run with: python -m pytest uniadmin/tests/test_validate.py -v
"""

import json
import pytest

from uniadmin.models import (
    UniAdminAction,
    UniAdminObservation,
    UniAdminState,
    TOOL_NAMES,
    TASK_CONFIGS,
    get_task_list,
)
from uniadmin.server.uniadmin_environment import UniAdminEnvironment
from uniadmin.world.loader import get_task_entity_refs


TASK_REFS = get_task_entity_refs()
TASK1_STUDENT = TASK_REFS["task_1"]["student_id"]
TASK2_STUDENT = TASK_REFS["task_2"]["student_id"]
TASK3 = TASK_REFS["task_3"]
TASK5_STUDENT = TASK_REFS["task_5"]["student_id"]


@pytest.fixture
def env():
    e = UniAdminEnvironment()
    yield e
    e.close()


class TestSpecCompliance:
    """OpenEnv spec compliance tests."""

    def test_reset_returns_observation(self, env):
        obs = env.reset()
        assert isinstance(obs, UniAdminObservation)
        assert obs.done is False
        assert obs.reward is None
        assert obs.current_step == 0
        assert len(obs.available_tools) == len(TOOL_NAMES)

    def test_step_returns_observation(self, env):
        env.reset()
        obs = env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": "STU-001"}))
        assert isinstance(obs, UniAdminObservation)
        assert obs.current_step == 1
        assert obs.reward is not None

    def test_state_returns_state(self, env):
        env.reset()
        state = env.state()
        assert isinstance(state, UniAdminState)
        assert state.episode_active is True
        assert len(state.state_hash) == 64

    def test_close_deactivates(self, env):
        env.reset()
        env.close()
        state = env.state()
        assert state.episode_active is False

    def test_6_tasks_available(self):
        tasks = get_task_list()
        assert len(tasks) == 6

    def test_all_task_ids_valid(self, env):
        for tid in TASK_CONFIGS:
            obs = env.reset(task_id=tid)
            assert obs.done is False
            assert obs.task_id == tid

    def test_tools_listed(self, env):
        env.reset()
        obs = env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": "STU-001"}))
        assert len(obs.available_tools) == len(TOOL_NAMES)

    def test_done_flag_on_submit(self, env):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"message": "Done.", "resolution_summary": {"x": 1}}
        ))
        assert obs.done is True

    def test_reward_in_0_1(self, env):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"message": "Done.", "resolution_summary": {"x": 1}}
        ))
        assert 0.0 <= obs.reward <= 1.0


class TestDeterminism:
    """Verify deterministic behavior."""

    def test_reset_produces_identical_state(self, env):
        env.reset(task_id="task_1_course_inquiry")
        h1 = env.state().state_hash

        env.reset(task_id="task_1_course_inquiry")
        h2 = env.state().state_hash

        assert h1 == h2

    def test_same_actions_produce_same_results(self, env):
        env.reset(task_id="task_1_course_inquiry")
        obs1 = env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": TASK1_STUDENT}))
        r1 = obs1.tool_result

        env.reset(task_id="task_1_course_inquiry")
        obs2 = env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": TASK1_STUDENT}))
        r2 = obs2.tool_result

        assert r1 == r2

    def test_all_tasks_deterministic(self, env):
        for tid in TASK_CONFIGS:
            env.reset(task_id=tid)
            h1 = env.state().state_hash
            env.reset(task_id=tid)
            h2 = env.state().state_hash
            assert h1 == h2, f"Task {tid} is non-deterministic"


class TestEdgeCases:
    """Edge case handling tests."""

    def test_invalid_entity_id(self, env):
        env.reset()
        obs = env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": "INVALID"}))
        assert obs.tool_success is False
        assert "not found" in (obs.error_message or "").lower()

    def test_missing_required_arg(self, env):
        env.reset()
        obs = env.step(UniAdminAction(tool_name="enroll_student", arguments={"student_id": "STU-001"}))
        assert obs.tool_success is False
        assert "course_id" in (obs.error_message or "").lower()

    def test_invalid_tool_name(self, env):
        env.reset()
        obs = env.step(UniAdminAction(tool_name="nonexistent_tool", arguments={}))
        assert obs.tool_success is False

    def test_step_without_reset(self, env):
        obs = env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": "STU-001"}))
        assert obs.done is True

    def test_step_after_done(self, env):
        env.reset()
        env.step(UniAdminAction(tool_name="submit_final_response", arguments={"message": "x", "resolution_summary": {}}))
        obs = env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": "STU-001"}))
        assert obs.done is True

    def test_double_reset(self, env):
        env.reset(task_id="task_1_course_inquiry")
        env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": TASK1_STUDENT}))
        env.reset(task_id="task_1_course_inquiry")
        state = env.state()
        assert state.step_count == 0
        assert len(state.audit_log) == 0

    def test_max_steps_exceeded(self, env):
        env.reset(task_id="task_1_course_inquiry")
        for i in range(16):
            obs = env.step(UniAdminAction(
                tool_name="get_student_record",
                arguments={"student_id": f"STU-{(i % 300) + 1:03d}"}
            ))
            if obs.done:
                break
        assert obs.done is True

    def test_task3_deadline_enforcement(self, env):
        env.reset(task_id="task_3_course_switch")
        # Find a valid course first
        obs = env.step(UniAdminAction(
            tool_name="search_courses",
            arguments={"filters": {"department": "DEPT-CS"}}
        ))
        import json
        data = json.loads(obs.tool_result)
        course_id = data["results"][0]["course_id"] if data["results"] else "CSE-101"
        
        for i in range(17):
            env.step(UniAdminAction(
                tool_name="search_students",
                arguments={"query": "", "page": i + 1}
            ))
        obs = env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={"student_id": TASK3["student_id"], "course_id": course_id}
        ))
        assert obs.tool_success is False
        assert "deadline" in (obs.error_message or "").lower()

    def test_negative_payment(self, env):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="update_fee_record",
            arguments={"student_id": TASK5_STUDENT, "payment_amount": -500}
        ))
        assert obs.tool_success is False

    def test_gender_mismatch_hostel(self, env):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="transfer_hostel",
            arguments={"student_id": TASK1_STUDENT, "target_room_id": "RM-A001"}
        ))
        assert obs.tool_success is False
        assert "gender" in (obs.error_message or "").lower()

    def test_server_never_crashes(self, env):
        """Rapid-fire bad inputs should not crash."""
        env.reset()
        bad_actions = [
            UniAdminAction(tool_name="", arguments={}),
            UniAdminAction(tool_name="get_student_record", arguments={}),
            UniAdminAction(tool_name="enroll_student", arguments={"student_id": None}),
            UniAdminAction(tool_name="check_prerequisites", arguments={"student_id": "X", "course_id": "Y"}),
            UniAdminAction(tool_name="update_fee_record", arguments={"student_id": TASK5_STUDENT, "payment_amount": "abc"}),
        ]
        for action in bad_actions:
            obs = env.step(action)
            assert isinstance(obs, UniAdminObservation)


class TestNullAgent:
    """Null agent scores 0.0 on all tasks."""

    @pytest.mark.parametrize("task_id", list(TASK_CONFIGS.keys()))
    def test_null_agent(self, env, task_id):
        env.reset(task_id=task_id)
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"message": "I cannot help.", "resolution_summary": {}}
        ))
        assert obs.done is True
        assert obs.reward <= 0.20, f"Null agent scored {obs.reward} on {task_id}"


class TestOptimalAgents:
    """Scripted optimal agents score high on easy tasks."""

    def test_optimal_task_1(self, env):
        env.reset(task_id="task_1_course_inquiry")
        env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": TASK1_STUDENT}))
        env.step(UniAdminAction(tool_name="get_enrollment_history", arguments={"student_id": TASK1_STUDENT}))
        obs = env.step(UniAdminAction(tool_name="search_courses", arguments={"filters": {"department": "DEPT-CS", "semester_offered": 6}}))
        cs = json.loads(obs.tool_result)
        if cs["results"]:
            env.step(UniAdminAction(tool_name="get_course_details", arguments={"course_id": cs["results"][0]["course_id"]}))
        env.step(UniAdminAction(tool_name="check_credit_limits", arguments={"student_id": TASK1_STUDENT}))
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={
                "message": "Here are available CS electives for semester 6.",
                "resolution_summary": {"courses": [c["course_id"] for c in cs["results"]]}
            }
        ))
        assert obs.reward >= 0.80

    def test_optimal_task_2(self, env):
        env.reset(task_id="task_2_hostel_allocation")
        env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": TASK2_STUDENT}))
        env.step(UniAdminAction(tool_name="check_fee_clearance", arguments={"student_id": TASK2_STUDENT}))
        env.step(UniAdminAction(tool_name="get_hostel_details", arguments={"student_id": TASK2_STUDENT}))
        obs = env.step(UniAdminAction(tool_name="transfer_hostel", arguments={"student_id": TASK2_STUDENT, "target_room_id": "RM-E001"}))
        assert obs.tool_success, f"Transfer failed: {obs.error_message}"
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={
                "message": "Room RM-E001 allocated.",
                "resolution_summary": {"room": "RM-E001", "student": TASK2_STUDENT}
            }
        ))
        assert obs.reward >= 0.80

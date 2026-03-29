"""Tests for graders (tasks 1-3).

Tests optimal scripted agents score near 1.0 and null agents score 0.0.
Run with: python -m pytest uniadmin/tests/test_graders.py -v
"""

import json
import pytest

from uniadmin.models import UniAdminAction
from uniadmin.server.uniadmin_environment import UniAdminEnvironment
from uniadmin.world.loader import get_task_entity_refs


TASK_REFS = get_task_entity_refs()
TASK1_STUDENT = TASK_REFS["task_1"]["student_id"]
TASK2_STUDENT = TASK_REFS["task_2"]["student_id"]
TASK3 = TASK_REFS["task_3"]


@pytest.fixture
def env():
    e = UniAdminEnvironment()
    yield e
    e.close()


class TestNullAgent:
    """Null agent: reset then immediately submit empty response -> score 0.0."""

    def test_null_task_1(self, env):
        env.reset(task_id="task_1_course_inquiry")
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"message": "", "resolution_summary": {}}
        ))
        # message is empty -> submit fails
        assert obs.tool_success is False or obs.reward == 0.0

    def test_null_task_1_with_message(self, env):
        env.reset(task_id="task_1_course_inquiry")
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"message": "I don't know.", "resolution_summary": {}}
        ))
        assert obs.done is True
        assert obs.reward is not None
        assert obs.reward <= 0.15  # Only gets submit points at most

    def test_null_task_2(self, env):
        env.reset(task_id="task_2_hostel_allocation")
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"message": "Done.", "resolution_summary": {}}
        ))
        assert obs.done is True
        assert obs.reward is not None
        assert obs.reward <= 0.15

    def test_null_task_3(self, env):
        env.reset(task_id="task_3_course_switch")
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"message": "Done.", "resolution_summary": {}}
        ))
        assert obs.done is True
        assert obs.reward is not None
        assert obs.reward <= 0.05


class TestOptimalTask1:
    """Optimal agent for Task 1 should score near 1.0."""

    def test_optimal_task_1(self, env):
        obs = env.reset(task_id="task_1_course_inquiry")

        # Step 1: Get student record
        obs = env.step(UniAdminAction(
            tool_name="get_student_record",
            arguments={"student_id": TASK1_STUDENT}
        ))
        assert obs.tool_success

        # Step 2: Get enrollment history
        obs = env.step(UniAdminAction(
            tool_name="get_enrollment_history",
            arguments={"student_id": TASK1_STUDENT}
        ))
        assert obs.tool_success
        enrollments = json.loads(obs.tool_result)
        current_courses = [e["course_id"] for e in enrollments["enrollments"] if e["status"] == "enrolled"]

        # Step 3: Search CS courses for semester 6
        obs = env.step(UniAdminAction(
            tool_name="search_courses",
            arguments={"filters": {"department": "DEPT-CS", "semester_offered": 6}}
        ))
        assert obs.tool_success

        # Step 4: Get details of a candidate course
        cs_courses = json.loads(obs.tool_result)
        if cs_courses["results"]:
            obs = env.step(UniAdminAction(
                tool_name="get_course_details",
                arguments={"course_id": cs_courses["results"][0]["course_id"]}
            ))
            assert obs.tool_success

        # Step 5: Check credit limits
        obs = env.step(UniAdminAction(
            tool_name="check_credit_limits",
            arguments={"student_id": TASK1_STUDENT}
        ))
        assert obs.tool_success

        # Step 6: Submit
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={
                "message": "Here are the available CS electives for next semester that fit your schedule and credit limit.",
                "resolution_summary": {
                    "available_courses": [c["course_id"] for c in cs_courses["results"]],
                    "current_courses": current_courses,
                }
            }
        ))
        assert obs.done
        assert obs.reward is not None
        assert obs.reward >= 0.80, f"Expected >= 0.80 but got {obs.reward}"


class TestOptimalTask2:
    """Optimal agent for Task 2 should score near 1.0."""

    def test_optimal_task_2(self, env):
        obs = env.reset(task_id="task_2_hostel_allocation")

        # Step 1: Get student record
        obs = env.step(UniAdminAction(
            tool_name="get_student_record",
            arguments={"student_id": TASK2_STUDENT}
        ))
        assert obs.tool_success
        student = json.loads(obs.tool_result)
        assert student["gender"] == "female"

        # Step 2: Check fee clearance
        obs = env.step(UniAdminAction(
            tool_name="check_fee_clearance",
            arguments={"student_id": TASK2_STUDENT}
        ))
        assert obs.tool_success

        # Step 3: Check hostel details (should be unallocated)
        obs = env.step(UniAdminAction(
            tool_name="get_hostel_details",
            arguments={"student_id": TASK2_STUDENT}
        ))
        assert obs.tool_success

        # Step 4: Transfer to female room RM-E001
        obs = env.step(UniAdminAction(
            tool_name="transfer_hostel",
            arguments={"student_id": TASK2_STUDENT, "target_room_id": "RM-E001"}
        ))
        assert obs.tool_success, f"Transfer failed: {obs.error_message}"

        # Step 5: Submit
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={
                "message": "Room RM-E001 in Einstein Hall (female block) has been allocated to you.",
                "resolution_summary": {
                    "allocated_room": "RM-E001",
                    "block": "BLK-E",
                    "student_id": TASK2_STUDENT
                }
            }
        ))
        assert obs.done
        assert obs.reward is not None
        assert obs.reward >= 0.80, f"Expected >= 0.80 but got {obs.reward}"


class TestOptimalTask3:
    """Optimal agent for Task 3 should score well (within deadline)."""

    def test_optimal_task_3(self, env):
        obs = env.reset(task_id="task_3_course_switch")
        desc = obs.task_description

        # Extract course IDs from description
        import re
        course_ids = re.findall(r'[A-Z]+-\d+', desc)
        student_id = TASK3["student_id"]

        # Step 1: Get student record
        obs = env.step(UniAdminAction(
            tool_name="get_student_record",
            arguments={"student_id": student_id}
        ))
        assert obs.tool_success

        # Step 2: Get enrollment history
        obs = env.step(UniAdminAction(
            tool_name="get_enrollment_history",
            arguments={"student_id": student_id}
        ))
        assert obs.tool_success
        hist = json.loads(obs.tool_result)
        enrolled = [e for e in hist["enrollments"] if e["status"] == "enrolled"]

        # Find course A (currently enrolled) and course B (target)
        course_a_id = enrolled[0]["course_id"] if enrolled else ""

        # Get course B from task description
        course_b_candidates = [cid for cid in course_ids if cid != course_a_id and cid != student_id]
        course_b_id = course_b_candidates[0] if course_b_candidates else ""

        if not course_a_id or not course_b_id:
            pytest.skip("Could not determine course A and B from task")

        # Step 3: Check prerequisites
        obs = env.step(UniAdminAction(
            tool_name="check_prerequisites",
            arguments={"student_id": student_id, "course_id": course_b_id}
        ))

        # Step 4: Check seat availability
        obs = env.step(UniAdminAction(
            tool_name="check_seat_availability",
            arguments={"course_id": course_b_id}
        ))

        # Step 5: Check credit limits
        obs = env.step(UniAdminAction(
            tool_name="check_credit_limits",
            arguments={"student_id": student_id}
        ))

        # Step 6: Check fee status
        obs = env.step(UniAdminAction(
            tool_name="check_fee_clearance",
            arguments={"student_id": student_id}
        ))

        # Step 7: Check scholarship compliance
        obs = env.step(UniAdminAction(
            tool_name="search_scholarships",
            arguments={"student_id": student_id}
        ))
        obs = env.step(UniAdminAction(
            tool_name="check_scholarship_compliance",
            arguments={"student_id": student_id, "scholarship_id": "SCH-001"}
        ))

        # Step 8: Drop course A
        obs = env.step(UniAdminAction(
            tool_name="drop_course",
            arguments={"student_id": student_id, "course_id": course_a_id}
        ))
        drop_success = obs.tool_success

        # Step 9: Enroll in course B
        if drop_success:
            obs = env.step(UniAdminAction(
                tool_name="enroll_student",
                arguments={"student_id": student_id, "course_id": course_b_id}
            ))

        # Step 10: Submit
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={
                "message": f"Course switch complete: dropped {course_a_id}, enrolled in {course_b_id}.",
                "resolution_summary": {
                    "dropped": course_a_id,
                    "enrolled": course_b_id,
                    "student_id": student_id
                }
            }
        ))
        assert obs.done
        assert obs.reward is not None
        # Score depends on whether drop+enroll succeeded
        print(f"Task 3 score: {obs.reward}")
        # At minimum, the validation checks should score points
        assert obs.reward >= 0.30, f"Expected >= 0.30 but got {obs.reward}"

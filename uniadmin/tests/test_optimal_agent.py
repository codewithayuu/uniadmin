"""Extended optimal agent tests for harder tasks.

Run with: python -m pytest uniadmin/tests/test_optimal_agent.py -v
"""

import json
import pytest

from uniadmin.models import UniAdminAction
from uniadmin.server.uniadmin_environment import UniAdminEnvironment
from uniadmin.world.loader import get_task_entity_refs


TASK_REFS = get_task_entity_refs()
TASK5_STUDENT = TASK_REFS["task_5"]["student_id"]


@pytest.fixture
def env():
    e = UniAdminEnvironment()
    yield e
    e.close()


class TestOptimalTask4:
    """Optimal agent for Task 4: Concurrent Enrollment Conflict."""

    def test_optimal_task_4(self, env):
        obs = env.reset(task_id="task_4_concurrent_conflict")
        desc = obs.task_description

        import re
        stu_ids = re.findall(r'STU-\d+', desc)
        course_ids = re.findall(r'[A-Z]+-\d+', desc)
        course_ids = [c for c in course_ids if not c.startswith("STU")]

        stu_x = stu_ids[0] if len(stu_ids) > 0 else "STU-150"
        stu_y = stu_ids[1] if len(stu_ids) > 1 else "STU-151"
        course_id = course_ids[0] if course_ids else ""

        if not course_id:
            pytest.skip("Could not extract course_id")

        env.step(UniAdminAction(tool_name="check_seat_availability", arguments={"course_id": course_id}))
        env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": stu_x}))
        env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": stu_y}))
        env.step(UniAdminAction(tool_name="search_scholarships", arguments={"student_id": stu_x}))
        env.step(UniAdminAction(tool_name="search_scholarships", arguments={"student_id": stu_y}))
        env.step(UniAdminAction(tool_name="check_fee_clearance", arguments={"student_id": stu_x}))
        env.step(UniAdminAction(tool_name="search_courses", arguments={"filters": {"has_availability": True}}))

        obs = env.step(UniAdminAction(tool_name="enroll_student", arguments={"student_id": stu_x, "course_id": course_id}))

        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={
                "message": f"Enrolled {stu_x} (scholarship dependency). {stu_y} denied — alternative courses available.",
                "resolution_summary": {
                    "enrolled": stu_x,
                    "denied": stu_y,
                    "reason": "scholarship_priority",
                    "alternatives_suggested": True,
                }
            }
        ))
        assert obs.done
        print(f"Task 4 score: {obs.reward:.3f}")
        assert obs.reward >= 0.50


class TestOptimalTask5Partial:
    """Partial optimal agent for Task 5 — discovers blockers."""

    def test_discover_blockers(self, env):
        obs = env.reset(task_id="task_5_graduation_crisis")

        obs = env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": TASK5_STUDENT}))
        data = json.loads(obs.tool_result)
        assert data["academic_status"] == "probation"

        obs = env.step(UniAdminAction(tool_name="get_fee_status", arguments={"student_id": TASK5_STUDENT}))
        data = json.loads(obs.tool_result)
        assert data["total_outstanding"] == 2500

        obs = env.step(UniAdminAction(tool_name="check_credit_limits", arguments={"student_id": TASK5_STUDENT}))
        assert any("REGULATION UPDATE" in n for n in obs.notifications)

        obs = env.step(UniAdminAction(tool_name="search_scholarships", arguments={"student_id": TASK5_STUDENT}))
        obs = env.step(UniAdminAction(tool_name="get_hostel_details", arguments={"student_id": TASK5_STUDENT}))
        obs = env.step(UniAdminAction(tool_name="get_enrollment_history", arguments={"student_id": TASK5_STUDENT}))

        obs = env.step(UniAdminAction(tool_name="update_fee_record", arguments={"student_id": TASK5_STUDENT, "payment_amount": 2500}))
        assert obs.tool_success
        data = json.loads(obs.tool_result)
        assert data["new_amount_due"] == 0

        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={
                "message": "Found 6 blockers for Karthik's graduation. Resolved fee payment. Other blockers require additional action.",
                "resolution_summary": {
                    "blockers_found": [
                        "missing_credits", "unpaid_fees", "prerequisite_gap",
                        "scholarship_constraint", "hostel_checkout", "probation_flag"
                    ],
                    "resolved": ["fee_payment"],
                    "pending": ["credit_overload", "prerequisite_waiver", "hostel_checkout", "probation_clearance"],
                }
            }
        ))
        assert obs.done
        print(f"Task 5 partial score: {obs.reward:.3f}")
        assert obs.reward >= 0.30

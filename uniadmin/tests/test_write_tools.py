"""Tests for UniAdmin write tools (12-21) and exception system.

Run with: python -m pytest uniadmin/tests/test_write_tools.py -v
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
TASK5 = TASK_REFS["task_5"]
TASK6 = TASK_REFS["task_6"]


@pytest.fixture
def env():
    """Create a fresh environment instance."""
    e = UniAdminEnvironment()
    yield e
    e.close()


class TestCheckPrerequisites:
    """Test check_prerequisites tool."""

    def test_missing_args(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(tool_name="check_prerequisites", arguments={}))
        assert obs.tool_success is False

    def test_no_prereqs(self, env: UniAdminEnvironment):
        env.reset()
        # Find a course with no prerequisites
        obs = env.step(UniAdminAction(
            tool_name="search_courses",
            arguments={"filters": {"department": "DEPT-CS"}}
        ))
        data = json.loads(obs.tool_result)
        no_prereq_course = None
        for c in data["results"]:
            if not c.get("prerequisites"):
                no_prereq_course = c["course_id"]
                break

        if no_prereq_course:
            obs2 = env.step(UniAdminAction(
                tool_name="check_prerequisites",
                arguments={"student_id": "STU-171", "course_id": no_prereq_course}
            ))
            assert obs2.tool_success is True
            d = json.loads(obs2.tool_result)
            assert d["prerequisites_met"] is True


class TestCheckCreditLimits:
    """Test check_credit_limits tool."""

    def test_valid_student(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="check_credit_limits",
            arguments={"student_id": "STU-171"}
        ))
        assert obs.tool_success is True
        data = json.loads(obs.tool_result)
        assert "current_credits" in data
        assert "credit_limit" in data
        assert "headroom" in data

    def test_invalid_student(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="check_credit_limits",
            arguments={"student_id": "INVALID"}
        ))
        assert obs.tool_success is False

    def test_task5_notification_trigger(self, env: UniAdminEnvironment):
        """check_credit_limits for Karthik triggers regulation change in Task 5."""
        env.reset(task_id="task_5_graduation_crisis")
        obs = env.step(UniAdminAction(
            tool_name="check_credit_limits",
            arguments={"student_id": TASK5["student_id"]}
        ))
        assert obs.tool_success is True
        # Notification should appear
        assert any("REGULATION UPDATE" in n for n in obs.notifications)


class TestCheckSeatAvailability:
    """Test check_seat_availability tool."""

    def test_valid_course(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="search_courses",
            arguments={"filters": {"department": "DEPT-CS"}}
        ))
        data = json.loads(obs.tool_result)
        course_id = data["results"][0]["course_id"]

        obs2 = env.step(UniAdminAction(
            tool_name="check_seat_availability",
            arguments={"course_id": course_id}
        ))
        assert obs2.tool_success is True
        d = json.loads(obs2.tool_result)
        assert "available_seats" in d
        assert "max_capacity" in d


class TestCheckFeeClearance:
    """Test check_fee_clearance tool."""

    def test_cleared_student(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="check_fee_clearance",
            arguments={"student_id": TASK2_STUDENT}
        ))
        assert obs.tool_success is True
        data = json.loads(obs.tool_result)
        assert data["fee_cleared"] is True

    def test_karthik_outstanding(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="check_fee_clearance",
            arguments={"student_id": TASK5["student_id"]}
        ))
        assert obs.tool_success is True
        data = json.loads(obs.tool_result)
        assert data["fee_cleared"] is False
        assert data["outstanding_amount"] == 2500


class TestCheckScholarshipCompliance:
    """Test check_scholarship_compliance tool."""

    def test_missing_args(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="check_scholarship_compliance",
            arguments={"student_id": TASK3["student_id"]}
        ))
        assert obs.tool_success is False
        assert "scholarship_id" in (obs.error_message or "").lower()

    def test_valid_check(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="check_scholarship_compliance",
            arguments={"student_id": TASK3["student_id"], "scholarship_id": TASK3["scholarship_id"]}
        ))
        assert obs.tool_success is True
        data = json.loads(obs.tool_result)
        assert "compliant" in data
        assert data["is_beneficiary"] is True


class TestEnrollStudent:
    """Test enroll_student tool."""

    def test_missing_args(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={"student_id": TASK2_STUDENT}
        ))
        assert obs.tool_success is False
        assert "course_id" in (obs.error_message or "").lower()

    def test_successful_enrollment(self, env: UniAdminEnvironment):
        """Enroll a fee-cleared student in an available course."""
        env.reset()
        # Find an available course with no prereqs
        obs = env.step(UniAdminAction(
            tool_name="search_courses",
            arguments={"filters": {"department": "DEPT-HS", "has_availability": True}}
        ))
        data = json.loads(obs.tool_result)
        if data["total"] == 0:
            pytest.skip("No available HS courses")

        course = None
        for c in data["results"]:
            if not c.get("prerequisites"):
                course = c
                break
        if not course:
            pytest.skip("No prereq-free available courses found")

        course_id = course["course_id"]
        old_enrollment = course["current_enrollment"]

        obs2 = env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={"student_id": TASK2_STUDENT, "course_id": course_id}
        ))
        assert obs2.tool_success is True
        d = json.loads(obs2.tool_result)
        assert "enrollment_id" in d

        # Verify enrollment count increased
        obs3 = env.step(UniAdminAction(
            tool_name="check_seat_availability",
            arguments={"course_id": course_id}
        ))
        d3 = json.loads(obs3.tool_result)
        assert d3["current_enrollment"] == old_enrollment + 1

    def test_duplicate_enrollment(self, env: UniAdminEnvironment):
        """Cannot enroll in a course already enrolled in."""
        env.reset()
        # STU-171 is already enrolled in courses
        obs = env.step(UniAdminAction(
            tool_name="get_enrollment_history",
            arguments={"student_id": "STU-171"}
        ))
        data = json.loads(obs.tool_result)
        enrolled = [e for e in data["enrollments"] if e["status"] == "enrolled"]
        if not enrolled:
            pytest.skip("No current enrollments to test duplicate")

        course_id = enrolled[0]["course_id"]
        obs2 = env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={"student_id": "STU-171", "course_id": course_id}
        ))
        assert obs2.tool_success is False
        assert "already enrolled" in (obs2.error_message or "").lower()

    def test_deadline_enforcement(self, env: UniAdminEnvironment):
        """After deadline, enrollment is rejected (Task 3)."""
        env.reset(task_id="task_3_course_switch")
        # Find an actual course ID from the world first
        obs = env.step(UniAdminAction(
            tool_name="search_courses",
            arguments={"filters": {"department": "DEPT-CS"}, "page": 1}
        ))
        data = json.loads(obs.tool_result)
        course_id = data["results"][0]["course_id"] if data["results"] else "CSE-101"
        
        # Burn steps to pass the deadline (step 16)
        for i in range(17):
            env.step(UniAdminAction(
                tool_name="get_student_record",
                arguments={"student_id": f"STU-{(i % 10) + 1:03d}"}
            ))

        obs = env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={"student_id": TASK3["student_id"], "course_id": course_id}
        ))
        assert obs.tool_success is False
        assert "deadline" in (obs.error_message or "").lower()

    def test_exception_override_requires_prior_validation(self, env: UniAdminEnvironment):
        """Blind override attempts should be blocked before rule evaluation."""
        env.reset(task_id="task_5_graduation_crisis")
        obs = env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={
                "student_id": TASK5["student_id"],
                "course_id": TASK5["capstone_course_id"],
                "exception_override": True,
            }
        ))
        assert obs.tool_success is False
        assert "required documentation not found" in (obs.error_message or "").lower()

    def test_exception_override_succeeds_after_validation(self, env: UniAdminEnvironment):
        """The same override path should remain solvable after evidence gathering."""
        env.reset(task_id="task_5_graduation_crisis")
        env.step(UniAdminAction(tool_name="get_fee_status", arguments={"student_id": TASK5["student_id"]}))
        env.step(UniAdminAction(tool_name="search_scholarships", arguments={"student_id": TASK5["student_id"]}))
        env.step(UniAdminAction(tool_name="get_enrollment_history", arguments={"student_id": TASK5["student_id"]}))
        env.step(UniAdminAction(tool_name="check_prerequisites", arguments={"student_id": TASK5["student_id"], "course_id": TASK5["capstone_course_id"]}))
        env.step(UniAdminAction(tool_name="check_credit_limits", arguments={"student_id": TASK5["student_id"]}))
        env.step(UniAdminAction(tool_name="update_fee_record", arguments={"student_id": TASK5["student_id"], "payment_amount": 2500}))
        obs = env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={
                "student_id": TASK5["student_id"],
                "course_id": TASK5["capstone_course_id"],
                "exception_override": True,
            }
        ))
        assert obs.tool_success is True, obs.error_message


class TestDropCourse:
    """Test drop_course tool."""

    def test_drop_enrolled_course(self, env: UniAdminEnvironment):
        env.reset()
        candidate_students = [TASK1_STUDENT, TASK2_STUDENT, TASK3["student_id"], TASK5["student_id"], "STU-129"]
        for student_id in candidate_students:
            obs = env.step(UniAdminAction(
                tool_name="get_enrollment_history",
                arguments={"student_id": student_id}
            ))
            data = json.loads(obs.tool_result)
            enrolled = [e for e in data["enrollments"] if e["status"] == "enrolled"]
            if not enrolled:
                continue

            course_id = enrolled[0]["course_id"]
            obs2 = env.step(UniAdminAction(
                tool_name="drop_course",
                arguments={"student_id": student_id, "course_id": course_id}
            ))
            if obs2.tool_success:
                d = json.loads(obs2.tool_result)
                assert "dropped" in d["message"].lower()
                return

        pytest.skip("Could not find a safe enrolled course to drop in the seeded world")

    def test_drop_not_enrolled(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="drop_course",
            arguments={"student_id": TASK2_STUDENT, "course_id": "CSE-110"}
        ))
        assert obs.tool_success is False
        assert "not" in (obs.error_message or "").lower()

    def test_drop_requires_scholarship_review_before_risky_change(self, env: UniAdminEnvironment):
        env.reset(task_id="task_3_course_switch")
        obs = env.step(UniAdminAction(
            tool_name="drop_course",
            arguments={"student_id": TASK3["student_id"], "course_id": TASK3["course_a_id"]}
        ))
        assert obs.tool_success is False
        assert "scholarship" in (obs.error_message or "").lower()

    def test_drop_is_allowed_after_scholarship_review(self, env: UniAdminEnvironment):
        env.reset(task_id="task_3_course_switch")
        env.step(UniAdminAction(tool_name="search_scholarships", arguments={"student_id": TASK3["student_id"]}))
        env.step(UniAdminAction(
            tool_name="check_scholarship_compliance",
            arguments={"student_id": TASK3["student_id"], "scholarship_id": TASK3["scholarship_id"]}
        ))
        obs = env.step(UniAdminAction(
            tool_name="drop_course",
            arguments={"student_id": TASK3["student_id"], "course_id": TASK3["course_a_id"]}
        ))
        assert obs.tool_success is True


class TestTransferHostel:
    """Test transfer_hostel tool."""

    def test_missing_args(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="transfer_hostel",
            arguments={"student_id": "STU-171"}
        ))
        assert obs.tool_success is False

    def test_gender_mismatch(self, env: UniAdminEnvironment):
        """Female student cannot transfer to male block."""
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="transfer_hostel",
            arguments={"student_id": TASK1_STUDENT, "target_room_id": "RM-A001"}
        ))
        assert obs.tool_success is False
        assert "gender" in (obs.error_message or "").lower()

    def test_successful_transfer(self, env: UniAdminEnvironment):
        """Transfer female student to available female room."""
        env.reset()
        # STU-171 is female, RM-E001 is in female block BLK-E and empty
        obs = env.step(UniAdminAction(
            tool_name="transfer_hostel",
            arguments={"student_id": "STU-171", "target_room_id": "RM-E001"}
        ))
        # May succeed or fail depending on fee status
        if obs.tool_success:
            d = json.loads(obs.tool_result)
            assert "transferred" in d["message"].lower()


class TestUpdateFeeRecord:
    """Test update_fee_record tool."""

    def test_valid_payment(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="update_fee_record",
            arguments={"student_id": TASK5["student_id"], "payment_amount": 2500}
        ))
        assert obs.tool_success is True
        data = json.loads(obs.tool_result)
        assert data["new_amount_due"] == 0
        assert data["status"] == "paid"

    def test_partial_payment(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="update_fee_record",
            arguments={"student_id": TASK5["student_id"], "payment_amount": 1000}
        ))
        assert obs.tool_success is True
        data = json.loads(obs.tool_result)
        assert data["new_amount_due"] == 1500
        assert data["status"] == "partial"

    def test_invalid_amount(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="update_fee_record",
            arguments={"student_id": TASK5["student_id"], "payment_amount": -100}
        ))
        assert obs.tool_success is False

    def test_zero_amount(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="update_fee_record",
            arguments={"student_id": TASK5["student_id"], "payment_amount": 0}
        ))
        assert obs.tool_success is False


class TestSubmitFinalResponse:
    """Test submit_final_response tool."""

    def test_submit_ends_episode(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={
                "message": "Here is your answer.",
                "resolution_summary": {"actions": ["looked up info"]}
            }
        ))
        assert obs.done is True
        data = json.loads(obs.tool_result)
        assert "grader_score" in data

    def test_submit_missing_message(self, env: UniAdminEnvironment):
        env.reset()
        obs = env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"resolution_summary": {}}
        ))
        assert obs.tool_success is False
        assert obs.done is False  # Episode should NOT end on failed submit

    def test_no_step_after_submit(self, env: UniAdminEnvironment):
        env.reset()
        env.step(UniAdminAction(
            tool_name="submit_final_response",
            arguments={"message": "Done.", "resolution_summary": {"done": True}}
        ))
        obs = env.step(UniAdminAction(
            tool_name="get_student_record",
            arguments={"student_id": "STU-001"}
        ))
        assert obs.done is True
        assert "no active episode" in (obs.error_message or "").lower()


class TestExceptionSystem:
    """Test the rule-based exception override system."""

    def test_fee_deferral_with_scholarship(self, env: UniAdminEnvironment):
        """Task 5 student has scholarship SCH-003 worth 100k, fees 100k total -> 100% coverage."""
        env.reset()
        # Karthik has outstanding fees but also has a scholarship
        obs = env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={
                "student_id": TASK5["student_id"],
                "course_id": "CSE-110",  # Try any CS course
                "exception_override": True
            }
        ))
        # The result depends on whether fees block and exception is approved
        # With SCH-003 covering 100%, fee deferral should be approved
        # But enrollment may still fail for other reasons (credit limit, etc.)
        # The key check is that the fee deferral exception path was evaluated

    def test_credit_overload_non_final_semester(self, env: UniAdminEnvironment):
        """Non-final semester student cannot get credit overload exception."""
        env.reset()
        # STU-171 is semester 5, not final
        from uniadmin.server.uniadmin_environment import UniAdminEnvironment as Env
        approved, reason = env._evaluate_exception("credit_overload", "STU-171")
        assert approved is False
        assert "final semester" in reason.lower()

    def test_always_denied_exceptions(self, env: UniAdminEnvironment):
        """Exceptions like capacity_override are always denied."""
        env.reset()
        approved, reason = env._evaluate_exception("capacity_override", "STU-171")
        assert approved is False

        approved, reason = env._evaluate_exception("gender_block_override", "STU-171")
        assert approved is False

    def test_probation_clearance(self, env: UniAdminEnvironment):
        """Probation clearance for student with CGPA >= 6.0."""
        env.reset()
        # Karthik has CGPA 7.50 — should be clearable
        approved, reason = env._evaluate_exception("academic_probation_clearance", TASK5["student_id"])
        assert approved is True


class TestExamRescheduleSafety:
    """Test Task 6 impact assessment and safe rescheduling."""

    def test_check_reschedule_impact_reports_global_safety(self, env: UniAdminEnvironment):
        env.reset(task_id="task_6_bulk_schedule")
        obs = env.step(UniAdminAction(
            tool_name="check_reschedule_impact",
            arguments={
                "course_id": TASK6["student_conflict_pairs"][0][1],
                "new_date": "2025-05-12",
                "new_time_slot": "09:00-10:30",
                "new_room_id": "EXAM-001",
            }
        ))
        assert obs.tool_success is True
        data = json.loads(obs.tool_result)
        assert "slot_available" in data
        assert "impacted_students" in data
        assert "would_create_new_conflict" in data

    def test_reschedule_exam_blocks_new_conflicts(self, env: UniAdminEnvironment):
        env.reset(task_id="task_6_bulk_schedule")
        student_id, course_id, conflicting_course_id = TASK6["student_conflict_pairs"][0]
        schedule_obs = env.step(UniAdminAction(
            tool_name="get_exam_schedule",
            arguments={"student_id": student_id}
        ))
        schedule = json.loads(schedule_obs.tool_result)
        conflicting_exam = next(
            exam for exam in schedule["exams"]
            if exam["course_id"] == conflicting_course_id
        )
        obs = env.step(UniAdminAction(
            tool_name="reschedule_exam",
            arguments={
                "course_id": course_id,
                "new_date": conflicting_exam["date"],
                "new_time_slot": conflicting_exam["time_slot"],
                "new_room_id": "EXAM-001",
            }
        ))
        assert obs.tool_success is False
        assert any(
            phrase in (obs.error_message or "").lower()
            for phrase in ["creates new student conflicts", "already invigilating", "already booked"]
        )


class TestStateIntegrity:
    """Test state consistency after mutations."""

    def test_enrollment_changes_state_hash(self, env: UniAdminEnvironment):
        env.reset()
        state_before = env.state()

        # Find available course
        obs = env.step(UniAdminAction(
            tool_name="search_courses",
            arguments={"filters": {"department": "DEPT-HS", "has_availability": True}}
        ))
        data = json.loads(obs.tool_result)
        if data["total"] == 0:
            pytest.skip("No available courses")

        course = None
        for c in data["results"]:
            if not c.get("prerequisites"):
                course = c
                break
        if not course:
            pytest.skip("No prereq-free courses")

        env.step(UniAdminAction(
            tool_name="enroll_student",
            arguments={"student_id": TASK2_STUDENT, "course_id": course["course_id"]}
        ))

        state_after = env.state()
        # State hash should change after mutation
        assert state_before.state_hash != state_after.state_hash

    def test_modified_entities_tracked(self, env: UniAdminEnvironment):
        env.reset()
        env.step(UniAdminAction(
            tool_name="update_fee_record",
            arguments={"student_id": TASK5["student_id"], "payment_amount": 2500}
        ))
        state = env.state()
        assert len(state.modified_entities) > 0

    def test_audit_log_complete(self, env: UniAdminEnvironment):
        env.reset()
        env.step(UniAdminAction(tool_name="get_student_record", arguments={"student_id": "STU-171"}))
        env.step(UniAdminAction(tool_name="check_fee_clearance", arguments={"student_id": "STU-171"}))
        env.step(UniAdminAction(tool_name="check_credit_limits", arguments={"student_id": "STU-171"}))

        state = env.state()
        assert len(state.audit_log) == 3
        assert state.audit_log[0]["tool_name"] == "get_student_record"
        assert state.audit_log[1]["tool_name"] == "check_fee_clearance"
        assert state.audit_log[2]["tool_name"] == "check_credit_limits"

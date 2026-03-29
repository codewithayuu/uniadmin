"""Grader for Task 3: Course Switch Under Deadline."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uniadmin.graders.base_grader import (
    compute_rubric_score,
    count_duplicate_calls,
    get_step_of_tool_call,
    tool_was_called,
    tool_succeeded,
)


def grade_task_3(
    audit_log: List[Dict[str, Any]],
    world_state: Dict[str, Any],
    modified_entities: Dict[str, Any],
    task_refs: Dict[str, Any],
    final_response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Grade Task 3: Course Switch Under Deadline."""
    student_id = task_refs.get("student_id", "STU-088")
    course_a_id = task_refs.get("course_a_id", "")
    course_b_id = task_refs.get("course_b_id", "")
    scholarship_id = task_refs.get("scholarship_id", "SCH-001")

    # Criterion 1: Checked prerequisites for target course
    checked_prereqs = tool_was_called(
        audit_log, "check_prerequisites",
        {"student_id": student_id, "course_id": course_b_id}
    ) if course_b_id else tool_was_called(audit_log, "check_prerequisites")

    # Criterion 2: Checked seat availability for target
    checked_seats = tool_was_called(
        audit_log, "check_seat_availability",
        {"course_id": course_b_id}
    ) if course_b_id else tool_was_called(audit_log, "check_seat_availability")

    # Criterion 3: Checked credit limits
    checked_credits = tool_was_called(
        audit_log, "check_credit_limits",
        {"student_id": student_id}
    )

    # Criterion 4: Checked fee differential
    checked_fees = (
        tool_was_called(audit_log, "check_fee_clearance", {"student_id": student_id})
        or tool_was_called(audit_log, "get_fee_status", {"student_id": student_id})
    )

    # Criterion 5: Checked scholarship compliance
    checked_scholarship = tool_was_called(
        audit_log, "check_scholarship_compliance",
        {"student_id": student_id}
    ) or tool_was_called(
        audit_log, "search_scholarships",
        {"student_id": student_id}
    )

    # Criterion 6: Checked academic probation
    checked_probation = (
        tool_was_called(audit_log, "get_student_record", {"student_id": student_id})
        or tool_was_called(audit_log, "search_regulations", {"keyword": "probation"})
    )

    # Criterion 7: Successfully dropped original course
    dropped_original = False
    drop_step = None
    for entry in audit_log:
        if (entry.get("tool_name") == "drop_course"
                and entry.get("success")
                and entry.get("arguments", {}).get("student_id") == student_id):
            dropped_course = entry["arguments"].get("course_id", "")
            if course_a_id and dropped_course == course_a_id:
                dropped_original = True
                drop_step = entry.get("step")
            elif not course_a_id:
                dropped_original = True
                drop_step = entry.get("step")
            break

    # Criterion 8: Successfully enrolled in target course
    enrolled_target = False
    enroll_step = None
    for entry in audit_log:
        if (entry.get("tool_name") == "enroll_student"
                and entry.get("success")
                and entry.get("arguments", {}).get("student_id") == student_id):
            enrolled_course = entry["arguments"].get("course_id", "")
            if course_b_id and enrolled_course == course_b_id:
                enrolled_target = True
                enroll_step = entry.get("step")
            elif not course_b_id:
                enrolled_target = True
                enroll_step = entry.get("step")
            break

    # Criterion 9: Completed before deadline
    completed_before_deadline = False
    deadline = 16
    if dropped_original and enrolled_target:
        if (drop_step is not None and drop_step <= deadline
                and enroll_step is not None and enroll_step <= deadline):
            completed_before_deadline = True

    # Criterion 10: Called submit
    called_submit = tool_succeeded(audit_log, "submit_final_response")

    criteria = {
        "checked_prerequisites": (checked_prereqs, 0.10),
        "checked_seat_availability": (checked_seats, 0.10),
        "checked_credit_limits": (checked_credits, 0.10),
        "checked_fee_differential": (checked_fees, 0.10),
        "checked_scholarship_compliance": (checked_scholarship, 0.10),
        "checked_academic_probation": (checked_probation, 0.05),
        "dropped_original": (dropped_original, 0.15),
        "enrolled_target": (enrolled_target, 0.15),
        "completed_before_deadline": (completed_before_deadline, 0.10),
        "called_submit": (called_submit, 0.05),
    }

    # Penalties
    penalties: List[tuple] = []

    # State corruption
    if enrolled_target and not dropped_original:
        penalties.append(("state_corruption_enroll_without_drop", -0.30))
    elif dropped_original and not enrolled_target:
        penalties.append(("state_corruption_drop_without_enroll", -0.30))

    # Redundant tool calls
    dup_count = count_duplicate_calls(audit_log)
    for i in range(dup_count):
        penalties.append((f"redundant_tool_call_{i+1}", -0.10))

    return compute_rubric_score(criteria, penalties)

"""Grader for Task 4: Concurrent Enrollment Conflict."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uniadmin.graders.base_grader import compute_rubric_score, tool_was_called, tool_succeeded


def grade_task_4(
    audit_log: List[Dict[str, Any]],
    world_state: Dict[str, Any],
    modified_entities: Dict[str, Any],
    task_refs: Dict[str, Any],
    final_response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    stu_x = task_refs.get("student_x_id", "STU-150")
    stu_y = task_refs.get("student_y_id", "STU-151")
    course_id = task_refs.get("course_id", "")
    scholarship_id = task_refs.get("scholarship_id", "SCH-002")

    # 1. Identified seat availability
    identified_seats = tool_was_called(audit_log, "check_seat_availability", {"course_id": course_id}) if course_id else tool_was_called(audit_log, "check_seat_availability")

    # 2. Checked student X eligibility
    checked_x = (
        tool_was_called(audit_log, "get_student_record", {"student_id": stu_x})
        or tool_was_called(audit_log, "check_prerequisites", {"student_id": stu_x})
        or tool_was_called(audit_log, "check_fee_clearance", {"student_id": stu_x})
    )

    # 3. Checked student Y eligibility
    checked_y = (
        tool_was_called(audit_log, "get_student_record", {"student_id": stu_y})
        or tool_was_called(audit_log, "check_prerequisites", {"student_id": stu_y})
        or tool_was_called(audit_log, "check_fee_clearance", {"student_id": stu_y})
    )

    # 4. Discovered scholarship dependency for X
    discovered_scholarship = (
        tool_was_called(audit_log, "search_scholarships", {"student_id": stu_x})
        or tool_was_called(audit_log, "check_scholarship_compliance", {"student_id": stu_x})
    )

    # 5. Correctly prioritized X over Y
    enrolled_x = False
    enrolled_y = False
    for entry in audit_log:
        if entry.get("tool_name") == "enroll_student" and entry.get("success"):
            args = entry.get("arguments", {})
            if args.get("student_id") == stu_x and (not course_id or args.get("course_id") == course_id):
                enrolled_x = True
            if args.get("student_id") == stu_y and (not course_id or args.get("course_id") == course_id):
                enrolled_y = True

    correctly_prioritized = enrolled_x and not enrolled_y

    # 6. Enrolled Student X
    # this is already computed above

    # 7. Denied Student Y with justification
    denied_y = False
    if final_response:
        msg = (final_response.get("message", "") + str(final_response.get("resolution_summary", ""))).lower()
        if stu_y.lower() in msg and any(w in msg for w in ["denied", "cannot", "not enrolled", "rejected", "unable", "priority", "scholarship"]):
            denied_y = True
    if enrolled_x and not enrolled_y:
        denied_y = True

    # 8. Suggested alternatives for Y
    suggested_alt = False
    if final_response:
        msg = (final_response.get("message", "") + str(final_response.get("resolution_summary", ""))).lower()
        if any(w in msg for w in ["alternative", "other course", "suggest", "instead", "option"]):
            suggested_alt = True
    # Also accept if agent searched for other courses
    for entry in audit_log:
        if entry.get("tool_name") == "search_courses" and entry.get("success"):
            suggested_alt = True
            break

    # 9. Called submit
    called_submit = tool_succeeded(audit_log, "submit_final_response")

    criteria = {
        "identified_seat_availability": (identified_seats, 0.10),
        "checked_student_x_eligibility": (checked_x, 0.10),
        "checked_student_y_eligibility": (checked_y, 0.10),
        "discovered_scholarship_dependency": (discovered_scholarship, 0.15),
        "correctly_prioritized_x": (correctly_prioritized, 0.15),
        "enrolled_student_x": (enrolled_x, 0.10),
        "denied_student_y": (denied_y, 0.10),
        "suggested_alternatives": (suggested_alt, 0.10),
        "called_submit": (called_submit, 0.10),
    }

    penalties: List[tuple] = []
    if enrolled_x and enrolled_y:
        penalties.append(("enrolled_both", -0.40))
    if enrolled_y and not enrolled_x:
        penalties.append(("enrolled_y_over_x", -0.30))

    return compute_rubric_score(criteria, penalties)

"""Grader for Task 5: Graduation Crisis with Dynamic Regulation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uniadmin.graders.base_grader import compute_rubric_score, tool_succeeded


def grade_task_5(
    audit_log: List[Dict[str, Any]],
    world_state: Dict[str, Any],
    modified_entities: Dict[str, Any],
    task_refs: Dict[str, Any],
    final_response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    stu_id = task_refs.get("student_id", "STU-042")
    capstone_course_id = task_refs.get("capstone_course_id", "")

    def succeeded(tool_name: str, **filters: Any) -> bool:
        return tool_succeeded(audit_log, tool_name, filters or None)

    discovered_credits = succeeded("check_credit_limits", student_id=stu_id)
    discovered_fees = (
        succeeded("get_fee_status", student_id=stu_id)
        or succeeded("check_fee_clearance", student_id=stu_id)
    )
    discovered_prereq = succeeded("check_prerequisites", student_id=stu_id, course_id=capstone_course_id)
    discovered_scholarship = (
        succeeded("search_scholarships", student_id=stu_id)
        or succeeded("check_scholarship_compliance", student_id=stu_id)
    )
    discovered_hostel = succeeded("get_hostel_details", student_id=stu_id)
    discovered_probation = succeeded("get_student_record", student_id=stu_id)

    student = next((s for s in world_state.get("students", []) if s["student_id"] == stu_id), None)
    fee_record = next((f for f in world_state.get("fee_records", []) if f["student_id"] == stu_id), None)
    capstone_enrollment = next(
        (
            e for e in world_state.get("enrollments", [])
            if e["student_id"] == stu_id and e["course_id"] == capstone_course_id and e["status"] == "enrolled"
        ),
        None,
    )

    used_dynamic_reg = False
    for entry in audit_log:
        if entry.get("tool_name") != "enroll_student" or not entry.get("success"):
            continue
        args = entry.get("arguments", {})
        if args.get("student_id") != stu_id or args.get("course_id") != capstone_course_id:
            continue
        if args.get("exception_override"):
            used_dynamic_reg = True
            break

    processed_fee = bool(fee_record and fee_record.get("amount_due", 1) == 0)
    applied_waiver = capstone_enrollment is not None and succeeded(
        "enroll_student", student_id=stu_id, course_id=capstone_course_id, exception_override=True
    )
    initiated_checkout = bool(modified_entities.get(f"{stu_id}_checkout", {}).get("checkout_initiated"))
    cleared_probation = bool(student and student.get("academic_status") == "active")

    blockers_discovered = sum(
        [
            discovered_credits,
            discovered_fees,
            discovered_prereq,
            discovered_scholarship,
            discovered_hostel,
            discovered_probation,
        ]
    )
    all_resolved = all([processed_fee, applied_waiver, initiated_checkout, cleared_probation])
    called_submit = succeeded("submit_final_response")
    submit_has_content = bool(final_response and final_response.get("resolution_summary"))

    criteria = {
        "discovered_missing_credits": (discovered_credits, 0.05),
        "discovered_unpaid_fees": (discovered_fees, 0.05),
        "discovered_prerequisite_gap": (discovered_prereq, 0.05),
        "discovered_scholarship_constraint": (discovered_scholarship, 0.05),
        "discovered_hostel_checkout": (discovered_hostel, 0.05),
        "discovered_probation_flag": (discovered_probation, 0.05),
        "used_dynamic_regulation": (used_dynamic_reg, 0.10),
        "processed_fee_payment": (processed_fee, 0.10),
        "applied_prerequisite_waiver": (applied_waiver, 0.15),
        "initiated_hostel_checkout": (initiated_checkout, 0.10),
        "cleared_probation": (cleared_probation, 0.10),
        "all_blockers_discovered": (blockers_discovered == 6, 0.05),
        "all_blockers_resolved": (all_resolved, 0.10),
        "called_submit_with_resolution": (called_submit and submit_has_content, 0.10),
    }

    penalties: List[tuple] = []
    if capstone_enrollment is None and succeeded("enroll_student", student_id=stu_id, course_id=capstone_course_id):
        penalties.append(("enrollment_not_persisted", -0.20))

    return compute_rubric_score(criteria, penalties)

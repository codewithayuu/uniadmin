from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from uniadmin.graders.base_grader import compute_rubric_score, tool_was_called, tool_succeeded


def grade_task_1(
    audit_log: List[Dict[str, Any]],
    world_state: Dict[str, Any],
    modified_entities: Dict[str, Any],
    task_refs: Dict[str, Any],
    final_response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    student_id = task_refs.get("student_id", "STU-171")

    # Criterion 1: Retrieved student's enrollment
    retrieved_enrollment = (
        tool_was_called(audit_log, "get_enrollment_history", {"student_id": student_id})
        or tool_was_called(audit_log, "get_student_record", {"student_id": student_id})
    )

    # Criterion 2: Searched CS electives for correct semester
    searched_cs = False
    searched_pages = set()
    expected_total_pages = 1
    for entry in audit_log:
        if entry.get("tool_name") == "search_courses" and entry.get("success"):
            args = entry.get("arguments", {})
            filters = args.get("filters", {})
            if filters.get("department") == "DEPT-CS":
                searched_cs = True
                searched_pages.add(int(args.get("page", 1) or 1))
                try:
                    payload = json.loads(entry.get("result_summary") or "{}")
                    expected_total_pages = max(
                        expected_total_pages,
                        int(payload.get("total_pages", 1) or 1),
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass
            query = args.get("query", "").lower()
            if "cs" in query or "computer" in query:
                searched_cs = True
                searched_pages.add(int(args.get("page", 1) or 1))
                try:
                    payload = json.loads(entry.get("result_summary") or "{}")
                    expected_total_pages = max(
                        expected_total_pages,
                        int(payload.get("total_pages", 1) or 1),
                    )
                except (TypeError, ValueError, json.JSONDecodeError):
                    pass

    # Criterion 3: Checked schedule conflicts
    checked_conflicts = False
    got_enrollment = tool_was_called(audit_log, "get_enrollment_history", {"student_id": student_id})
    got_course_details_count = sum(
        1 for entry in audit_log
        if entry.get("tool_name") == "get_course_details" and entry.get("success")
    )
    got_exam_schedule = tool_was_called(audit_log, "get_exam_schedule", {"student_id": student_id})

    if got_enrollment and (got_course_details_count >= 1 or got_exam_schedule):
        checked_conflicts = True
    if tool_was_called(audit_log, "get_student_record", {"student_id": student_id}) and searched_cs:
        checked_conflicts = True

    # Criterion 4: Checked credit limit
    checked_credit = tool_was_called(audit_log, "check_credit_limits", {"student_id": student_id})

    # Criterion 5: Provided a concrete course list tied to real course IDs
    provided_list = False
    covered_all_pages = expected_total_pages <= 1 or searched_pages >= set(range(1, expected_total_pages + 1))
    if final_response:
        summary = final_response.get("resolution_summary", {})
        candidates = (
            summary.get("courses")
            or summary.get("recommended")
            or summary.get("available_courses")
            or []
        )
        valid_course_ids = {c["course_id"] for c in world_state.get("courses", [])}
        extracted_ids = set()
        if isinstance(candidates, list):
            extracted_ids.update(
                item for item in candidates
                if isinstance(item, str) and item in valid_course_ids
            )
        elif isinstance(candidates, str):
            extracted_ids.update(re.findall(r"\b[A-Z]{2,4}-\d{3}\b", candidates))

        if not extracted_ids:
            message = final_response.get("message", "")
            extracted_ids.update(re.findall(r"\b[A-Z]{2,4}-\d{3}\b", message))

        extracted_ids = {course_id for course_id in extracted_ids if course_id in valid_course_ids}
        if extracted_ids:
            provided_list = covered_all_pages

    # Criterion 6: Called submit_final_response
    called_submit = tool_succeeded(audit_log, "submit_final_response")

    criteria = {
        "retrieved_student_enrollment": (retrieved_enrollment, 0.15),
        "searched_cs_electives": (searched_cs, 0.15),
        "checked_schedule_conflicts": (checked_conflicts, 0.20),
        "checked_credit_limit": (checked_credit, 0.15),
        "provided_accurate_list": (provided_list, 0.20),
        "called_submit": (called_submit, 0.15),
    }

    penalties: List[tuple] = []
    return compute_rubric_score(criteria, penalties)

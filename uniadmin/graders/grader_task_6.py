"""Grader for Task 6: Bulk Exam Schedule Conflict Resolution."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from uniadmin.graders.base_grader import compute_rubric_score, tool_succeeded


def _student_exam_entries(world_state: Dict[str, Any], student_id: str) -> List[Dict[str, Any]]:
    enrolled = {
        e["course_id"]
        for e in world_state.get("enrollments", [])
        if e["student_id"] == student_id and e["status"] == "enrolled"
    }
    return [exam for exam in world_state.get("exam_schedule", []) if exam["course_id"] in enrolled]


def _has_same_slot_conflict(entries: List[Dict[str, Any]]) -> bool:
    seen: Set[Tuple[str, str]] = set()
    for exam in entries:
        key = (exam["date"], exam["time_slot"])
        if key in seen:
            return True
        seen.add(key)
    return False


def grade_task_6(
    audit_log: List[Dict[str, Any]],
    world_state: Dict[str, Any],
    modified_entities: Dict[str, Any],
    task_refs: Dict[str, Any],
    final_response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    conflict_pairs = task_refs.get("student_conflict_pairs", [])
    conflict_students = {pair[0] for pair in conflict_pairs}
    rescheduled_exam_ids = {
        exam_id for exam_id, change in modified_entities.items()
        if exam_id.startswith("EXM-") and isinstance(change, dict)
    }

    identified_all = all(
        tool_succeeded(audit_log, "get_exam_schedule", {"student_id": student_id})
        for student_id in conflict_students
    )
    checked_faculty = (
        tool_succeeded(audit_log, "search_faculty")
        or tool_succeeded(audit_log, "check_reschedule_impact")
        or tool_succeeded(audit_log, "find_exam_alternatives")
    )
    checked_rooms = any(
        entry.get("tool_name") in {"find_exam_alternatives", "check_reschedule_impact"}
        and entry.get("success")
        for entry in audit_log
    )
    used_alternative_search = checked_rooms

    resolved_students = 0
    no_same_day_violations = True
    for student_id in conflict_students:
        entries = _student_exam_entries(world_state, student_id)
        if not _has_same_slot_conflict(entries):
            resolved_students += 1
        seen_dates: Set[str] = set()
        for exam in entries:
            if exam["date"] in seen_dates:
                no_same_day_violations = False
                break
            seen_dates.add(exam["date"])

    resolved_2 = resolved_students >= 2
    resolved_4 = resolved_students >= 4
    resolved_6 = resolved_students >= 6
    resolved_all = resolved_students == len(conflict_students)
    called_submit = tool_succeeded(audit_log, "submit_final_response")
    submit_has_content = bool(final_response and final_response.get("resolution_summary"))

    criteria = {
        "identified_all_conflicts": (identified_all, 0.15),
        "checked_room_availability": (checked_rooms, 0.10),
        "checked_faculty_availability": (checked_faculty, 0.10),
        "used_exam_alternative_search": (used_alternative_search, 0.10),
        "resolved_2_plus": (resolved_2, 0.10),
        "resolved_4_plus": (resolved_4, 0.10),
        "resolved_6_plus": (resolved_6, 0.10),
        "resolved_all_8": (resolved_all, 0.10),
        "no_same_day_violations": (no_same_day_violations, 0.05),
        "called_submit": (called_submit and submit_has_content, 0.10),
    }

    penalties: List[tuple] = []
    if not rescheduled_exam_ids:
        penalties.append(("no_exam_mutations", -0.30))

    return compute_rubric_score(criteria, penalties)

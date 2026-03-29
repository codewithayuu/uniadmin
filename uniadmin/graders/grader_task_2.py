"""Grader for Task 2: Hostel Room Allocation."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uniadmin.graders.base_grader import compute_rubric_score, tool_was_called, tool_succeeded


def grade_task_2(
    audit_log: List[Dict[str, Any]],
    world_state: Dict[str, Any],
    modified_entities: Dict[str, Any],
    task_refs: Dict[str, Any],
    final_response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Grade Task 2: Hostel Room Allocation."""
    student_id = task_refs.get("student_id", "STU-201")

    # Criterion 1: Retrieved student record
    retrieved_student = tool_was_called(audit_log, "get_student_record", {"student_id": student_id})

    # Criterion 2: Checked gender-appropriate blocks
    checked_gender = (
        tool_was_called(audit_log, "get_student_record", {"student_id": student_id})
        and tool_was_called(audit_log, "get_hostel_details", {"student_id": student_id})
    ) or tool_was_called(audit_log, "search_regulations", {"applicable_to": "hostel"})

    # Criterion 3: Checked room availability
    checked_availability = tool_was_called(audit_log, "get_hostel_details", {"student_id": student_id})

    # Criterion 4: Checked fee clearance
    checked_fee = (
        tool_was_called(audit_log, "check_fee_clearance", {"student_id": student_id})
        or tool_was_called(audit_log, "get_fee_status", {"student_id": student_id})
    )

    # Criterion 5: Allocated correct room
    allocated_room = False
    wrong_gender = False
    full_room = False

    for entry in audit_log:
        if entry.get("tool_name") == "transfer_hostel" and entry.get("success"):
            args = entry.get("arguments", {})
            if args.get("student_id") == student_id:
                allocated_room = True
                target_room_id = args.get("target_room_id", "")
                student = None
                for s in world_state.get("students", []):
                    if s["student_id"] == student_id:
                        student = s
                        break
                if student:
                    student_gender = student.get("gender", "")
                    for room in world_state.get("hostel_rooms", []):
                        if room["room_id"] == target_room_id:
                            block_id = room["block_id"]
                            for block in world_state.get("hostel_blocks", []):
                                if block["block_id"] == block_id:
                                    if block.get("gender_restriction") != student_gender:
                                        wrong_gender = True
                                    break
                            break
                break

    for entry in audit_log:
        if entry.get("tool_name") == "transfer_hostel" and not entry.get("success"):
            result = entry.get("result_summary", "").lower()
            if "gender" in result:
                wrong_gender = True
            if "full" in result or "capacity" in result:
                full_room = True

    # Criterion 6: Student record updated
    student_updated = False
    if allocated_room:
        for s in world_state.get("students", []):
            if s["student_id"] == student_id and s.get("hostel_id"):
                student_updated = True
                break
        if student_id in modified_entities:
            if modified_entities[student_id].get("hostel_id"):
                student_updated = True

    # Criterion 7: Called submit
    called_submit = tool_succeeded(audit_log, "submit_final_response")

    criteria = {
        "retrieved_student_record": (retrieved_student, 0.10),
        "checked_gender_blocks": (checked_gender, 0.15),
        "checked_room_availability": (checked_availability, 0.15),
        "checked_fee_clearance": (checked_fee, 0.15),
        "allocated_correct_room": (allocated_room, 0.20),
        "updated_student_record": (student_updated, 0.10),
        "called_submit": (called_submit, 0.15),
    }

    penalties: List[tuple] = []
    if wrong_gender:
        penalties.append(("wrong_gender_block", -0.20))
    if full_room:
        penalties.append(("full_room_allocation", -0.15))

    return compute_rubric_score(criteria, penalties)

from __future__ import annotations

import hashlib
import json
import time
from typing import Any, Dict, List, Optional, Set, Tuple

from uniadmin.models import (
    PENALTY_DUPLICATE_CALL,
    PENALTY_STATE_CORRUPTION,
    PENALTY_TOOL_ERROR,
    PENALTY_DEADLINE_EXCEEDED,
    REWARD_NEW_INFO,
    REWARD_TOOL_SUCCESS,
    TASK_CONFIGS,
    TOOL_NAMES,
    DEFAULT_CREDIT_LIMIT,
    ELEVATED_CREDIT_LIMIT,
    UniAdminAction,
    UniAdminObservation,
    UniAdminState,
)
from uniadmin.world.loader import load_world_copy, load_policies, get_task_entity_refs
from uniadmin.graders.dispatcher import dispatch_grader


# Grade ordering for comparison
GRADE_ORDER = {
    "A+": 12, "A": 11, "A-": 10, "B+": 9, "B": 8, "B-": 7,
    "C+": 6, "C": 5, "C-": 4, "D": 3, "F": 0, "W": -1,
}


def _grade_gte(grade_a: str, grade_b: str) -> bool:
    """Check if grade_a is greater than or equal to grade_b."""
    return GRADE_ORDER.get(grade_a, -2) >= GRADE_ORDER.get(grade_b, -2)


class UniAdminEnvironment:


    def __init__(self) -> None:

        self._world: Dict[str, Any] = {}
        self._policies: Dict[str, Any] = {}
        self._task_refs: Dict[str, Any] = {}
        self._task_id: str = ""
        self._task_config: Dict[str, Any] = {}
        self._step_count: int = 0
        self._episode_active: bool = False
        self._done: bool = False

        # Audit and tracking
        self._audit_log: List[Dict[str, Any]] = []
        self._modified_entities: Dict[str, Any] = {}
        self._retrieved_entity_ids: Set[str] = set()
        self._call_history: List[Tuple[str, str]] = []  # (tool_name, args_hash)
        self._pending_notifications: List[str] = []
        self._fired_notification_ids: Set[str] = set()
        self._cumulative_step_reward: float = 0.0

        # Dynamic state flags
        self._credit_limit_elevated: bool = False
        self._deadline_passed: bool = False
        self._hostel_checkout_initiated: Dict[str, bool] = {}
        self._probation_cleared: Dict[str, bool] = {}
        self._state_hash_cache: Optional[str] = None
        self._state_hash_dirty: bool = True

        # Grader result cache (set after submit_final_response)
        self._grader_result: Optional[Dict[str, Any]] = None
        self._final_response_data: Optional[Dict[str, Any]] = None

        # Tool handler dispatch table
        self._tool_handlers: Dict[str, Any] = {
            # Search tools (1-5)
            "search_students": self._tool_search_students,
            "search_courses": self._tool_search_courses,
            "search_faculty": self._tool_search_faculty,
            "search_regulations": self._tool_search_regulations,
            "search_scholarships": self._tool_search_scholarships,
            # Retrieve tools (6-11)
            "get_student_record": self._tool_get_student_record,
            "get_course_details": self._tool_get_course_details,
            "get_enrollment_history": self._tool_get_enrollment_history,
            "get_fee_status": self._tool_get_fee_status,
            "get_hostel_details": self._tool_get_hostel_details,
            "get_exam_schedule": self._tool_get_exam_schedule,
            # Validate tools (12-16)
            "check_prerequisites": self._tool_check_prerequisites,
            "check_credit_limits": self._tool_check_credit_limits,
            "check_seat_availability": self._tool_check_seat_availability,
            "check_fee_clearance": self._tool_check_fee_clearance,
            "check_scholarship_compliance": self._tool_check_scholarship_compliance,
            # Modify tools (17-20)
            "enroll_student": self._tool_enroll_student,
            "drop_course": self._tool_drop_course,
            "transfer_hostel": self._tool_transfer_hostel,
            "update_fee_record": self._tool_update_fee_record,
            "initiate_hostel_checkout": self._tool_initiate_hostel_checkout,
            "clear_probation_hold": self._tool_clear_probation_hold,
            "find_exam_alternatives": self._tool_find_exam_alternatives,
            "check_reschedule_impact": self._tool_check_reschedule_impact,
            "reschedule_exam": self._tool_reschedule_exam,
            # Special
            "submit_final_response": self._tool_submit_final_response,
        }

    def reset(self, task_id: Optional[str] = None) -> UniAdminObservation:
        # Default task
        if task_id is None:
            task_id = "task_1_course_inquiry"

        if task_id not in TASK_CONFIGS:
            # Return error observation for invalid task_id
            return UniAdminObservation(
                done=True,
                reward=0.0,
                metadata={"error": f"Invalid task_id: {task_id}"},
                task_id=task_id,
                task_description=f"ERROR: Unknown task '{task_id}'",
                tool_result="",
                tool_success=False,
                error_message=f"Invalid task_id: {task_id}. Valid tasks: {list(TASK_CONFIGS.keys())}",
                current_step=0,
            )

        # Load fresh world state
        self._world = load_world_copy()
        self._policies = load_policies()
        self._task_refs = get_task_entity_refs()

        # Set task
        self._task_id = task_id
        self._task_config = TASK_CONFIGS[task_id]

        # Reset episode state
        self._step_count = 0
        self._episode_active = True
        self._done = False
        self._audit_log = []
        self._modified_entities = {}
        self._retrieved_entity_ids = set()
        self._call_history = []
        self._pending_notifications = []
        self._fired_notification_ids = set()
        self._cumulative_step_reward = 0.0
        self._credit_limit_elevated = False
        self._deadline_passed = False
        self._hostel_checkout_initiated = {}
        self._probation_cleared = {}
        self._grader_result = None
        self._final_response_data = None
        self._state_hash_cache = None
        self._state_hash_dirty = True

        # Build task description with context
        task_description = self._build_task_description()

        # Compute steps remaining
        deadline = self._task_config.get("deadline_step")
        steps_remaining = None
        if deadline is not None:
            steps_remaining = deadline - self._step_count
        task_ref_key_map = {
            "task_1_course_inquiry": "task_1",
            "task_2_hostel_allocation": "task_2",
            "task_3_course_switch": "task_3",
            "task_4_concurrent_conflict": "task_4",
            "task_5_graduation_crisis": "task_5",
            "task_6_bulk_schedule": "task_6",
        }
        task_refs = dict(self._task_refs.get(task_ref_key_map.get(self._task_id, ""), {}))

        return UniAdminObservation(
            done=False,
            reward=None,
            metadata={
                "episode_started": True,
                "task_difficulty": self._task_config["difficulty"],
                "task_refs": task_refs,
            },
            task_id=self._task_id,
            task_description=task_description,
            tool_result="",
            tool_success=True,
            error_message=None,
            current_step=0,
            steps_remaining=steps_remaining,
            notifications=[],
            available_tools=list(TOOL_NAMES),
        )

    def step(self, action: UniAdminAction) -> UniAdminObservation:
        # Check episode is active
        if not self._episode_active or self._done:
            return UniAdminObservation(
                done=True,
                reward=0.0,
                metadata={"error": "No active episode. Call reset() first."},
                task_id=self._task_id,
                task_description="",
                tool_result="",
                tool_success=False,
                error_message="No active episode. Call reset() first.",
                current_step=self._step_count,
            )

        self._step_count += 1
        step_reward = 0.0

        # Check if max steps exceeded
        max_steps = self._task_config.get("max_steps", 50)
        if self._step_count > max_steps:
            self._done = True
            self._episode_active = False
            # Trigger grader with whatever state we have
            grader_score = self._run_grader()
            return UniAdminObservation(
                done=True,
                reward=grader_score,
                metadata={"reason": "max_steps_exceeded", "grader_result": self._grader_result},
                task_id=self._task_id,
                task_description=self._task_config["description"],
                tool_result="Maximum steps exceeded. Episode ended automatically.",
                tool_success=False,
                error_message="Maximum steps exceeded.",
                current_step=self._step_count,
                steps_remaining=0,
                notifications=[],
                available_tools=list(TOOL_NAMES),
            )

        # Update deadline status (Task 3)
        deadline = self._task_config.get("deadline_step")
        if deadline is not None and self._step_count > deadline:
            if not self._deadline_passed:
                self._deadline_passed = True
                step_reward += PENALTY_DEADLINE_EXCEEDED

        # Validate tool_name
        tool_name = action.tool_name
        if tool_name not in self._tool_handlers:
            step_reward += PENALTY_TOOL_ERROR
            self._cumulative_step_reward += step_reward
            self._log_audit(tool_name, action.arguments, "Invalid tool name", False)
            return self._make_observation(
                tool_result=f"Invalid tool name: '{tool_name}'. Available tools: {TOOL_NAMES}",
                tool_success=False,
                error_message=f"Invalid tool name: '{tool_name}'",
                step_reward=step_reward,
            )

        # Check for duplicate call
        args_hash = hashlib.md5(
            json.dumps(action.arguments, sort_keys=True, default=str).encode()
        ).hexdigest()
        call_signature = (tool_name, args_hash)
        is_duplicate = call_signature in self._call_history
        self._call_history.append(call_signature)

        if is_duplicate:
            step_reward += PENALTY_DUPLICATE_CALL

        # Execute tool handler
        try:
            result = self._tool_handlers[tool_name](action.arguments)
        except Exception as e:
            step_reward += PENALTY_TOOL_ERROR
            self._cumulative_step_reward += step_reward
            self._log_audit(tool_name, action.arguments, f"Internal error: {str(e)}", False)
            return self._make_observation(
                tool_result=f"Internal error executing '{tool_name}': {str(e)}",
                tool_success=False,
                error_message=str(e),
                step_reward=step_reward,
            )

        # Unpack result
        tool_success = result.get("success", False)
        tool_result_str = json.dumps(result.get("data", {}), default=str, ensure_ascii=False)
        error_msg = result.get("error", None)
        new_entity_ids = result.get("entity_ids", set())
        metadata_extra = result.get("metadata", {})
        if tool_success and result.get("state_diff") is not None:
            self._state_hash_dirty = True

        # Compute rewards
        if tool_success:
            step_reward += REWARD_TOOL_SUCCESS
            # New information bonus
            new_ids = new_entity_ids - self._retrieved_entity_ids
            if new_ids:
                step_reward += REWARD_NEW_INFO
                self._retrieved_entity_ids.update(new_ids)
        else:
            if not is_duplicate:
                step_reward += PENALTY_TOOL_ERROR

        self._cumulative_step_reward += step_reward

        if tool_name != "submit_final_response":
            self._log_audit(tool_name, action.arguments,
                            tool_result_str[:500], tool_success,
                            state_diff=result.get("state_diff"))

        # Check notification triggers
        self._check_notification_triggers(tool_name, action.arguments, result)

        # Drain pending notifications
        notifications = list(self._pending_notifications)
        self._pending_notifications = []

        # Check if episode ended (submit_final_response sets self._done)
        obs_metadata = {"step_reward": step_reward}
        obs_metadata.update(metadata_extra)
        if self._grader_result:
            obs_metadata["grader_result"] = self._grader_result

        return self._make_observation(
            tool_result=tool_result_str,
            tool_success=tool_success,
            error_message=error_msg,
            step_reward=step_reward if not self._done else (self._grader_result or {}).get("score", 0.0),
            notifications=notifications,
            metadata_extra=obs_metadata,
        )

    def state(self) -> UniAdminState:
        return UniAdminState(
            task_id=self._task_id,
            step_count=self._step_count,
            modified_entities=dict(self._modified_entities),
            state_hash=self._compute_state_hash(),
            audit_log=list(self._audit_log),
            episode_active=self._episode_active,
        )

    def close(self) -> None:
        """Close the environment and clean up resources."""
        self._world = {}
        self._policies = {}
        self._task_refs = {}
        self._audit_log = []
        self._modified_entities = {}
        self._episode_active = False
        self._done = True
        self._state_hash_cache = None
        self._state_hash_dirty = True

    def _build_task_description(self) -> str:
        """Build the full task description with scenario-specific entity IDs."""
        base_desc = self._task_config["description"]
        refs = self._task_refs.get(self._task_id.replace("_course_inquiry", "").replace("_hostel_allocation", "").replace("_course_switch", "").replace("_concurrent_conflict", "").replace("_graduation_crisis", "").replace("_bulk_schedule", ""), {})

        # Map task_id to ref key
        ref_key_map = {
            "task_1_course_inquiry": "task_1",
            "task_2_hostel_allocation": "task_2",
            "task_3_course_switch": "task_3",
            "task_4_concurrent_conflict": "task_4",
            "task_5_graduation_crisis": "task_5",
            "task_6_bulk_schedule": "task_6",
        }
        ref_key = ref_key_map.get(self._task_id, "")
        refs = self._task_refs.get(ref_key, {})

        if self._task_id == "task_1_course_inquiry":
            student_id = refs.get("student_id", "STU-171")
            target_sem = refs.get("target_semester", 6)
            return (
                f"{base_desc}\n\n"
                f"Student {student_id} is asking about available Computer Science "
                f"elective courses for semester {target_sem} that don't conflict with "
                f"their current schedule and fit within their credit limit. "
                f"Please look up the student's current enrollments, find suitable "
                f"CS electives, check for schedule conflicts and credit limits, "
                f"and provide a complete list of valid options."
            )

        elif self._task_id == "task_2_hostel_allocation":
            student_id = refs.get("student_id", "STU-201")
            return (
                f"{base_desc}\n\n"
                f"Student {student_id} is a new student requesting hostel accommodation. "
                f"Please look up the student's record, find a suitable room in a "
                f"gender-appropriate hostel block, verify fee clearance and room "
                f"availability, and process the allocation."
            )

        elif self._task_id == "task_3_course_switch":
            student_id = refs.get("student_id", "STU-088")
            course_a = refs.get("course_a_id", "")
            course_b = refs.get("course_b_id", "")
            return (
                f"{base_desc}\n\n"
                f"Student {student_id} wants to switch from course {course_a} to "
                f"course {course_b}. The add/drop deadline is at step 16 — after "
                f"which drop_course and enroll_student will be rejected.\n\n"
                f"You must: check prerequisites for the target course, check seat "
                f"availability, check credit limits after the switch, check fee "
                f"differential, check scholarship compliance, check academic "
                f"probation restrictions, then execute the drop and enroll."
            )

        elif self._task_id == "task_4_concurrent_conflict":
            stu_x = refs.get("student_x_id", "STU-150")
            stu_y = refs.get("student_y_id", "STU-151")
            course = refs.get("course_id", "")
            return (
                f"{base_desc}\n\n"
                f"Two students have requested enrollment in the same course:\n"
                f"- Student {stu_x} has requested enrollment in {course}\n"
                f"- Student {stu_y} has also requested enrollment in {course}\n\n"
                f"The course has limited seats. You must check both students' "
                f"eligibility, determine if any scholarship or policy dependencies "
                f"affect priority, enroll the appropriate student, and deny the "
                f"other with a proper explanation and alternative suggestions."
            )

        elif self._task_id == "task_5_graduation_crisis":
            student_id = refs.get("student_id", "STU-042")
            student_name = refs.get("student_name", "Karthik Nair")
            return (
                f"{base_desc}\n\n"
                f"Student {student_id} ({student_name}) is in their final semester "
                f"and requests a graduation eligibility check. On the surface "
                f"everything appears fine, but you need to thoroughly investigate "
                f"all aspects: credits, fees, course prerequisites, scholarship "
                f"requirements, hostel status, and academic standing.\n\n"
                f"Check everything carefully. There may be hidden issues that "
                f"need to be discovered and resolved."
            )

        elif self._task_id == "task_6_bulk_schedule":
            pairs = refs.get("student_conflict_pairs", [])
            conflict_lines = []
            for stu_id, c1, c2 in pairs:
                conflict_lines.append(
                    f"  - {stu_id}: exam conflict between {c1} and {c2}"
                )
            conflict_text = "\n".join(conflict_lines) if conflict_lines else "  (conflict details in exam schedule)"
            return (
                f"{base_desc}\n\n"
                f"The following students have reported exam timetable clashes:\n"
                f"{conflict_text}\n\n"
                f"You must resolve ALL conflicts by finding alternative exam "
                f"slots. Constraints: room capacity, faculty invigilator "
                f"availability, and no two exams on the same day per student. "
                f"Resolving one conflict must not create new conflicts. "
                f"When evaluating a risky move, use check_reschedule_impact "
                f"before reschedule_exam."
            )

        return base_desc

    def _make_observation(
        self,
        tool_result: str,
        tool_success: bool,
        error_message: Optional[str],
        step_reward: float,
        notifications: Optional[List[str]] = None,
        metadata_extra: Optional[Dict[str, Any]] = None,
    ) -> UniAdminObservation:
        """Construct a UniAdminObservation."""
        deadline = self._task_config.get("deadline_step")
        steps_remaining = None
        if deadline is not None:
            steps_remaining = max(0, deadline - self._step_count)

        metadata = metadata_extra or {}

        # If done, reward is the grader score
        reward = step_reward
        if self._done and self._grader_result:
            reward = self._grader_result.get("score", 0.0)

        return UniAdminObservation(
            done=self._done,
            reward=reward,
            metadata=metadata,
            task_id=self._task_id,
            task_description=self._task_config.get("description", ""),
            tool_result=tool_result,
            tool_success=tool_success,
            error_message=error_message,
            current_step=self._step_count,
            steps_remaining=steps_remaining,
            notifications=notifications or [],
            available_tools=list(TOOL_NAMES),
        )

    def _log_audit(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result_summary: str,
        success: bool,
        state_diff: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log a tool call to the audit trail."""
        self._audit_log.append({
            "step": self._step_count,
            "timestamp": time.time(),
            "tool_name": tool_name,
            "arguments": arguments,
            "result_summary": result_summary,
            "success": success,
            "state_diff": state_diff,
        })

    def _compute_state_hash(self) -> str:
        """Compute SHA-256 hash of the full entity graph for integrity."""
        if not self._world:
            return hashlib.sha256(b"empty").hexdigest()
        if not self._state_hash_dirty and self._state_hash_cache:
            return self._state_hash_cache

        # Hash all mutable entity collections
        hashable_parts = []
        for key in sorted(self._world.keys()):
            if key.startswith("_"):
                continue
            hashable_parts.append(
                json.dumps(self._world[key], sort_keys=True, default=str)
            )
        combined = "|".join(hashable_parts)
        self._state_hash_cache = hashlib.sha256(combined.encode()).hexdigest()
        self._state_hash_dirty = False
        return self._state_hash_cache

    def _audit_entry_succeeded(self, tool_name: str, **filters: Any) -> bool:
        """Return True if a matching successful tool call already exists."""
        for entry in self._audit_log:
            if entry.get("tool_name") != tool_name or not entry.get("success"):
                continue
            arguments = entry.get("arguments", {})
            if all(arguments.get(key) == value for key, value in filters.items()):
                return True
        return False

    def _can_attempt_exception_override(
        self,
        exception_type: str,
        student_id: str,
        course_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Require prior evidence-gathering before blind exception attempts."""
        if exception_type == "fee_deferral":
            checked_fees = (
                self._audit_entry_succeeded("get_fee_status", student_id=student_id)
                or self._audit_entry_succeeded("check_fee_clearance", student_id=student_id)
            )
            checked_support = self._audit_entry_succeeded("search_scholarships", student_id=student_id)
            if not checked_fees or not checked_support:
                return False, (
                    "Required documentation not found in session context. "
                    "Check fee status or fee clearance and scholarship support "
                    "before requesting a fee deferral exception."
                )
            return True, ""

        if exception_type == "prerequisite_waiver":
            checked_prereq = bool(course_id) and self._audit_entry_succeeded(
                "check_prerequisites", student_id=student_id, course_id=course_id
            )
            checked_history = self._audit_entry_succeeded(
                "get_enrollment_history", student_id=student_id
            )
            if not checked_prereq or not checked_history:
                return False, (
                    "Required documentation not found in session context. "
                    "Check prerequisites and review enrollment history before "
                    "requesting the prerequisite waiver."
                )
            return True, ""

        if exception_type == "credit_overload":
            if not self._audit_entry_succeeded("check_credit_limits", student_id=student_id):
                return False, (
                    "Required documentation not found in session context. "
                    "Check credit limits before requesting a credit overload exception."
                )
            return True, ""

        return True, ""

    def _check_notification_triggers(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        # Task 5: check_credit_limits for Karthik triggers regulation change
        if (
            self._task_id == "task_5_graduation_crisis"
            and tool_name == "check_credit_limits"
            and arguments.get("student_id") == self._task_refs.get("task_5", {}).get("student_id")
            and "NTF-001" not in self._fired_notification_ids
        ):
            # Find the notification
            for ntf in self._world.get("notifications", []):
                if ntf["notification_id"] == "NTF-001":
                    self._pending_notifications.append(ntf["content"])
                    self._fired_notification_ids.add("NTF-001")
                    # Apply the dynamic regulation: elevate credit limit
                    self._credit_limit_elevated = True
                    break

        # Task 3: deadline warning at step >= 12
        if (
            self._task_id == "task_3_course_switch"
            and self._step_count >= 12
            and "NTF-002" not in self._fired_notification_ids
        ):
            for ntf in self._world.get("notifications", []):
                if ntf["notification_id"] == "NTF-002":
                    self._pending_notifications.append(ntf["content"])
                    self._fired_notification_ids.add("NTF-002")
                    break

        # Generic: capacity alert when seat check returns <=2
        if (
            tool_name == "check_seat_availability"
            and result.get("success")
            and "NTF-003" not in self._fired_notification_ids
        ):
            data = result.get("data", {})
            if isinstance(data, dict) and data.get("available_seats", 999) <= 2:
                for ntf in self._world.get("notifications", []):
                    if ntf["notification_id"] == "NTF-003":
                        self._pending_notifications.append(ntf["content"])
                        self._fired_notification_ids.add("NTF-003")
                        break

        # Generic: fee reminder when fee clearance check shows outstanding
        if (
            tool_name == "check_fee_clearance"
            and result.get("success")
            and "NTF-004" not in self._fired_notification_ids
        ):
            data = result.get("data", {})
            if isinstance(data, dict) and data.get("outstanding_amount", 0) > 0:
                for ntf in self._world.get("notifications", []):
                    if ntf["notification_id"] == "NTF-004":
                        self._pending_notifications.append(ntf["content"])
                        self._fired_notification_ids.add("NTF-004")
                        break

        # Generic: probation notice when student record shows probation
        if (
            tool_name == "get_student_record"
            and result.get("success")
            and "NTF-006" not in self._fired_notification_ids
        ):
            data = result.get("data", {})
            if isinstance(data, dict) and data.get("academic_status") == "probation":
                for ntf in self._world.get("notifications", []):
                    if ntf["notification_id"] == "NTF-006":
                        self._pending_notifications.append(ntf["content"])
                        self._fired_notification_ids.add("NTF-006")
                        break

        # Hostel deadline notice for graduating students
        if (
            tool_name == "get_hostel_details"
            and result.get("success")
            and "NTF-007" not in self._fired_notification_ids
        ):
            stu_id = arguments.get("student_id", "")
            student = self._find_student(stu_id)
            if student and student.get("semester") == 8:
                for ntf in self._world.get("notifications", []):
                    if ntf["notification_id"] == "NTF-007":
                        self._pending_notifications.append(ntf["content"])
                        self._fired_notification_ids.add("NTF-007")
                        break

    # Helper: Entity Lookups

    def _find_student(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Find a student by ID."""
        for s in self._world.get("students", []):
            if s["student_id"] == student_id:
                return s
        return None

    def _find_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Find a course by ID."""
        for c in self._world.get("courses", []):
            if c["course_id"] == course_id:
                return c
        return None

    def _find_enrollments_for_student(
        self, student_id: str, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find all enrollments for a student, optionally filtered by status."""
        results = []
        for e in self._world.get("enrollments", []):
            if e["student_id"] == student_id:
                if status is None or e["status"] == status:
                    results.append(e)
        return results

    def _find_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Find a hostel room by ID."""
        for r in self._world.get("hostel_rooms", []):
            if r["room_id"] == room_id:
                return r
        return None

    def _find_block(self, block_id: str) -> Optional[Dict[str, Any]]:
        """Find a hostel block by ID."""
        for b in self._world.get("hostel_blocks", []):
            if b["block_id"] == block_id:
                return b
        return None

    def _find_fee_record(self, student_id: str) -> Optional[Dict[str, Any]]:
        """Find fee record for a student."""
        for f in self._world.get("fee_records", []):
            if f["student_id"] == student_id:
                return f
        return None

    def _find_exam_for_course(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Find an exam schedule entry by course ID."""
        for exam in self._world.get("exam_schedule", []):
            if exam["course_id"] == course_id:
                return exam
        return None

    def _get_student_exam_entries(self, student_id: str) -> List[Dict[str, Any]]:
        """Return all exam entries for the student's currently enrolled courses."""
        enrolled_courses = {
            e["course_id"]
            for e in self._world.get("enrollments", [])
            if e["student_id"] == student_id and e["status"] == "enrolled"
        }
        return [
            exam for exam in self._world.get("exam_schedule", [])
            if exam["course_id"] in enrolled_courses
        ]

    def _student_has_same_day_exam(
        self,
        student_id: str,
        candidate_date: str,
        exclude_course_id: Optional[str] = None,
    ) -> bool:
        """Check whether a student already has another exam on the candidate date."""
        for exam in self._get_student_exam_entries(student_id):
            if exclude_course_id and exam["course_id"] == exclude_course_id:
                continue
            if exam["date"] == candidate_date:
                return True
        return False

    def _is_exam_slot_available(
        self,
        course_id: str,
        candidate_date: str,
        candidate_time_slot: str,
        candidate_room_id: str,
        faculty_id: str,
    ) -> Tuple[bool, str]:
        """Validate whether an exam slot is available for rescheduling."""
        for exam in self._world.get("exam_schedule", []):
            if exam["course_id"] == course_id:
                continue
            if exam["date"] == candidate_date and exam["time_slot"] == candidate_time_slot:
                if exam["room_id"] == candidate_room_id:
                    return False, f"Room {candidate_room_id} is already booked."
                if exam["faculty_invigilator"] == faculty_id:
                    return False, f"Faculty {faculty_id} is already invigilating another exam."
        return True, ""

    def _assess_reschedule_impact(
        self,
        course_id: str,
        new_date: str,
        new_time_slot: str,
        new_room_id: str,
    ) -> Dict[str, Any]:
        """Dry-run a proposed exam move and report downstream student impact."""
        exam = self._find_exam_for_course(course_id)
        if not exam:
            return {
                "slot_available": False,
                "availability_reason": f"Exam not found for course {course_id}",
                "impacted_students": [],
                "same_slot_conflicts": [],
                "same_day_violations": [],
            }

        slot_available, availability_reason = self._is_exam_slot_available(
            course_id,
            new_date,
            new_time_slot,
            new_room_id,
            exam["faculty_invigilator"],
        )
        impacted_students = sorted(
            e["student_id"]
            for e in self._world.get("enrollments", [])
            if e["course_id"] == course_id and e["status"] == "enrolled"
        )

        same_slot_conflicts: List[Dict[str, Any]] = []
        same_day_violations: List[Dict[str, Any]] = []
        seen_same_slot: Set[Tuple[str, str, str, str]] = set()
        seen_same_day: Set[Tuple[str, str, str]] = set()
        if slot_available:
            for student_id in impacted_students:
                for other_exam in self._get_student_exam_entries(student_id):
                    if other_exam["course_id"] == course_id:
                        continue
                    if (
                        other_exam["date"] == new_date
                        and other_exam["time_slot"] == new_time_slot
                    ):
                        key = (student_id, other_exam["course_id"], new_date, new_time_slot)
                        if key not in seen_same_slot:
                            same_slot_conflicts.append(
                                {
                                    "student_id": student_id,
                                    "conflicting_course_id": other_exam["course_id"],
                                    "date": new_date,
                                    "time_slot": new_time_slot,
                                }
                            )
                            seen_same_slot.add(key)
                    elif other_exam["date"] == new_date:
                        key = (student_id, other_exam["course_id"], new_date)
                        if key not in seen_same_day:
                            same_day_violations.append(
                                {
                                    "student_id": student_id,
                                    "conflicting_course_id": other_exam["course_id"],
                                    "date": new_date,
                                }
                            )
                            seen_same_day.add(key)

        return {
            "slot_available": slot_available,
            "availability_reason": availability_reason,
            "impacted_students": impacted_students,
            "impacted_student_count": len(impacted_students),
            "same_slot_conflicts": same_slot_conflicts,
            "new_same_slot_conflicts": len(same_slot_conflicts),
            "same_day_violations": same_day_violations,
            "new_same_day_violations": len(same_day_violations),
            "new_conflicts_created": len(same_slot_conflicts) + len(same_day_violations),
            "would_create_new_conflict": bool(same_slot_conflicts or same_day_violations),
        }

    def _get_current_credits(self, student_id: str) -> int:
        """Calculate total credits for currently enrolled courses."""
        total = 0
        for e in self._world.get("enrollments", []):
            if e["student_id"] == student_id and e["status"] == "enrolled":
                course = self._find_course(e["course_id"])
                if course:
                    total += course.get("credits", 0)
        return total

    def _get_credit_limit(self, student_id: str) -> int:
        """Get the credit limit for a student, considering dynamic regulation."""
        student = self._find_student(student_id)
        if not student:
            return DEFAULT_CREDIT_LIMIT

        if self._credit_limit_elevated and student.get("semester") == 8:
            return ELEVATED_CREDIT_LIMIT

        if student.get("academic_status") == "probation":
            return 15  # Probation credit limit

        return DEFAULT_CREDIT_LIMIT

    def _evaluate_exception(
        self, exception_type: str, student_id: str, context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """Evaluate whether an exception override should be approved."""
        student = self._find_student(student_id)
        if not student:
            return False, "Student not found."

        context = context or {}

        if exception_type == "credit_overload":
            if student.get("semester") != 8:
                return False, "Credit overload exception requires final semester (semester 8)."
            graduation_credits = 160
            current_total = student.get("credits_completed", 0) + self._get_current_credits(student_id)
            shortfall = graduation_credits - current_total
            if shortfall <= 0:
                return False, "Student already meets graduation credit requirement."
            if shortfall > 3:
                return False, f"Credit shortfall is {shortfall}, exceeds maximum of 3 for exception."
            return True, f"Credit overload approved: final semester, {shortfall} credits short of graduation."

        elif exception_type == "prerequisite_waiver":
            course_id = context.get("course_id", "")
            course = self._find_course(course_id)
            if not course:
                return False, "Target course not found."

            prereqs = course.get("prerequisites", [])
            if not prereqs:
                return False, "Course has no prerequisites to waive."

            student_history = self._find_enrollments_for_student(student_id)
            completed_courses = [
                e for e in student_history
                if e["status"] == "completed" and e.get("grade") and _grade_gte(e["grade"], "B")
            ]

            if not completed_courses:
                return False, "No completed courses with grade B or better found."

            for prereq_id in prereqs:
                prereq_course = self._find_course(prereq_id)
                if not prereq_course:
                    continue
                prereq_dept = prereq_course.get("department", "")

                for enrollment in completed_courses:
                    enrolled_course = self._find_course(enrollment["course_id"])
                    if enrolled_course and enrolled_course.get("department") == prereq_dept:
                        return True, (
                            f"Prerequisite waiver approved: student completed "
                            f"{enrollment['course_id']} with grade {enrollment['grade']} "
                            f"(equivalent to prerequisite {prereq_id})."
                        )

            return False, "No equivalent course with grade >= B found for the prerequisite."

        elif exception_type == "fee_deferral":
            fee_record = self._find_fee_record(student_id)
            if not fee_record:
                return False, "No fee record found."

            total_fee = fee_record.get("total_fee", 0)
            if total_fee <= 0:
                return False, "No fees to defer."

            total_scholarship = 0
            for sch in self._world.get("scholarships", []):
                if student_id in sch.get("beneficiaries", []):
                    total_scholarship += sch.get("amount", 0)

            coverage = total_scholarship / total_fee if total_fee > 0 else 0
            if coverage >= 0.5:
                return True, f"Fee deferral approved: scholarship covers {coverage*100:.0f}% of fees."
            return False, f"Scholarship coverage is {coverage*100:.0f}%, minimum 50% required."

        elif exception_type == "academic_probation_clearance":
            if student.get("cgpa", 0) >= 6.0:
                return True, f"Probation clearance approved: CGPA {student['cgpa']} >= 6.0."
            return False, f"CGPA {student.get('cgpa', 0)} is below 6.0 threshold for clearance."

        else:
            return False, f"Exception type '{exception_type}' is not available or always denied."

    # Grader stub (replaced in Phases 5-6)

    def _run_grader(self) -> float:
        """Run the grader for the current task. Returns score 0.0-1.0."""
        ref_key_map = {
            "task_1_course_inquiry": "task_1",
            "task_2_hostel_allocation": "task_2",
            "task_3_course_switch": "task_3",
            "task_4_concurrent_conflict": "task_4",
            "task_5_graduation_crisis": "task_5",
            "task_6_bulk_schedule": "task_6",
        }
        ref_key = ref_key_map.get(self._task_id, "")
        task_refs = self._task_refs.get(ref_key, {})

        self._grader_result = dispatch_grader(
            task_id=self._task_id,
            audit_log=self._audit_log,
            world_state=self._world,
            modified_entities=self._modified_entities,
            task_refs=task_refs,
            final_response=self._final_response_data,
        )
        return self._grader_result.get("score", 0.0)

    # Public accessors

    def get_grader_result(self) -> Optional[Dict[str, Any]]:
        return self._grader_result

    def get_audit_log(self) -> List[Dict[str, Any]]:
        return list(self._audit_log)

    def get_final_response(self) -> Optional[Dict[str, Any]]:
        return self._final_response_data

    # Tool 1: search_students

    def _tool_search_students(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search students by query and/or filters with pagination."""
        query = str(arguments.get("query", "")).strip().lower()
        filters = arguments.get("filters", {})
        page = int(arguments.get("page", 1))

        if page < 1:
            page = 1

        results = []
        for s in self._world.get("students", []):
            # Text search on name and student_id
            if query:
                if (query not in s["student_id"].lower()
                        and query not in s["name"].lower()):
                    continue

            # Apply filters
            if filters:
                if "department" in filters and s["department"] != filters["department"]:
                    continue
                if "semester" in filters and s["semester"] != int(filters["semester"]):
                    continue
                if "min_cgpa" in filters and s["cgpa"] < float(filters["min_cgpa"]):
                    continue
                if "max_cgpa" in filters and s["cgpa"] > float(filters["max_cgpa"]):
                    continue
                if "academic_status" in filters and s["academic_status"] != filters["academic_status"]:
                    continue

            results.append(s)

        # Paginate
        per_page = 10
        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        page_results = results[start:end]

        entity_ids = {s["student_id"] for s in page_results}

        return {
            "success": True,
            "data": {
                "_meta": {
                    "total_results": total,
                    "current_page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
                    "has_more_pages": end < total,
                    "next_page": page + 1 if end < total else None,
                    "next_page_hint": f"Pass page={page + 1} to see more" if end < total else "",
                },
                "results": page_results,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
                "returned_count": len(page_results),
                "has_more": end < total,
                "next_page": page + 1 if end < total else None,
                "remaining_results": max(0, total - end),
                "pagination_notice": (
                    f"More results are available. Request page {page + 1}."
                    if end < total else "This is the final page."
                ),
            },
            "entity_ids": entity_ids,
        }

    # Tool 2: search_courses

    def _tool_search_courses(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search courses by query and/or filters with pagination."""
        query = str(arguments.get("query", "")).strip().lower()
        filters = arguments.get("filters", {})
        page = int(arguments.get("page", 1))

        if page < 1:
            page = 1

        results = []
        for c in self._world.get("courses", []):
            # Text search
            if query:
                if (query not in c["course_id"].lower()
                        and query not in c["name"].lower()):
                    continue

            # Apply filters
            if filters:
                if "department" in filters and c["department"] != filters["department"]:
                    continue
                if "semester_offered" in filters and c["semester_offered"] != int(filters["semester_offered"]):
                    continue
                if "min_credits" in filters and c["credits"] < int(filters["min_credits"]):
                    continue
                if "max_credits" in filters and c["credits"] > int(filters["max_credits"]):
                    continue
                if filters.get("has_availability"):
                    if c["current_enrollment"] >= c["max_capacity"]:
                        continue

            results.append(c)

        # Paginate
        per_page = 10
        total = len(results)
        start = (page - 1) * per_page
        end = start + per_page
        page_results = results[start:end]

        entity_ids = {c["course_id"] for c in page_results}

        return {
            "success": True,
            "data": {
                "_meta": {
                    "total_results": total,
                    "current_page": page,
                    "per_page": per_page,
                    "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
                    "has_more_pages": end < total,
                    "next_page": page + 1 if end < total else None,
                    "next_page_hint": f"Pass page={page + 1} to see more" if end < total else "",
                },
                "results": page_results,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page if total > 0 else 0,
                "returned_count": len(page_results),
                "has_more": end < total,
                "next_page": page + 1 if end < total else None,
                "remaining_results": max(0, total - end),
                "pagination_notice": (
                    f"More results are available. Request page {page + 1}."
                    if end < total else "This is the final page."
                ),
            },
            "entity_ids": entity_ids,
        }

    # Tool 3: search_faculty

    def _tool_search_faculty(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search faculty by query and/or department."""
        query = str(arguments.get("query", "")).strip().lower()
        department = str(arguments.get("department", "")).strip()

        results = []
        for f in self._world.get("faculty", []):
            if query:
                if (query not in f["faculty_id"].lower()
                        and query not in f["name"].lower()):
                    continue
            if department:
                if f["department"] != department:
                    continue
            results.append(f)

        entity_ids = {f["faculty_id"] for f in results}

        return {
            "success": True,
            "data": {"results": results, "total": len(results)},
            "entity_ids": entity_ids,
        }

    # Tool 4: search_regulations

    def _tool_search_regulations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search regulations by keyword and/or applicable entity type."""
        keyword = str(arguments.get("keyword", "")).strip().lower()
        applicable_to = str(arguments.get("applicable_to", "")).strip().lower()

        results = []
        for r in self._world.get("regulations", []):
            if keyword:
                if (keyword not in r["title"].lower()
                        and keyword not in r["description"].lower()):
                    continue
            if applicable_to:
                if r["applicable_to"].lower() != applicable_to:
                    continue
            results.append(r)

        entity_ids = {r["reg_id"] for r in results}

        return {
            "success": True,
            "data": {"results": results, "total": len(results)},
            "entity_ids": entity_ids,
        }

    # Tool 5: search_scholarships

    def _tool_search_scholarships(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search scholarships a student is eligible for."""
        student_id = arguments.get("student_id")
        if not student_id:
            return {
                "success": False,
                "data": {},
                "error": "Missing required argument: student_id",
                "entity_ids": set(),
            }

        student = self._find_student(str(student_id))
        if not student:
            return {
                "success": False,
                "data": {},
                "error": f"Entity not found: {student_id}",
                "entity_ids": set(),
            }

        eligible = []
        held = []
        for sch in self._world.get("scholarships", []):
            # Check if student is a current beneficiary
            if student_id in sch.get("beneficiaries", []):
                held.append(sch)
                continue

            # Check basic eligibility
            if (student["cgpa"] >= sch.get("min_cgpa", 0)
                    and student["credits_completed"] >= sch.get("min_credits", 0)):
                eligible.append(sch)

        entity_ids = {sch["scholarship_id"] for sch in eligible + held}
        entity_ids.add(student_id)

        return {
            "success": True,
            "data": {
                "student_id": student_id,
                "currently_held": held,
                "eligible_for": eligible,
            },
            "entity_ids": entity_ids,
        }

    
    # Tool 6: get_student_record
    

    def _tool_get_student_record(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve the full record for a student."""
        student_id = arguments.get("student_id")
        if not student_id:
            return {
                "success": False,
                "data": {},
                "error": "Missing required argument: student_id",
                "entity_ids": set(),
            }

        student = self._find_student(str(student_id))
        if not student:
            return {
                "success": False,
                "data": {},
                "error": f"Entity not found: {student_id}",
                "entity_ids": set(),
            }

        warnings = []
        for scholarship in self._world.get("scholarships", []):
            if str(student_id) not in scholarship.get("beneficiaries", []):
                continue
            min_semester_credits = scholarship.get("min_semester_credits")
            if min_semester_credits:
                warnings.append(
                    f"Warning: Scholarship {scholarship['scholarship_id']} requires maintaining {min_semester_credits} active credits."
                )

        return {
            "success": True,
            "data": {**dict(student), "warnings": warnings},
            "entity_ids": {student_id},
        }

    # Tool 7: get_course_details

    def _tool_get_course_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve full details for a course including enrolled students."""
        course_id = arguments.get("course_id")
        if not course_id:
            return {
                "success": False,
                "data": {},
                "error": "Missing required argument: course_id",
                "entity_ids": set(),
            }

        course = self._find_course(str(course_id))
        if not course:
            return {
                "success": False,
                "data": {},
                "error": f"Entity not found: {course_id}",
                "entity_ids": set(),
            }

        # Find enrolled students
        enrolled = []
        for e in self._world.get("enrollments", []):
            if e["course_id"] == course_id and e["status"] == "enrolled":
                enrolled.append(e["student_id"])

        course_data = dict(course)
        course_data["enrolled_students"] = enrolled

        entity_ids = {course_id}
        entity_ids.update(enrolled)

        return {
            "success": True,
            "data": course_data,
            "entity_ids": entity_ids,
        }

    # Tool 8: get_enrollment_history

    def _tool_get_enrollment_history(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve all enrollments for a student."""
        student_id = arguments.get("student_id")
        if not student_id:
            return {
                "success": False,
                "data": {},
                "error": "Missing required argument: student_id",
                "entity_ids": set(),
            }

        student = self._find_student(str(student_id))
        if not student:
            return {
                "success": False,
                "data": {},
                "error": f"Entity not found: {student_id}",
                "entity_ids": set(),
            }

        enrollments = []
        for e in self._world.get("enrollments", []):
            if e["student_id"] == student_id:
                enrollments.append(e)

        entity_ids = {student_id}
        entity_ids.update(e["enrollment_id"] for e in enrollments)
        entity_ids.update(e["course_id"] for e in enrollments)

        return {
            "success": True,
            "data": {
                "student_id": student_id,
                "enrollments": enrollments,
                "total": len(enrollments),
            },
            "entity_ids": entity_ids,
        }

    # Tool 9: get_fee_status

    def _tool_get_fee_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve fee records for a student."""
        student_id = arguments.get("student_id")
        if not student_id:
            return {
                "success": False,
                "data": {},
                "error": "Missing required argument: student_id",
                "entity_ids": set(),
            }

        student = self._find_student(str(student_id))
        if not student:
            return {
                "success": False,
                "data": {},
                "error": f"Entity not found: {student_id}",
                "entity_ids": set(),
            }

        fee_record = self._find_fee_record(str(student_id))
        if not fee_record:
            return {
                "success": True,
                "data": {
                    "student_id": student_id,
                    "fee_records": [],
                    "total_outstanding": 0,
                },
                "entity_ids": {student_id},
            }

        entity_ids = {student_id, fee_record["record_id"]}

        warnings = []
        for scholarship in self._world.get("scholarships", []):
            if str(student_id) not in scholarship.get("beneficiaries", []):
                continue
            min_semester_credits = scholarship.get("min_semester_credits")
            if min_semester_credits:
                warnings.append(
                    f"Warning: Scholarship {scholarship['scholarship_id']} requires maintaining {min_semester_credits} active credits."
                )

        return {
            "success": True,
            "data": {
                "student_id": student_id,
                "fee_record": dict(fee_record),
                "total_outstanding": fee_record["amount_due"],
                "warnings": warnings,
            },
            "entity_ids": entity_ids,
        }

    # Tool 10: get_hostel_details

    def _tool_get_hostel_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve hostel allocation details for a student."""
        student_id = arguments.get("student_id")
        if not student_id:
            return {
                "success": False,
                "data": {},
                "error": "Missing required argument: student_id",
                "entity_ids": set(),
            }

        student = self._find_student(str(student_id))
        if not student:
            return {
                "success": False,
                "data": {},
                "error": f"Entity not found: {student_id}",
                "entity_ids": set(),
            }

        hostel_id = student.get("hostel_id")
        if not hostel_id:
            return {
                "success": True,
                "data": {
                    "student_id": student_id,
                    "allocated": False,
                    "message": "No hostel allocation found for this student.",
                },
                "entity_ids": {student_id},
            }

        room = self._find_room(hostel_id)
        if not room:
            return {
                "success": True,
                "data": {
                    "student_id": student_id,
                    "allocated": True,
                    "room_id": hostel_id,
                    "room_details": None,
                    "message": f"Room {hostel_id} referenced but not found in records.",
                },
                "entity_ids": {student_id},
            }

        block = self._find_block(room["block_id"])
        block_data = dict(block) if block else {"block_id": room["block_id"]}

        entity_ids = {student_id, room["room_id"], room["block_id"]}

        return {
            "success": True,
            "data": {
                "student_id": student_id,
                "allocated": True,
                "room": dict(room),
                "block": block_data,
                "checkout_initiated": self._hostel_checkout_initiated.get(str(student_id), False),
            },
            "entity_ids": entity_ids,
        }

    # Tool 11: get_exam_schedule

    def _tool_get_exam_schedule(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve exam schedule for a student or course."""
        student_id = arguments.get("student_id", "")
        course_id = arguments.get("course_id", "")

        if not student_id and not course_id:
            return {
                "success": False,
                "data": {},
                "error": "Missing required argument: at least one of student_id or course_id must be provided",
                "entity_ids": set(),
            }

        exams = []
        entity_ids: Set[str] = set()

        if course_id:
            # Get exam for specific course
            course = self._find_course(str(course_id))
            if not course:
                return {
                    "success": False,
                    "data": {},
                    "error": f"Entity not found: {course_id}",
                    "entity_ids": set(),
                }
            entity_ids.add(course_id)

            for ex in self._world.get("exam_schedule", []):
                if ex["course_id"] == course_id:
                    exams.append(ex)
                    entity_ids.add(ex["exam_id"])

        if student_id:
            # Get exams for all courses the student is enrolled in
            student = self._find_student(str(student_id))
            if not student:
                return {
                    "success": False,
                    "data": {},
                    "error": f"Entity not found: {student_id}",
                    "entity_ids": set(),
                }
            entity_ids.add(student_id)

            # Get enrolled course IDs
            enrolled_courses = set()
            for e in self._world.get("enrollments", []):
                if e["student_id"] == student_id and e["status"] == "enrolled":
                    enrolled_courses.add(e["course_id"])

            for ex in self._world.get("exam_schedule", []):
                if ex["course_id"] in enrolled_courses:
                    if ex not in exams: 
                        exams.append(ex)
                    entity_ids.add(ex["exam_id"])
                    entity_ids.add(ex["course_id"])

        # Check for conflicts (same date + time_slot)
        conflicts = []
        for i, ex1 in enumerate(exams):
            for ex2 in exams[i + 1:]:
                if ex1["date"] == ex2["date"] and ex1["time_slot"] == ex2["time_slot"]:
                    conflicts.append({
                        "exam_1": ex1["exam_id"],
                        "course_1": ex1["course_id"],
                        "exam_2": ex2["exam_id"],
                        "course_2": ex2["course_id"],
                        "date": ex1["date"],
                        "time_slot": ex1["time_slot"],
                    })

        return {
            "success": True,
            "data": {
                "exams": exams,
                "total": len(exams),
                "conflicts": conflicts,
                "has_conflicts": len(conflicts) > 0,
            },
            "entity_ids": entity_ids,
        }

   
    # Tool 12: check_prerequisites

    def _tool_check_prerequisites(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a student has met prerequisites for a course."""
        student_id = arguments.get("student_id")
        course_id = arguments.get("course_id")

        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}
        if not course_id:
            return {"success": False, "data": {}, "error": "Missing required argument: course_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}

        course = self._find_course(str(course_id))
        if not course:
            return {"success": False, "data": {}, "error": f"Entity not found: {course_id}", "entity_ids": set()}

        prereqs = course.get("prerequisites", [])
        if not prereqs:
            return {
                "success": True,
                "data": {
                    "student_id": student_id,
                    "course_id": course_id,
                    "prerequisites_met": True,
                    "prerequisites_required": [],
                    "prerequisites_completed": [],
                    "missing": [],
                },
                "entity_ids": {student_id, course_id},
            }

        completed = []
        missing = []
        student_history = self._find_enrollments_for_student(student_id)
        completed_courses = {e["course_id"] for e in student_history if e["status"] == "completed"}

        for prereq_id in prereqs:
            if prereq_id in completed_courses:
                completed.append(prereq_id)
            else:
                missing.append(prereq_id)

        return {
            "success": True,
            "data": {
                "student_id": student_id,
                "course_id": course_id,
                "prerequisites_met": len(missing) == 0,
                "prerequisites_required": prereqs,
                "prerequisites_completed": completed,
                "missing": missing,
            },
            "entity_ids": {student_id, course_id},
        }

    
    # Tool 13: check_credit_limits
    

    def _tool_check_credit_limits(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check credit limits and available headroom for a student."""
        student_id = arguments.get("student_id")
        additional_credits = arguments.get("additional_credits", 0)

        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}

        current_credits = self._get_current_credits(str(student_id))
        credit_limit = self._get_credit_limit(str(student_id))
        headroom = credit_limit - current_credits

        new_total = current_credits + additional_credits
        within_limit = new_total <= credit_limit

        return {
            "success": True,
            "data": {
                "student_id": student_id,
                "current_credits": current_credits,
                "credit_limit": credit_limit,
                "headroom": headroom,
                "additional_credits_requested": additional_credits,
                "new_total_with_additional": new_total,
                "within_limit": within_limit,
                "limit_exceeded": not within_limit,
            },
            "entity_ids": {student_id},
        }

    
    # Tool 14: check_seat_availability
    

    def _tool_check_seat_availability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check seat availability in a course."""
        course_id = arguments.get("course_id")

        if not course_id:
            return {"success": False, "data": {}, "error": "Missing required argument: course_id", "entity_ids": set()}

        course = self._find_course(str(course_id))
        if not course:
            return {"success": False, "data": {}, "error": f"Entity not found: {course_id}", "entity_ids": set()}

        max_capacity = course["max_capacity"]
        current_enrollment = course["current_enrollment"]
        available_seats = max_capacity - current_enrollment
        has_availability = available_seats > 0

        return {
            "success": True,
            "data": {
                "course_id": course_id,
                "course_name": course["name"],
                "max_capacity": max_capacity,
                "current_enrollment": current_enrollment,
                "available_seats": available_seats,
                "has_availability": has_availability,
                "full": not has_availability,
            },
            "entity_ids": {course_id},
        }

    
    # Tool 15: check_fee_clearance
    

    def _tool_check_fee_clearance(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a student has cleared all fees."""
        student_id = arguments.get("student_id")

        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}

        fee_record = self._find_fee_record(str(student_id))
        if not fee_record:
            return {
                "success": True,
                "data": {
                    "student_id": student_id,
                    "fee_cleared": True,
                    "outstanding_amount": 0,
                    "total_fee": 0,
                },
                "entity_ids": {student_id},
            }

        outstanding = fee_record.get("amount_due", 0)
        fee_cleared = outstanding <= 0

        return {
            "success": True,
            "data": {
                "student_id": student_id,
                "fee_cleared": fee_cleared,
                "outstanding_amount": outstanding,
                "total_fee": fee_record.get("total_fee", 0),
                "amount_paid": fee_record.get("amount_paid", 0),
            },
            "entity_ids": {student_id, fee_record["record_id"]},
        }

    
    # Tool 16: check_scholarship_compliance
    

    def _tool_check_scholarship_compliance(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a student is compliant with scholarship requirements."""
        student_id = arguments.get("student_id")
        scholarship_id = arguments.get("scholarship_id")

        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}
        if not scholarship_id:
            return {"success": False, "data": {}, "error": "Missing required argument: scholarship_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}

        scholarship = None
        for sch in self._world.get("scholarships", []):
            if sch["scholarship_id"] == scholarship_id:
                scholarship = sch
                break

        if not scholarship:
            return {"success": False, "data": {}, "error": f"Entity not found: {scholarship_id}", "entity_ids": set()}

        is_beneficiary = student_id in scholarship.get("beneficiaries", [])
        min_cgpa = scholarship.get("min_cgpa", 0)
        student_cgpa = student.get("cgpa", 0)
        cgpa_compliant = student_cgpa >= min_cgpa

        current_credits = self._get_current_credits(str(student_id))
        min_credits = scholarship.get("min_semester_credits", 0)
        credits_compliant = current_credits >= min_credits or min_credits == 0

        required_courses = scholarship.get("required_courses", [])
        enrolled_courses = {e["course_id"] for e in self._world.get("enrollments", [])
                          if e["student_id"] == student_id and e["status"] == "enrolled"}
        required_courses_met = all(rc in enrolled_courses for rc in required_courses)

        compliant = is_beneficiary and cgpa_compliant and credits_compliant and required_courses_met

        return {
            "success": True,
            "data": {
                "student_id": student_id,
                "scholarship_id": scholarship_id,
                "is_beneficiary": is_beneficiary,
                "compliant": compliant,
                "cgpa_compliant": cgpa_compliant,
                "student_cgpa": student_cgpa,
                "required_cgpa": min_cgpa,
                "credits_compliant": credits_compliant,
                "current_credits": current_credits,
                "required_semester_credits": min_credits,
                "required_courses_met": required_courses_met,
                "required_courses": required_courses,
            },
            "entity_ids": {student_id, scholarship_id},
        }

    
    # Tool 17: enroll_student
    

    def _tool_enroll_student(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Enroll a student in a course."""
        student_id = arguments.get("student_id")
        course_id = arguments.get("course_id")
        exception_override = arguments.get("exception_override", False)

        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}
        if not course_id:
            return {"success": False, "data": {}, "error": "Missing required argument: course_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}

        course = self._find_course(str(course_id))
        if not course:
            return {"success": False, "data": {}, "error": f"Entity not found: {course_id}", "entity_ids": set()}

        # Check deadline (Task 3)
        if self._deadline_passed:
            return {
                "success": False,
                "data": {"reason": "deadline_passed"},
                "error": "Add/drop deadline has passed. Enrollment changes are no longer permitted.",
                "entity_ids": {student_id, course_id},
            }

        # Check duplicate enrollment
        for e in self._world.get("enrollments", []):
            if (e["student_id"] == student_id and e["course_id"] == course_id
                    and e["status"] == "enrolled"):
                return {
                    "success": False,
                    "data": {"reason": "already_enrolled"},
                    "error": f"Student {student_id} is already enrolled in {course_id}.",
                    "entity_ids": {student_id, course_id},
                }

        # Check seat availability
        if course["current_enrollment"] >= course["max_capacity"]:
            return {
                "success": False,
                "data": {"reason": "course_full", "exception_available": False},
                "error": f"Course {course_id} is full ({course['current_enrollment']}/{course['max_capacity']}).",
                "entity_ids": {student_id, course_id},
            }

        # Check fee clearance
        fee_record = self._find_fee_record(str(student_id))
        if fee_record and fee_record.get("amount_due", 0) > 0:
            if exception_override:
                override_allowed, override_reason = self._can_attempt_exception_override(
                    "fee_deferral",
                    str(student_id),
                    str(course_id),
                )
                if not override_allowed:
                    return {
                        "success": False,
                        "data": {
                            "reason": "override_requires_prior_validation",
                            "exception_type": "fee_deferral",
                        },
                        "error": override_reason,
                        "entity_ids": {student_id, course_id},
                        "metadata": {"exception_available": True, "exception_type": "fee_deferral"},
                    }
                approved, reason = self._evaluate_exception("fee_deferral", str(student_id))
                if not approved:
                    return {
                        "success": False,
                        "data": {"reason": "fee_exception_denied", "exception_available": True, "exception_type": "fee_deferral"},
                        "error": f"Fee deferral exception denied: {reason}",
                        "entity_ids": {student_id, course_id},
                        "metadata": {"exception_available": True, "exception_type": "fee_deferral"},
                    }
            else:
                return {
                    "success": False,
                    "data": {"reason": "fees_outstanding", "outstanding": fee_record["amount_due"],
                             "exception_available": True, "exception_type": "fee_deferral"},
                    "error": f"Outstanding fees of INR {fee_record['amount_due']} must be cleared.",
                    "entity_ids": {student_id, course_id},
                    "metadata": {"exception_available": True, "exception_type": "fee_deferral"},
                }

        # Check prerequisites
        prereqs = course.get("prerequisites", [])
        if prereqs:
            completed = set()
            for e in self._world.get("enrollments", []):
                if e["student_id"] == student_id and e["status"] == "completed":
                    completed.add(e["course_id"])

            missing = [p for p in prereqs if p not in completed]
            if missing:
                if exception_override:
                    override_allowed, override_reason = self._can_attempt_exception_override(
                        "prerequisite_waiver",
                        str(student_id),
                        str(course_id),
                    )
                    if not override_allowed:
                        return {
                            "success": False,
                            "data": {
                                "reason": "override_requires_prior_validation",
                                "missing": missing,
                                "exception_type": "prerequisite_waiver",
                            },
                            "error": override_reason,
                            "entity_ids": {student_id, course_id},
                            "metadata": {"exception_available": True, "exception_type": "prerequisite_waiver"},
                        }
                    approved, reason = self._evaluate_exception(
                        "prerequisite_waiver", str(student_id),
                        context={"course_id": str(course_id)}
                    )
                    if not approved:
                        return {
                            "success": False,
                            "data": {"reason": "prereq_exception_denied", "missing": missing,
                                     "exception_available": True, "exception_type": "prerequisite_waiver"},
                            "error": f"Prerequisite waiver denied: {reason}",
                            "entity_ids": {student_id, course_id},
                            "metadata": {"exception_available": True, "exception_type": "prerequisite_waiver"},
                        }
                else:
                    return {
                        "success": False,
                        "data": {"reason": "prerequisites_not_met", "missing": missing,
                                 "exception_available": True, "exception_type": "prerequisite_waiver"},
                        "error": f"Prerequisites not met. Missing: {missing}",
                        "entity_ids": {student_id, course_id},
                        "metadata": {"exception_available": True, "exception_type": "prerequisite_waiver"},
                    }

        # Check credit limit
        current_credits = self._get_current_credits(str(student_id))
        credit_limit = self._get_credit_limit(str(student_id))
        new_total = current_credits + course.get("credits", 0)

        if new_total > credit_limit:
            if exception_override:
                override_allowed, override_reason = self._can_attempt_exception_override(
                    "credit_overload",
                    str(student_id),
                    str(course_id),
                )
                if not override_allowed:
                    return {
                        "success": False,
                        "data": {
                            "reason": "override_requires_prior_validation",
                            "current": current_credits,
                            "limit": credit_limit,
                            "course_credits": course["credits"],
                            "exception_type": "credit_overload",
                        },
                        "error": override_reason,
                        "entity_ids": {student_id, course_id},
                        "metadata": {"exception_available": True, "exception_type": "credit_overload"},
                    }
                approved, reason = self._evaluate_exception("credit_overload", str(student_id))
                if not approved:
                    return {
                        "success": False,
                        "data": {"reason": "credit_exception_denied", "current": current_credits,
                                 "limit": credit_limit, "course_credits": course["credits"],
                                 "exception_available": True, "exception_type": "credit_overload"},
                        "error": f"Credit overload exception denied: {reason}",
                        "entity_ids": {student_id, course_id},
                        "metadata": {"exception_available": True, "exception_type": "credit_overload"},
                    }
            else:
                return {
                    "success": False,
                    "data": {"reason": "credit_limit_exceeded", "current": current_credits,
                             "limit": credit_limit, "course_credits": course["credits"],
                             "exception_available": True, "exception_type": "credit_overload"},
                    "error": f"Credit limit exceeded: {current_credits}+{course['credits']}={new_total} > {credit_limit}.",
                    "entity_ids": {student_id, course_id},
                    "metadata": {"exception_available": True, "exception_type": "credit_overload"},
                }

        # All checks passed — enroll
        new_enrollment_id = f"ENR-{len(self._world.get('enrollments', [])) + 1:05d}"
        new_enrollment = {
            "enrollment_id": new_enrollment_id,
            "student_id": student_id,
            "course_id": course_id,
            "semester": student.get("semester", 1),
            "grade": None,
            "status": "enrolled",
        }

        self._world["enrollments"].append(new_enrollment)
        course["current_enrollment"] += 1

        state_diff = {
            "enrollment_added": new_enrollment,
            "course_enrollment_updated": {
                "course_id": course_id,
                "new_enrollment_count": course["current_enrollment"],
            },
        }
        self._modified_entities[new_enrollment_id] = new_enrollment
        self._modified_entities[course_id] = {"current_enrollment": course["current_enrollment"]}

        return {
            "success": True,
            "data": {
                "message": f"Student {student_id} successfully enrolled in {course_id}.",
                "enrollment_id": new_enrollment_id,
                "course_name": course["name"],
                "credits": course["credits"],
                "new_credit_total": current_credits + course["credits"],
            },
            "entity_ids": {student_id, course_id, new_enrollment_id},
            "state_diff": state_diff,
        }

    
    # Tool 18: drop_course
    

    def _tool_drop_course(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Drop a student from a course."""
        student_id = arguments.get("student_id")
        course_id = arguments.get("course_id")

        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}
        if not course_id:
            return {"success": False, "data": {}, "error": "Missing required argument: course_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}

        course = self._find_course(str(course_id))
        if not course:
            return {"success": False, "data": {}, "error": f"Entity not found: {course_id}", "entity_ids": set()}

        # Check deadline
        if self._deadline_passed:
            return {
                "success": False,
                "data": {"reason": "deadline_passed"},
                "error": "Add/drop deadline has passed. Course drops are no longer permitted.",
                "entity_ids": {student_id, course_id},
            }

        # Find the enrollment
        enrollment = None
        for e in self._world.get("enrollments", []):
            if (e["student_id"] == student_id and e["course_id"] == course_id
                    and e["status"] == "enrolled"):
                enrollment = e
                break

        if not enrollment:
            return {
                "success": False,
                "data": {"reason": "not_enrolled"},
                "error": f"Student {student_id} is not currently enrolled in {course_id}.",
                "entity_ids": {student_id, course_id},
            }

        current_credits = self._get_current_credits(str(student_id))
        projected_credits = max(0, current_credits - int(course.get("credits", 0)))
        scholarship_risks: List[Dict[str, Any]] = []
        for scholarship in self._world.get("scholarships", []):
            if str(student_id) not in scholarship.get("beneficiaries", []):
                continue
            min_credits = int(scholarship.get("min_semester_credits", 0))
            if projected_credits < min_credits:
                scholarship_risks.append(
                    {
                        "scholarship_id": scholarship["scholarship_id"],
                        "projected_credits": projected_credits,
                        "required_credits": min_credits,
                    }
                )

        if scholarship_risks:
            checked_scholarship = any(
                self._audit_entry_succeeded(
                    "check_scholarship_compliance",
                    student_id=str(student_id),
                    scholarship_id=risk["scholarship_id"],
                )
                for risk in scholarship_risks
            ) or self._audit_entry_succeeded("search_scholarships", student_id=str(student_id))
            if not checked_scholarship:
                return {
                    "success": False,
                    "data": {
                        "reason": "scholarship_review_required",
                        "projected_credits": projected_credits,
                        "scholarship_risks": scholarship_risks,
                    },
                    "error": (
                        "Dropping this course may violate scholarship credit requirements. "
                        "Review scholarship compliance before attempting the drop."
                    ),
                    "entity_ids": {student_id, course_id, *[risk["scholarship_id"] for risk in scholarship_risks]},
                }

        # Execute drop
        enrollment["status"] = "dropped"
        enrollment["grade"] = "W"
        course["current_enrollment"] = max(0, course["current_enrollment"] - 1)

        new_credits = self._get_current_credits(str(student_id))

        state_diff = {
            "enrollment_dropped": {
                "enrollment_id": enrollment["enrollment_id"],
                "student_id": student_id,
                "course_id": course_id,
            },
            "course_enrollment_updated": {
                "course_id": course_id,
                "new_enrollment_count": course["current_enrollment"],
            },
        }
        self._modified_entities[enrollment["enrollment_id"]] = {"status": "dropped"}
        self._modified_entities[course_id] = {"current_enrollment": course["current_enrollment"]}

        return {
            "success": True,
            "data": {
                "message": f"Student {student_id} dropped from {course_id}.",
                "enrollment_id": enrollment["enrollment_id"],
                "course_name": course["name"],
                "credits_dropped": course["credits"],
                "new_credit_total": new_credits,
            },
            "entity_ids": {student_id, course_id, enrollment["enrollment_id"]},
            "state_diff": state_diff,
        }

    
    # Tool 19: transfer_hostel
    

    def _tool_transfer_hostel(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Transfer a student to a different hostel room."""
        student_id = arguments.get("student_id")
        target_room_id = arguments.get("target_room_id")

        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}
        if not target_room_id:
            return {"success": False, "data": {}, "error": "Missing required argument: target_room_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}

        target_room = self._find_room(str(target_room_id))
        if not target_room:
            return {"success": False, "data": {}, "error": f"Entity not found: {target_room_id}", "entity_ids": set()}

        target_block = self._find_block(target_room["block_id"])
        if not target_block:
            return {"success": False, "data": {}, "error": f"Block not found for room {target_room_id}", "entity_ids": set()}

        # Check fee clearance
        fee_record = self._find_fee_record(str(student_id))
        if fee_record and fee_record.get("amount_due", 0) > 0:
            return {
                "success": False,
                "data": {"reason": "fees_outstanding", "outstanding": fee_record["amount_due"],
                         "exception_available": True, "exception_type": "fee_deferral"},
                "error": f"Outstanding fees of INR {fee_record['amount_due']} must be cleared.",
                "entity_ids": {student_id, target_room_id},
                "metadata": {"exception_available": True, "exception_type": "fee_deferral"},
            }

        # Check gender restriction
        student_gender = student.get("gender", "")
        block_restriction = target_block.get("gender_restriction", "")
        if block_restriction and student_gender != block_restriction:
            return {
                "success": False,
                "data": {"reason": "gender_mismatch", "student_gender": student_gender,
                         "block_restriction": block_restriction},
                "error": f"Gender mismatch: student is {student_gender}, block {target_block['block_id']} is {block_restriction}-only.",
                "entity_ids": {student_id, target_room_id},
            }

        # Check room capacity
        if target_room["occupant_count"] >= target_room["capacity"]:
            return {
                "success": False,
                "data": {"reason": "room_full", "capacity": target_room["capacity"],
                         "current_occupants": target_room["occupant_count"]},
                "error": f"Room {target_room_id} is full ({target_room['occupant_count']}/{target_room['capacity']}).",
                "entity_ids": {student_id, target_room_id},
            }

        # Execute transfer
        old_room_id = student.get("hostel_id")
        state_diff_parts: Dict[str, Any] = {}

        # Remove from old room
        if old_room_id:
            old_room = self._find_room(old_room_id)
            if old_room:
                if student_id in old_room.get("current_occupants", []):
                    old_room["current_occupants"].remove(student_id)
                old_room["occupant_count"] = max(0, old_room["occupant_count"] - 1)
                state_diff_parts["old_room"] = {"room_id": old_room_id, "occupant_count": old_room["occupant_count"]}
                self._modified_entities[old_room_id] = {"occupant_count": old_room["occupant_count"]}

        # Add to new room
        target_room["current_occupants"].append(student_id)
        target_room["occupant_count"] += 1
        student["hostel_id"] = target_room_id

        state_diff_parts["new_room"] = {"room_id": target_room_id, "occupant_count": target_room["occupant_count"]}
        state_diff_parts["student"] = {"student_id": student_id, "hostel_id": target_room_id}

        self._modified_entities[target_room_id] = {"occupant_count": target_room["occupant_count"]}
        self._modified_entities[student_id] = {"hostel_id": target_room_id}

        return {
            "success": True,
            "data": {
                "message": f"Student {student_id} transferred to room {target_room_id}.",
                "old_room": old_room_id,
                "new_room": target_room_id,
                "block": target_block["name"],
            },
            "entity_ids": {student_id, target_room_id, old_room_id or ""},
            "state_diff": state_diff_parts,
        }

    
    # Tool 20: update_fee_record
    

    def _tool_update_fee_record(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Record a payment towards a student's outstanding fees."""
        student_id = arguments.get("student_id")
        payment_amount = arguments.get("payment_amount")

        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}
        if payment_amount is None:
            return {"success": False, "data": {}, "error": "Missing required argument: payment_amount", "entity_ids": set()}

        try:
            payment_amount = float(payment_amount)
        except (ValueError, TypeError):
            return {"success": False, "data": {}, "error": f"Type error: expected number for payment_amount, got {type(payment_amount).__name__}", "entity_ids": set()}

        if payment_amount <= 0:
            return {"success": False, "data": {}, "error": "Payment amount must be greater than 0.", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}

        fee_record = self._find_fee_record(str(student_id))
        if not fee_record:
            return {
                "success": False,
                "data": {"reason": "no_fee_record"},
                "error": f"No fee record found for student {student_id}.",
                "entity_ids": {student_id},
            }

        old_due = fee_record["amount_due"]
        old_paid = fee_record["amount_paid"]

        fee_record["amount_paid"] += payment_amount
        fee_record["amount_due"] = max(0, fee_record["amount_due"] - payment_amount)
        if fee_record["amount_due"] <= 0:
            fee_record["status"] = "paid"
        else:
            fee_record["status"] = "partial"

        state_diff = {
            "fee_record": {
                "record_id": fee_record["record_id"],
                "old_amount_due": old_due,
                "new_amount_due": fee_record["amount_due"],
                "old_amount_paid": old_paid,
                "new_amount_paid": fee_record["amount_paid"],
                "payment_amount": payment_amount,
            }
        }
        self._modified_entities[fee_record["record_id"]] = {
            "amount_due": fee_record["amount_due"],
            "amount_paid": fee_record["amount_paid"],
            "status": fee_record["status"],
        }

        return {
            "success": True,
            "data": {
                "message": f"Payment of INR {payment_amount} recorded for student {student_id}.",
                "record_id": fee_record["record_id"],
                "payment_amount": payment_amount,
                "new_amount_due": fee_record["amount_due"],
                "new_amount_paid": fee_record["amount_paid"],
                "status": fee_record["status"],
            },
            "entity_ids": {student_id, fee_record["record_id"]},
            "state_diff": state_diff,
        }

    
    # Tool 21: initiate_hostel_checkout
    

    def _tool_initiate_hostel_checkout(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Initiate hostel checkout for a student."""
        student_id = arguments.get("student_id")
        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}
        if not student.get("hostel_id"):
            return {
                "success": False,
                "data": {"reason": "no_hostel_allocation"},
                "error": f"Student {student_id} does not currently have a hostel allocation.",
                "entity_ids": {str(student_id)},
            }

        self._hostel_checkout_initiated[str(student_id)] = True
        checkout_key = f"{student_id}_checkout"
        self._modified_entities[checkout_key] = {
            "student_id": str(student_id),
            "checkout_initiated": True,
            "status": "requested",
        }
        return {
            "success": True,
            "data": {
                "student_id": str(student_id),
                "checkout_initiated": True,
                "hostel_id": student["hostel_id"],
                "status": "requested",
            },
            "entity_ids": {str(student_id), checkout_key, student["hostel_id"]},
            "state_diff": {"hostel_checkout": {"student_id": str(student_id), "status": "requested"}},
        }

    
    # Tool 22: clear_probation_hold
    

    def _tool_clear_probation_hold(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Clear the probation hold for an eligible student."""
        student_id = arguments.get("student_id")
        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}
        if student.get("academic_status") != "probation":
            return {
                "success": False,
                "data": {"reason": "not_on_probation"},
                "error": f"Student {student_id} is not on academic probation.",
                "entity_ids": {str(student_id)},
            }

        approved, reason = self._evaluate_exception("academic_probation_clearance", str(student_id))
        if not approved:
            return {
                "success": False,
                "data": {"reason": "clearance_denied"},
                "error": reason,
                "entity_ids": {str(student_id)},
            }

        student["academic_status"] = "active"
        self._probation_cleared[str(student_id)] = True
        self._modified_entities[str(student_id)] = {
            **self._modified_entities.get(str(student_id), {}),
            "academic_status": "active",
            "probation_cleared": True,
        }
        return {
            "success": True,
            "data": {
                "student_id": str(student_id),
                "academic_status": "active",
                "probation_cleared": True,
                "message": reason,
            },
            "entity_ids": {str(student_id)},
            "state_diff": {"student": {"student_id": str(student_id), "academic_status": "active"}},
        }

    
    # Tool 23: find_exam_alternatives
    

    def _tool_find_exam_alternatives(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Find valid alternative exam slots for a student's course."""
        student_id = arguments.get("student_id")
        course_id = arguments.get("course_id")
        if not student_id:
            return {"success": False, "data": {}, "error": "Missing required argument: student_id", "entity_ids": set()}
        if not course_id:
            return {"success": False, "data": {}, "error": "Missing required argument: course_id", "entity_ids": set()}

        student = self._find_student(str(student_id))
        exam = self._find_exam_for_course(str(course_id))
        if not student:
            return {"success": False, "data": {}, "error": f"Entity not found: {student_id}", "entity_ids": set()}
        if not exam:
            return {"success": False, "data": {}, "error": f"Exam not found for course {course_id}", "entity_ids": set()}

        alternatives: List[Dict[str, Any]] = []
        exam_entries = self._world.get("exam_schedule", [])
        candidate_dates = sorted({candidate["date"] for candidate in exam_entries})
        candidate_times = sorted({candidate["time_slot"] for candidate in exam_entries})
        candidate_rooms = sorted({candidate["room_id"] for candidate in exam_entries})

        for candidate_date in candidate_dates:
            if self._student_has_same_day_exam(str(student_id), candidate_date, exclude_course_id=str(course_id)):
                continue
            for candidate_time in candidate_times:
                for candidate_room in candidate_rooms:
                    available, _ = self._is_exam_slot_available(
                        str(course_id),
                        candidate_date,
                        candidate_time,
                        candidate_room,
                        exam["faculty_invigilator"],
                    )
                    if not available:
                        continue
                    impact = self._assess_reschedule_impact(
                        str(course_id),
                        candidate_date,
                        candidate_time,
                        candidate_room,
                    )
                    if impact["would_create_new_conflict"]:
                        continue
                    alternatives.append({
                        "date": candidate_date,
                        "time_slot": candidate_time,
                        "room_id": candidate_room,
                        "faculty_invigilator": exam["faculty_invigilator"],
                        "impact_summary": {
                            "impacted_students": impact["impacted_students"],
                            "new_same_slot_conflicts": 0,
                            "new_same_day_violations": 0,
                        },
                    })
                    if len(alternatives) >= 5:
                        break
                if len(alternatives) >= 5:
                    break
            if len(alternatives) >= 5:
                break

        return {
            "success": True,
            "data": {
                "student_id": str(student_id),
                "course_id": str(course_id),
                "current_exam": dict(exam),
                "alternatives": alternatives,
                "total": len(alternatives),
            },
            "entity_ids": {str(student_id), str(course_id), exam["exam_id"]},
        }

    
    # Tool 24: check_reschedule_impact
    

    def _tool_check_reschedule_impact(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dry-run an exam move and report whether it is globally safe."""
        course_id = arguments.get("course_id")
        new_date = arguments.get("new_date")
        new_time_slot = arguments.get("new_time_slot")
        new_room_id = arguments.get("new_room_id")
        if not course_id:
            return {"success": False, "data": {}, "error": "Missing required argument: course_id", "entity_ids": set()}
        if not new_date:
            return {"success": False, "data": {}, "error": "Missing required argument: new_date", "entity_ids": set()}
        if not new_time_slot:
            return {"success": False, "data": {}, "error": "Missing required argument: new_time_slot", "entity_ids": set()}
        if not new_room_id:
            return {"success": False, "data": {}, "error": "Missing required argument: new_room_id", "entity_ids": set()}

        exam = self._find_exam_for_course(str(course_id))
        if not exam:
            return {"success": False, "data": {}, "error": f"Exam not found for course {course_id}", "entity_ids": set()}

        impact = self._assess_reschedule_impact(
            str(course_id),
            str(new_date),
            str(new_time_slot),
            str(new_room_id),
        )
        return {
            "success": True,
            "data": {
                "course_id": str(course_id),
                "exam_id": exam["exam_id"],
                "current_slot": {
                    "date": exam["date"],
                    "time_slot": exam["time_slot"],
                    "room_id": exam["room_id"],
                },
                "proposed_slot": {
                    "date": str(new_date),
                    "time_slot": str(new_time_slot),
                    "room_id": str(new_room_id),
                },
                **impact,
            },
            "entity_ids": {str(course_id), exam["exam_id"], *impact["impacted_students"]},
        }

    
    # Tool 25: reschedule_exam
    

    def _tool_reschedule_exam(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Reschedule an exam to a validated slot."""
        course_id = arguments.get("course_id")
        new_date = arguments.get("new_date")
        new_time_slot = arguments.get("new_time_slot")
        new_room_id = arguments.get("new_room_id")
        if not course_id:
            return {"success": False, "data": {}, "error": "Missing required argument: course_id", "entity_ids": set()}
        if not new_date:
            return {"success": False, "data": {}, "error": "Missing required argument: new_date", "entity_ids": set()}
        if not new_time_slot:
            return {"success": False, "data": {}, "error": "Missing required argument: new_time_slot", "entity_ids": set()}
        if not new_room_id:
            return {"success": False, "data": {}, "error": "Missing required argument: new_room_id", "entity_ids": set()}

        exam = self._find_exam_for_course(str(course_id))
        if not exam:
            return {"success": False, "data": {}, "error": f"Exam not found for course {course_id}", "entity_ids": set()}

        impact = self._assess_reschedule_impact(
            str(course_id),
            str(new_date),
            str(new_time_slot),
            str(new_room_id),
        )
        if not impact["slot_available"]:
            return {"success": False, "data": {"reason": "slot_unavailable"}, "error": impact["availability_reason"], "entity_ids": {str(course_id), exam["exam_id"]}}
        if impact["same_slot_conflicts"] or impact["same_day_violations"]:
            return {
                "success": False,
                "data": {
                    "reason": "creates_student_conflict",
                    **impact,
                },
                "error": (
                    "Reschedule blocked: the proposed slot creates new student conflicts. "
                    "Use check_reschedule_impact or find_exam_alternatives to choose a safe slot."
                ),
                "entity_ids": {str(course_id), exam["exam_id"], *impact["impacted_students"]},
            }

        impacted_students = impact["impacted_students"]
        old_exam = dict(exam)
        exam["date"] = str(new_date)
        exam["time_slot"] = str(new_time_slot)
        exam["room_id"] = str(new_room_id)
        self._modified_entities[exam["exam_id"]] = {
            "course_id": str(course_id),
            "date": str(new_date),
            "time_slot": str(new_time_slot),
            "room_id": str(new_room_id),
        }
        return {
            "success": True,
            "data": {
                "course_id": str(course_id),
                "exam_id": exam["exam_id"],
                "old_slot": {
                    "date": old_exam["date"],
                    "time_slot": old_exam["time_slot"],
                    "room_id": old_exam["room_id"],
                },
                "new_slot": {
                    "date": exam["date"],
                    "time_slot": exam["time_slot"],
                    "room_id": exam["room_id"],
                },
                "impacted_students": impacted_students,
                "same_day_warnings": [],
            },
            "entity_ids": {str(course_id), exam["exam_id"], *impacted_students},
            "state_diff": {"exam_rescheduled": {"exam_id": exam["exam_id"], "old": old_exam, "new": dict(exam)}},
        }

    
    # Tool 26: submit_final_response
    

    def _tool_submit_final_response(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Terminal action — submit the final response and trigger grading."""
        message = arguments.get("message", "")
        resolution_summary = arguments.get("resolution_summary", {})

        if not message:
            return {"success": False, "data": {}, "error": "Missing required argument: message", "entity_ids": set()}
        if not isinstance(resolution_summary, dict):
            return {"success": False, "data": {}, "error": "Type error: resolution_summary must be an object/dict", "entity_ids": set()}

        # Store final response data
        self._final_response_data = {
            "message": message,
            "resolution_summary": resolution_summary,
        }

        # Set episode as done
        self._done = True
        self._episode_active = False

        # Log the audit entry BEFORE running the grader so the grader
        # can see that submit_final_response was called successfully.
        self._log_audit(
            "submit_final_response", arguments,
            "Final response submitted.", True,
        )

        # Run grader
        grader_score = self._run_grader()

        return {
            "success": True,
            "data": {
                "message": "Final response submitted. Episode complete.",
                "grader_score": grader_score,
                "grader_result": self._grader_result,
            },
            "entity_ids": set(),
            "state_diff": {"episode_ended": True, "grader_score": grader_score},
        }

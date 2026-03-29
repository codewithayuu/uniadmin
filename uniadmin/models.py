from __future__ import annotations

from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field

TOOL_NAMES: List[str] = [
    # Search Tools (read-only, no state mutation)
    "search_students",
    "search_courses",
    "search_faculty",
    "search_regulations",
    "search_scholarships",
    # Retrieve Tools (single-entity lookup, no state mutation)
    "get_student_record",
    "get_course_details",
    "get_enrollment_history",
    "get_fee_status",
    "get_hostel_details",
    "get_exam_schedule",
    # Validate Tools (check feasibility, no state mutation)
    "check_prerequisites",
    "check_credit_limits",
    "check_seat_availability",
    "check_fee_clearance",
    "check_scholarship_compliance",
    # Modify Tools (state mutation — tracked in audit log)
    "enroll_student",
    "drop_course",
    "transfer_hostel",
    "update_fee_record",
    "initiate_hostel_checkout",
    "clear_probation_hold",
    "find_exam_alternatives",
    "check_reschedule_impact",
    "reschedule_exam",
    # Special Tools
    "submit_final_response",
]

TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    # ── Search Tools ────────────────────────────────────────────────────────
    "search_students": {
        "description": (
            "Search students by query string and/or filters. "
            "Returns max 10 results per page and includes pagination metadata "
            "such as has_more and next_page."
        ),
        "parameters": {
            "query": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Search query matching student name or student_id",
            },
            "filters": {
                "type": "object",
                "required": False,
                "default": {},
                "description": (
                    "Filter dict with optional keys: department, semester (int), "
                    "min_cgpa (float), max_cgpa (float), academic_status"
                ),
            },
            "page": {
                "type": "integer",
                "required": False,
                "default": 1,
                "description": "Page number for pagination (10 results per page)",
            },
        },
        "mutates_state": False,
    },
    "search_courses": {
        "description": (
            "Search courses by query string and/or filters. "
            "Returns max 10 results per page and includes pagination metadata "
            "such as has_more and next_page."
        ),
        "parameters": {
            "query": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Search query matching course name or course_id",
            },
            "filters": {
                "type": "object",
                "required": False,
                "default": {},
                "description": (
                    "Filter dict with optional keys: department, semester_offered (int), "
                    "min_credits (int), max_credits (int), has_availability (bool)"
                ),
            },
            "page": {
                "type": "integer",
                "required": False,
                "default": 1,
                "description": "Page number for pagination (10 results per page)",
            },
        },
        "mutates_state": False,
    },
    "search_faculty": {
        "description": "Search faculty members by query and/or department.",
        "parameters": {
            "query": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Search query matching faculty name or faculty_id",
            },
            "department": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Filter by department name",
            },
        },
        "mutates_state": False,
    },
    "search_regulations": {
        "description": (
            "Search university regulations by keyword and/or applicable entity type."
        ),
        "parameters": {
            "keyword": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Keyword to search in regulation title and description",
            },
            "applicable_to": {
                "type": "string",
                "required": False,
                "default": "",
                "description": (
                    "Filter by applicable entity type: "
                    "student, course, faculty, hostel, exam"
                ),
            },
        },
        "mutates_state": False,
    },
    "search_scholarships": {
        "description": (
            "Search scholarships that a specific student is eligible for "
            "based on their CGPA and completed credits."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "Student ID to check scholarship eligibility for",
            },
        },
        "mutates_state": False,
    },
    # ── Retrieve Tools ──────────────────────────────────────────────────────
    "get_student_record": {
        "description": (
            "Retrieve the full record for a specific student including personal "
            "info, department, semester, CGPA, credits, academic status, and "
            "hostel allocation."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier (e.g., 'STU-001')",
            },
        },
        "mutates_state": False,
    },
    "get_course_details": {
        "description": (
            "Retrieve full details for a specific course including name, "
            "department, credits, prerequisites, capacity, current enrollment "
            "count, and enrolled student list."
        ),
        "parameters": {
            "course_id": {
                "type": "string",
                "required": True,
                "description": "The course's unique identifier (e.g., 'CSE-301')",
            },
        },
        "mutates_state": False,
    },
    "get_enrollment_history": {
        "description": (
            "Retrieve all enrollment records for a specific student across all "
            "semesters, including grades and enrollment status."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
        },
        "mutates_state": False,
    },
    "get_fee_status": {
        "description": (
            "Retrieve fee records and outstanding balances for a specific student, "
            "including amount due, amount paid, due date, and payment status."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
        },
        "mutates_state": False,
    },
    "get_hostel_details": {
        "description": (
            "Retrieve current hostel allocation details for a specific student, "
            "including block, room, capacity, and occupancy."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
        },
        "mutates_state": False,
    },
    "get_exam_schedule": {
        "description": (
            "Retrieve exam schedule entries. Provide either student_id (to get "
            "all exams for courses the student is enrolled in) or course_id "
            "(to get the exam for that specific course). At least one must be "
            "provided."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": False,
                "default": "",
                "description": (
                    "Student ID — returns exams for all courses the student "
                    "is currently enrolled in"
                ),
            },
            "course_id": {
                "type": "string",
                "required": False,
                "default": "",
                "description": "Course ID — returns exam schedule for this course",
            },
        },
        "mutates_state": False,
    },
    # ── Validate Tools ──────────────────────────────────────────────────────
    "check_prerequisites": {
        "description": (
            "Check whether a student has completed all prerequisites for a "
            "given course. Returns pass/fail and lists any missing prerequisites."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
            "course_id": {
                "type": "string",
                "required": True,
                "description": "The course to check prerequisites for",
            },
        },
        "mutates_state": False,
    },
    "check_credit_limits": {
        "description": (
            "Check a student's current credit load against the semester credit "
            "limit. Returns current credits, credit limit, and remaining headroom."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
            "semester": {
                "type": "integer",
                "required": False,
                "description": (
                    "Semester number to check (defaults to student's current semester)"
                ),
            },
        },
        "mutates_state": False,
    },
    "check_seat_availability": {
        "description": (
            "Check how many seats are available in a specific course. Returns "
            "max capacity, current enrollment, and available seats."
        ),
        "parameters": {
            "course_id": {
                "type": "string",
                "required": True,
                "description": "The course's unique identifier",
            },
        },
        "mutates_state": False,
    },
    "check_fee_clearance": {
        "description": (
            "Check whether a student has any outstanding fees that would block "
            "administrative actions like enrollment or hostel allocation."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
        },
        "mutates_state": False,
    },
    "check_scholarship_compliance": {
        "description": (
            "Check whether a student still meets the minimum credit and CGPA "
            "requirements for a specific scholarship."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
            "scholarship_id": {
                "type": "string",
                "required": True,
                "description": "The scholarship's unique identifier",
            },
        },
        "mutates_state": False,
    },
    # ── Modify Tools ────────────────────────────────────────────────────────
    "enroll_student": {
        "description": (
            "Enroll a student in a course. Validates prerequisites, seat "
            "availability, credit limits, and fee clearance before enrolling. "
            "If validation fails, returns error with details. Use "
            "exception_override=true to request a policy exception."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
            "course_id": {
                "type": "string",
                "required": True,
                "description": "The course to enroll in",
            },
            "exception_override": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": (
                    "Set to true to request an exception override when "
                    "enrollment was denied due to a policy restriction"
                ),
            },
        },
        "mutates_state": True,
    },
    "drop_course": {
        "description": (
            "Drop a student from a course they are currently enrolled in. "
            "Updates enrollment status and adjusts course enrollment count."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
            "course_id": {
                "type": "string",
                "required": True,
                "description": "The course to drop",
            },
            "exception_override": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Set to true to request an exception override",
            },
        },
        "mutates_state": True,
    },
    "transfer_hostel": {
        "description": (
            "Transfer a student to a different hostel room. Validates gender "
            "restrictions, room capacity, and fee clearance before transferring."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
            "target_room_id": {
                "type": "string",
                "required": True,
                "description": "The target room's unique identifier (e.g., 'RM-101')",
            },
            "exception_override": {
                "type": "boolean",
                "required": False,
                "default": False,
                "description": "Set to true to request an exception override",
            },
        },
        "mutates_state": True,
    },
    "update_fee_record": {
        "description": (
            "Record a payment towards a student's outstanding fees. Updates the "
            "fee record with the payment amount and recalculates balance."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
            "payment_amount": {
                "type": "number",
                "required": True,
                "description": "The payment amount in INR (must be > 0)",
            },
        },
        "mutates_state": True,
    },
    "initiate_hostel_checkout": {
        "description": (
            "Initiate hostel checkout for a graduating student. Records the "
            "checkout request and target checkout date."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
        },
        "mutates_state": True,
    },
    "clear_probation_hold": {
        "description": (
            "Clear a student's probation hold if they satisfy the recovery policy."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
        },
        "mutates_state": True,
    },
    "find_exam_alternatives": {
        "description": (
            "Find valid alternative exam slots for a student's conflicting course. "
            "Results respect room capacity, faculty availability, and the "
            "no-two-exams-same-day rule across all impacted students."
        ),
        "parameters": {
            "student_id": {
                "type": "string",
                "required": True,
                "description": "The student's unique identifier",
            },
            "course_id": {
                "type": "string",
                "required": True,
                "description": "The course whose exam needs a valid alternative",
            },
        },
        "mutates_state": False,
    },
    "check_reschedule_impact": {
        "description": (
            "Dry-run an exam move before committing it. Returns whether the "
            "slot is available and whether moving the course would create new "
            "same-slot or same-day conflicts for any enrolled students."
        ),
        "parameters": {
            "course_id": {
                "type": "string",
                "required": True,
                "description": "Course whose exam may be rescheduled",
            },
            "new_date": {
                "type": "string",
                "required": True,
                "description": "Candidate exam date in YYYY-MM-DD format",
            },
            "new_time_slot": {
                "type": "string",
                "required": True,
                "description": "Candidate exam time slot",
            },
            "new_room_id": {
                "type": "string",
                "required": True,
                "description": "Candidate exam room identifier",
            },
        },
        "mutates_state": False,
    },
    "reschedule_exam": {
        "description": (
            "Reschedule a course exam to a specific alternative slot. "
            "Validates room availability, faculty availability, and global "
            "student conflict constraints before mutating the exam schedule."
        ),
        "parameters": {
            "course_id": {
                "type": "string",
                "required": True,
                "description": "Course whose exam should be rescheduled",
            },
            "new_date": {
                "type": "string",
                "required": True,
                "description": "New exam date in YYYY-MM-DD format",
            },
            "new_time_slot": {
                "type": "string",
                "required": True,
                "description": "New exam time slot",
            },
            "new_room_id": {
                "type": "string",
                "required": True,
                "description": "Target exam room identifier",
            },
        },
        "mutates_state": True,
    },
    # ── Special Tools ───────────────────────────────────────────────────────
    "submit_final_response": {
        "description": (
            "TERMINAL ACTION. Submit the final response to the student and end "
            "the episode. This triggers the grader for evaluation. The agent "
            "MUST call this tool to complete any task. The resolution_summary "
            "should be a structured dict of all actions taken and their outcomes."
        ),
        "parameters": {
            "message": {
                "type": "string",
                "required": True,
                "description": (
                    "Final message to the student summarizing the resolution "
                    "and any actions taken on their behalf"
                ),
            },
            "resolution_summary": {
                "type": "object",
                "required": True,
                "description": (
                    "Structured dict summarizing actions taken, e.g.: "
                    '{"enrolled": [{"student_id": "...", "course_id": "..."}], '
                    '"dropped": [...], "fees_paid": [...], "issues_found": [...]}'
                ),
            },
        },
        "mutates_state": False,
    },
}

TASK_CONFIGS: Dict[str, Dict[str, Any]] = {
    "task_1_course_inquiry": {
        "difficulty": "easy",
        "max_steps": 15,
        "deadline_step": None,
        "description": (
            "A student asks about available elective courses in Computer Science "
            "for next semester that don't conflict with their current schedule "
            "and fit within their credit limit."
        ),
    },
    "task_2_hostel_allocation": {
        "difficulty": "easy",
        "max_steps": 15,
        "deadline_step": None,
        "description": (
            "A new student requests hostel accommodation. Find a suitable room "
            "matching gender restriction, verify fee clearance, check room "
            "availability, and process the allocation."
        ),
    },
    "task_3_course_switch": {
        "difficulty": "medium",
        "max_steps": 20,
        "deadline_step": 16,
        "description": (
            "A student wants to switch from Course A to Course B. The add/drop "
            "deadline is at step 16 — after which drop_course and enroll_student "
            "will be rejected. The agent must complete all validations and "
            "execute the switch before the deadline."
        ),
    },
    "task_4_concurrent_conflict": {
        "difficulty": "medium",
        "max_steps": 25,
        "deadline_step": None,
        "description": (
            "Two students both request enrollment in a course with exactly 1 "
            "seat remaining. One student has a scholarship dependency requiring "
            "this course. The agent must correctly prioritize based on policy "
            "(scholarship dependency) over merit (CGPA)."
        ),
    },
    "task_5_graduation_crisis": {
        "difficulty": "hard",
        "max_steps": 40,
        "deadline_step": None,
        "description": (
            "Final-semester student 'Karthik' requests a graduation eligibility "
            "check. On the surface he appears fine, but there are 6 hidden "
            "blockers that the agent must discover through careful investigation. "
            "A dynamic regulation change is triggered mid-episode when the agent "
            "checks credit limits, and the agent must resolve each blocker via "
            "real administrative actions."
        ),
    },
    "task_6_bulk_schedule": {
        "difficulty": "hard",
        "max_steps": 50,
        "deadline_step": None,
        "description": (
            "8 students have reported exam timetable clashes. Each involves 2 "
            "exams scheduled at the same time. The agent must resolve ALL "
            "conflicts by finding and applying alternative exam slots, "
            "constrained by room capacity, faculty availability, and the "
            "no-two-exams-same-day rule. Use impact checks to avoid creating "
            "new conflicts for other enrolled students."
        ),
    },
}


REWARD_TOOL_SUCCESS: float = 0.03
REWARD_NEW_INFO: float = 0.05
PENALTY_DUPLICATE_CALL: float = -0.05
PENALTY_TOOL_ERROR: float = -0.03
PENALTY_STATE_CORRUPTION: float = -0.30
PENALTY_DEADLINE_EXCEEDED: float = -0.10

DEFAULT_CREDIT_LIMIT: int = 21
ELEVATED_CREDIT_LIMIT: int = 24
class UniAdminAction(BaseModel):


    tool_name: str = Field(
        ...,
        description="Name of the tool to invoke (must be one of the available tools)",
    )
    arguments: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific arguments as a dictionary",
    )
    message_to_student: Optional[str] = Field(
        None,
        description="Optional message to relay to the student",
    )

    model_config = {"extra": "forbid"}


class UniAdminObservation(BaseModel):

    done: bool = Field(
        False,
        description="Whether the episode has ended",
    )
    reward: Optional[Union[float, int]] = Field(
        None,
        description="Reward for this step (None on reset, float on step)",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata (exception info, grader breakdown, etc.)",
    )

    task_id: str = Field(
        "",
        description="Identifier for the current task",
    )
    task_description: str = Field(
        "",
        description="Human-readable description of what the agent must accomplish",
    )
    tool_result: str = Field(
        "",
        description="Serialized result of the last tool call (empty on reset)",
    )
    tool_success: bool = Field(
        True,
        description="Whether the last tool call executed without error",
    )
    error_message: Optional[str] = Field(
        None,
        description="Descriptive error message when tool_success is False",
    )
    current_step: int = Field(
        0,
        description="Current step number in the episode (0 on reset)",
    )
    steps_remaining: Optional[int] = Field(
        None,
        description="Steps until deadline (None if task has no deadline)",
    )
    notifications: List[str] = Field(
        default_factory=list,
        description="Dynamic notifications (regulation changes, warnings, etc.)",
    )
    available_tools: List[str] = Field(
        default_factory=lambda: list(TOOL_NAMES),
        description="List of all available tool names",
    )

    model_config = {"extra": "allow"}


class UniAdminState(BaseModel):


    task_id: str = Field(
        "",
        description="Identifier for the current task",
    )
    step_count: int = Field(
        0,
        description="Total number of steps taken in this episode",
    )
    modified_entities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Only entities that have been modified since reset()",
    )
    state_hash: str = Field(
        "",
        description="SHA-256 hash of the full entity graph for integrity checks",
    )
    audit_log: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Chronological log of all tool calls, arguments, and results",
    )
    episode_active: bool = Field(
        False,
        description="Whether an episode is currently in progress",
    )

    model_config = {"extra": "allow"}


class TaskInfo(BaseModel):

    task_id: str = Field(..., description="Unique task identifier")
    description: str = Field(..., description="Human-readable task description")
    difficulty: str = Field(..., description="Task difficulty: easy, medium, or hard")
    max_steps: int = Field(..., description="Maximum steps allowed for this task")
    deadline_step: Optional[int] = Field(
        None,
        description="Step number at which time-sensitive actions become invalid",
    )
    action_schema: Dict[str, Any] = Field(
        default_factory=lambda: {
            "tool_name": "string (one of available tools)",
            "arguments": "object (tool-specific)",
            "message_to_student": "string (optional)",
        },
        description="Schema for the action expected by this task",
    )



def format_tools_for_prompt() -> str:

    lines: List[str] = []
    for i, (name, schema) in enumerate(TOOL_SCHEMAS.items(), 1):
        lines.append(f"{i}. {name}")
        lines.append(f"   Description: {schema['description']}")
        lines.append("   Parameters:")
        for pname, pinfo in schema["parameters"].items():
            req_label = "REQUIRED" if pinfo.get("required", False) else "optional"
            default_str = ""
            if "default" in pinfo and not pinfo.get("required", False):
                default_str = f", default={pinfo['default']!r}"
            lines.append(
                f"     - {pname} ({pinfo['type']}, {req_label}{default_str}): "
                f"{pinfo['description']}"
            )
        state_note = "YES — mutates state" if schema["mutates_state"] else "no"
        lines.append(f"   Mutates state: {state_note}")
        lines.append("")
    return "\n".join(lines)

def get_task_list() -> List[TaskInfo]:
    return [
        TaskInfo(
            task_id=task_id,
            description=config["description"],
            difficulty=config["difficulty"],
            max_steps=config["max_steps"],
            deadline_step=config.get("deadline_step"),
        )
        for task_id, config in TASK_CONFIGS.items()
    ]

from __future__ import annotations

from typing import Any, Dict, List, Optional

from uniadmin.graders.base_grader import MIN_INTERIOR_SCORE
from uniadmin.graders.grader_task_1 import grade_task_1
from uniadmin.graders.grader_task_2 import grade_task_2
from uniadmin.graders.grader_task_3 import grade_task_3
from uniadmin.graders.grader_task_4 import grade_task_4
from uniadmin.graders.grader_task_5 import grade_task_5
from uniadmin.graders.grader_task_6 import grade_task_6


GRADER_MAP = {
    "task_1_course_inquiry": grade_task_1,
    "task_2_hostel_allocation": grade_task_2,
    "task_3_course_switch": grade_task_3,
    "task_4_concurrent_conflict": grade_task_4,
    "task_5_graduation_crisis": grade_task_5,
    "task_6_bulk_schedule": grade_task_6,
}


def _stub_grader(
    audit_log: List[Dict[str, Any]],
    world_state: Dict[str, Any],
    modified_entities: Dict[str, Any],
    task_refs: Dict[str, Any],
    final_response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "score": MIN_INTERIOR_SCORE,
        "raw_score": 0.0,
        "total_penalties": 0.0,
        "breakdown": {},
        "penalties": [],
    }


def dispatch_grader(
    task_id: str,
    audit_log: List[Dict[str, Any]],
    world_state: Dict[str, Any],
    modified_entities: Dict[str, Any],
    task_refs: Dict[str, Any],
    final_response: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    grader_fn = GRADER_MAP.get(task_id, _stub_grader)
    return grader_fn(audit_log, world_state, modified_entities, task_refs, final_response)

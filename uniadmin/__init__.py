"""UniAdmin - University Administrative Operations Environment for OpenEnv.

A fully simulated university administrative operations environment where an AI
agent acts as a university admin desk officer processing student requests across
~4,000 interconnected entities (students, courses, faculty, hostels, fees,
scholarships, regulations).
"""

from uniadmin.models import (
    UniAdminAction,
    UniAdminObservation,
    UniAdminState,
    TaskInfo,
    TOOL_NAMES,
    TOOL_SCHEMAS,
    TASK_CONFIGS,
    format_tools_for_prompt,
)

__all__ = [
    "UniAdminAction",
    "UniAdminObservation",
    "UniAdminState",
    "TaskInfo",
    "TOOL_NAMES",
    "TOOL_SCHEMAS",
    "TASK_CONFIGS",
    "format_tools_for_prompt",
]

__version__ = "1.0.0"

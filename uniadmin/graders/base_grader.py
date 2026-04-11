from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

MIN_INTERIOR_SCORE = 0.01
MAX_INTERIOR_SCORE = 0.99


def normalize_score(score: float) -> float:
    return max(MIN_INTERIOR_SCORE, min(MAX_INTERIOR_SCORE, score))


def tool_was_called(
    audit_log: List[Dict[str, Any]],
    tool_name: str,
    args_filter: Optional[Dict[str, Any]] = None,
) -> bool:
    for entry in audit_log:
        if entry.get("tool_name") != tool_name:
            continue
        if entry.get("success") is False:
            continue
        if args_filter:
            args = entry.get("arguments", {})
            if all(args.get(k) == v for k, v in args_filter.items()):
                return True
        else:
            return True
    return False


def tool_succeeded(
    audit_log: List[Dict[str, Any]],
    tool_name: str,
    args_filter: Optional[Dict[str, Any]] = None,
) -> bool:
    
    for entry in audit_log:
        if entry.get("tool_name") != tool_name:
            continue
        if entry.get("success") is not True:
            continue
        if args_filter:
            args = entry.get("arguments", {})
            if all(args.get(k) == v for k, v in args_filter.items()):
                return True
        else:
            return True
    return False


def get_step_of_tool_call(
    audit_log: List[Dict[str, Any]],
    tool_name: str,
    args_filter: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    for entry in audit_log:
        if entry.get("tool_name") != tool_name:
            continue
        if entry.get("success") is not True:
            continue
        if args_filter:
            args = entry.get("arguments", {})
            if all(args.get(k) == v for k, v in args_filter.items()):
                return entry.get("step")
        else:
            return entry.get("step")
    return None


def count_duplicate_calls(audit_log: List[Dict[str, Any]]) -> int:
    seen: Set[Tuple[str, str]] = set()
    duplicates = 0
    for entry in audit_log:
        tool_name = entry.get("tool_name", "")
        args_hash = hashlib.md5(
            json.dumps(entry.get("arguments", {}), sort_keys=True, default=str).encode()
        ).hexdigest()
        sig = (tool_name, args_hash)
        if sig in seen:
            duplicates += 1
        else:
            seen.add(sig)
    return duplicates


def compute_rubric_score(
    criteria_results: Dict[str, Tuple[bool, float]],
    penalties: List[Tuple[str, float]],
) -> Dict[str, Any]:
    breakdown = {}
    raw_score = 0.0

    for name, (passed, points) in criteria_results.items():
        breakdown[name] = {
            "passed": passed,
            "points": points if passed else 0.0,
            "max_points": points,
        }
        if passed:
            raw_score += points

    total_penalties = 0.0
    penalty_details = []
    for pname, pvalue in penalties:
        total_penalties += pvalue
        penalty_details.append({"name": pname, "value": pvalue})

    final_score = normalize_score(raw_score + total_penalties)

    return {
        "score": final_score,
        "raw_score": raw_score,
        "total_penalties": total_penalties,
        "breakdown": breakdown,
        "penalties": penalty_details,
    }

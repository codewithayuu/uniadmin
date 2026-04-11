"""UniAdmin baseline inference runner.

Runs either:
1. an OpenAI-compatible model against the HTTP environment, or
2. a deterministic mock agent for no-key local testing.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from openai import OpenAI

from uniadmin.client import UniAdminClient
from uniadmin.models import TASK_CONFIGS, UniAdminObservation, format_tools_for_prompt

ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "outputs" / "evals" / "inference_results.json"

API_BASE_URL = os.environ.get("API_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4o")
API_KEY = os.environ.get("HF_TOKEN", os.environ.get("OPENAI_API_KEY", ""))
ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "")
TEMPERATURE = 0.0
MAX_TOKENS = 2048
GLOBAL_MAX_STEPS = 30

SYSTEM_PROMPT = """You are a university administrative desk officer. Process each request using the available tools.

Rules:
1. Verify before mutating.
2. Respect fees, prerequisites, schedules, deadlines, and policy constraints.
3. Use submit_final_response only when you are done.
4. Respond with exactly one JSON object on one line:
{"tool_name":"<tool_name>","arguments":{...}}

Available tools:
""" + format_tools_for_prompt()

MOCK_ACTIONS: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["llm", "mock"], default="llm")
    parser.add_argument("--env-base-url", default=ENV_BASE_URL)
    return parser.parse_args()


def resolve_agent_mode(requested_agent: str) -> Tuple[str, Optional[str]]:
    if requested_agent == "mock":
        return "mock", None

    api_key = os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY")
    if api_key:
        return "llm", None

    return "mock", (
        "No HF_TOKEN or OPENAI_API_KEY detected; falling back to mock mode for submission-safe inference."
    )


def parse_model_action(response_text: str) -> Tuple[str, Dict[str, Any]]:
    text = response_text.strip()
    try:
        data = json.loads(text)
        if isinstance(data, dict) and "tool_name" in data:
            return str(data["tool_name"]), dict(data.get("arguments", {}))
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            data = json.loads(match.group(0))
            if isinstance(data, dict) and "tool_name" in data:
                return str(data["tool_name"]), dict(data.get("arguments", {}))
        except json.JSONDecodeError:
            pass

    return "submit_final_response", {
        "message": "Unable to continue because the model output was not valid JSON.",
        "resolution_summary": {"status": "parser_fallback"},
    }


def format_observation(obs: UniAdminObservation) -> str:
    parts = [f"Task: {obs.task_id}", f"Step: {obs.current_step}", f"Success: {obs.tool_success}"]
    if obs.tool_result:
        parts.append(f"Tool result: {obs.tool_result[:3000]}")
    if obs.error_message:
        parts.append(f"Error: {obs.error_message}")
    if obs.notifications:
        parts.append("Notifications: " + " | ".join(obs.notifications))
    if obs.steps_remaining is not None:
        parts.append(f"Steps until deadline: {obs.steps_remaining}")
    return "\n".join(parts)


def wait_for_env(base_url: str, timeout_seconds: float = 30.0) -> None:
    client = UniAdminClient(base_url=base_url, timeout=5.0)
    deadline = time.time() + timeout_seconds
    last_error = "environment did not start"
    while time.time() < deadline:
        try:
            client.health()
            return
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)
            time.sleep(1.0)
    raise RuntimeError(last_error)


def boot_local_server() -> Tuple[str, subprocess.Popen[bytes]]:
    base_url = "http://127.0.0.1:7860"
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "uniadmin.server.app:app", "--host", "127.0.0.1", "--port", "7860"],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    wait_for_env(base_url)
    return base_url, process


def build_openai_client() -> OpenAI:
    api_key = os.environ.get("HF_TOKEN") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Set either HF_TOKEN or OPENAI_API_KEY before running LLM inference."
        )
    return OpenAI(base_url=API_BASE_URL, api_key=api_key)


def llm_next_action(client: OpenAI, messages: List[Dict[str, Any]]) -> Tuple[str, Dict[str, Any], str]:
    completion = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        temperature=TEMPERATURE,
        max_tokens=MAX_TOKENS,
        stream=False,
    )
    response_text = completion.choices[0].message.content or ""
    tool_name, arguments = parse_model_action(response_text)
    return tool_name, arguments, response_text


def run_task_with_mock(env: UniAdminClient, task_id: str) -> Dict[str, Any]:
    obs = env.reset(task_id=task_id)
    refs = dict(obs.metadata.get("task_refs", {}))
    steps = 0
    if task_id == "task_1_course_inquiry":
        student_id = refs["student_id"]
        search_results: Dict[str, Any] = {}
        actions = [
            ("get_student_record", {"student_id": student_id}),
            ("get_enrollment_history", {"student_id": student_id}),
            ("search_courses", {"filters": {"department": "DEPT-CS", "semester_offered": refs.get("target_semester", 6)}}),
            ("get_exam_schedule", {"student_id": student_id}),
            ("check_credit_limits", {"student_id": student_id}),
        ]
        for tool_name, arguments in actions:
            steps += 1
            obs = env.step(tool_name=tool_name, arguments=arguments)
            if tool_name == "search_courses":
                search_results = json.loads(obs.tool_result) if obs.tool_result else {}
        steps += 1
        obs = env.step(
            tool_name="submit_final_response",
            arguments={
                "message": "Available CS electives identified.",
                "resolution_summary": {
                    "available_courses": [
                        course["course_id"] for course in search_results.get("results", [])
                    ],
                },
            },
        )
    elif task_id == "task_2_hostel_allocation":
        student_id = refs["student_id"]
        actions = [
            ("get_student_record", {"student_id": student_id}),
            ("check_fee_clearance", {"student_id": student_id}),
            ("get_hostel_details", {"student_id": student_id}),
            ("transfer_hostel", {"student_id": student_id, "target_room_id": refs["available_female_room"]}),
        ]
        for tool_name, arguments in actions:
            steps += 1
            obs = env.step(tool_name=tool_name, arguments=arguments)
        steps += 1
        obs = env.step(
            tool_name="submit_final_response",
            arguments={"message": "Hostel room allocated.", "resolution_summary": {"allocated_room": refs["available_female_room"]}},
        )
    elif task_id == "task_3_course_switch":
        student_id = refs["student_id"]
        course_a_id = refs["course_a_id"]
        course_b_id = refs["course_b_id"]
        actions = [
            ("get_student_record", {"student_id": student_id}),
            ("check_prerequisites", {"student_id": student_id, "course_id": course_b_id}),
            ("check_seat_availability", {"course_id": course_b_id}),
            ("check_credit_limits", {"student_id": student_id}),
            ("check_fee_clearance", {"student_id": student_id}),
            ("search_scholarships", {"student_id": student_id}),
            ("check_scholarship_compliance", {"student_id": student_id, "scholarship_id": refs["scholarship_id"]}),
            ("drop_course", {"student_id": student_id, "course_id": course_a_id}),
            ("enroll_student", {"student_id": student_id, "course_id": course_b_id}),
        ]
        for tool_name, arguments in actions:
            steps += 1
            obs = env.step(tool_name=tool_name, arguments=arguments)
        steps += 1
        obs = env.step(
            tool_name="submit_final_response",
            arguments={
                "message": "Course switch completed.",
                "resolution_summary": {"dropped": course_a_id, "enrolled": course_b_id},
            },
        )
    elif task_id == "task_4_concurrent_conflict":
        stu_x = refs["student_x_id"]
        stu_y = refs["student_y_id"]
        course_id = refs["course_id"]
        actions = [
            ("check_seat_availability", {"course_id": course_id}),
            ("get_student_record", {"student_id": stu_x}),
            ("get_student_record", {"student_id": stu_y}),
            ("search_scholarships", {"student_id": stu_x}),
            ("check_prerequisites", {"student_id": stu_x, "course_id": course_id}),
            ("check_fee_clearance", {"student_id": stu_x}),
            ("enroll_student", {"student_id": stu_x, "course_id": course_id}),
            ("search_courses", {"filters": {"department": "DEPT-ECE", "has_availability": True}}),
        ]
        for tool_name, arguments in actions:
            steps += 1
            obs = env.step(tool_name=tool_name, arguments=arguments)
        steps += 1
        obs = env.step(
            tool_name="submit_final_response",
            arguments={
                "message": "Scholarship-priority student enrolled; alternate options identified for the other student.",
                "resolution_summary": {"enrolled": stu_x, "denied": stu_y},
            },
        )
    elif task_id == "task_5_graduation_crisis":
        student_id = refs["student_id"]
        capstone_course_id = refs["capstone_course_id"]
        actions = [
            ("get_student_record", {"student_id": student_id}),
            ("get_fee_status", {"student_id": student_id}),
            ("check_credit_limits", {"student_id": student_id}),
            ("get_enrollment_history", {"student_id": student_id}),
            ("check_prerequisites", {"student_id": student_id, "course_id": capstone_course_id}),
            ("search_scholarships", {"student_id": student_id}),
            ("check_scholarship_compliance", {"student_id": student_id, "scholarship_id": refs["scholarship_id"]}),
            ("get_hostel_details", {"student_id": student_id}),
            ("update_fee_record", {"student_id": student_id, "payment_amount": 2500}),
            ("clear_probation_hold", {"student_id": student_id}),
            ("initiate_hostel_checkout", {"student_id": student_id}),
            ("enroll_student", {"student_id": student_id, "course_id": capstone_course_id, "exception_override": True}),
        ]
        for tool_name, arguments in actions:
            steps += 1
            obs = env.step(tool_name=tool_name, arguments=arguments)
        steps += 1
        obs = env.step(
            tool_name="submit_final_response",
            arguments={
                "message": "Graduation blockers resolved through real administrative actions.",
                "resolution_summary": {"fees_paid": True, "probation_cleared": True, "checkout_initiated": True, "capstone_enrolled": capstone_course_id},
            },
        )
    elif task_id == "task_6_bulk_schedule":
        conflict_pairs = refs["student_conflict_pairs"]
        for student_id, course_id, _ in conflict_pairs:
            steps += 1
            env.step(tool_name="get_exam_schedule", arguments={"student_id": student_id})
            steps += 1
            alt_obs = env.step(tool_name="find_exam_alternatives", arguments={"student_id": student_id, "course_id": course_id})
            alt_data = json.loads(alt_obs.tool_result)
            alternatives = alt_data.get("alternatives", [])
            if alternatives:
                choice = alternatives[0]
                steps += 1
                env.step(
                    tool_name="check_reschedule_impact",
                    arguments={
                        "course_id": course_id,
                        "new_date": choice["date"],
                        "new_time_slot": choice["time_slot"],
                        "new_room_id": choice["room_id"],
                    },
                )
                steps += 1
                env.step(
                    tool_name="reschedule_exam",
                    arguments={
                        "course_id": course_id,
                        "new_date": choice["date"],
                        "new_time_slot": choice["time_slot"],
                        "new_room_id": choice["room_id"],
                    },
                )
        steps += 1
        obs = env.step(tool_name="search_faculty", arguments={})
        steps += 1
        obs = env.step(
            tool_name="submit_final_response",
            arguments={"message": "All exam conflicts processed with schedule mutations.", "resolution_summary": {"resolved_students": 8}},
        )
    else:
        raise RuntimeError(f"Unsupported task id: {task_id}")
    grader = env.grader() or {}
    return {"task_id": task_id, "difficulty": TASK_CONFIGS[task_id]["difficulty"], "score": grader.get("score", 0.0), "steps": steps, "grader_result": grader}


def run_task_with_llm(env: UniAdminClient, model_client: OpenAI, task_id: str) -> Dict[str, Any]:
    obs = env.reset(task_id=task_id)
    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
        {"role": "user", "content": [{"type": "text", "text": obs.task_description}]},
    ]
    steps = 0
    max_steps = min(TASK_CONFIGS[task_id]["max_steps"], GLOBAL_MAX_STEPS)

    while not obs.done and steps < max_steps:
        steps += 1
        try:
            tool_name, arguments, raw_response = llm_next_action(model_client, messages)
        except Exception as exc:  # noqa: BLE001
            raw_response = str(exc)
            tool_name = "submit_final_response"
            arguments = {"message": "Model request failed.", "resolution_summary": {"error": str(exc)}}
        obs = env.step(tool_name=tool_name, arguments=arguments)
        messages.append({"role": "assistant", "content": [{"type": "text", "text": raw_response}]})
        messages.append({"role": "user", "content": [{"type": "text", "text": format_observation(obs)}]})

    grader = env.grader() or {}
    return {"task_id": task_id, "difficulty": TASK_CONFIGS[task_id]["difficulty"], "score": grader.get("score", 0.0), "steps": steps, "grader_result": grader}


def write_results(
    *,
    requested_agent: str,
    effective_agent: str,
    base_url: str,
    elapsed: float,
    results: List[Dict[str, Any]],
    warning: Optional[str] = None,
    error: Optional[str] = None,
) -> None:
    average_score = sum(result["score"] for result in results) / len(results) if results else 0.0
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload: Dict[str, Any] = {
        "requested_agent_mode": requested_agent,
        "agent_mode": effective_agent,
        "model": MODEL_NAME if effective_agent == "llm" else "mock",
        "api_base": API_BASE_URL if effective_agent == "llm" else "",
        "environment_base_url": base_url,
        "average_score": average_score,
        "total_time_seconds": elapsed,
        "results": results,
    }
    if warning:
        payload["warning"] = warning
    if error:
        payload["error"] = error

    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)


def main() -> None:
    args = parse_args()
    server_process: Optional[subprocess.Popen[bytes]] = None
    env: Optional[UniAdminClient] = None
    base_url = args.env_base_url
    requested_agent = args.agent
    effective_agent, warning = resolve_agent_mode(requested_agent)
    results: List[Dict[str, Any]] = []
    start = time.time()
    fatal_error: Optional[str] = None

    try:
        if warning:
            print(f"WARNING: {warning}", file=sys.stderr)

        if not base_url:
            base_url, server_process = boot_local_server()

        env = UniAdminClient(base_url=base_url, timeout=60.0)
        model_client = build_openai_client() if effective_agent == "llm" else None

        for task_id in TASK_CONFIGS:
            if effective_agent == "mock":
                result = run_task_with_mock(env, task_id)
            else:
                assert model_client is not None
                result = run_task_with_llm(env, model_client, task_id)
            results.append(result)
            print(f"{task_id}: score={result['score']:.3f} steps={result['steps']}")
    except Exception as exc:  # noqa: BLE001
        fatal_error = str(exc)
        print(f"ERROR: {fatal_error}", file=sys.stderr)
    finally:
        if env is not None:
            env.close()
        if server_process is not None:
            server_process.terminate()
            try:
                server_process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server_process.kill()
                server_process.wait(timeout=5)

        elapsed = time.time() - start
        write_results(
            requested_agent=requested_agent,
            effective_agent=effective_agent,
            base_url=base_url,
            elapsed=elapsed,
            results=results,
            warning=warning,
            error=fatal_error,
        )

    average_score = sum(result["score"] for result in results) / len(results) if results else 0.0
    print(f"Average score: {average_score:.3f}")
    print(f"Results written to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()

"""UniAdmin baseline inference runner."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

from uniadmin.client import UniAdminClient
from uniadmin.models import TASK_CONFIGS, UniAdminObservation, format_tools_for_prompt

ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = ROOT / "outputs" / "evals" / "inference_results.json"

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN = os.getenv("HF_TOKEN")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "")
TEMPERATURE = 0.0
MAX_TOKENS = 2048
GLOBAL_MAX_STEPS = 30
BENCHMARK = "uniadmin"

SYSTEM_PROMPT = """You are a university administrative desk officer. Process each request using the available tools.

Rules:
1. Verify before mutating.
2. Respect fees, prerequisites, schedules, deadlines, and policy constraints.
3. Use submit_final_response only when you are done.
4. Respond with exactly one JSON object on one line:
{"tool_name":"<tool_name>","arguments":{...}}

Available tools:
""" + format_tools_for_prompt()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent", choices=["llm", "mock"], default="llm")
    parser.add_argument("--env-base-url", default=ENV_BASE_URL)
    return parser.parse_args()


def resolve_agent_mode(requested_agent: str) -> Tuple[str, Optional[str]]:
    if requested_agent == "mock":
        return "mock", None
    if HF_TOKEN:
        return "llm", None
    return "mock", "HF_TOKEN is not set; falling back to mock mode for submission-safe inference."


def sanitize_log_value(value: Optional[str]) -> str:
    if not value:
        return "null"
    return str(value).replace("\r", " ").replace("\n", " ")


def format_action_str(tool_name: str, arguments: Dict[str, Any]) -> str:
    compact_args = json.dumps(arguments, separators=(",", ":"), ensure_ascii=True, default=str)
    return f"{tool_name}({compact_args})"


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    print(
        f"[STEP] step={step} action={sanitize_log_value(action)} reward={reward:.2f} "
        f"done={str(done).lower()} error={sanitize_log_value(error)}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{reward:.2f}" for reward in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
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
    if not HF_TOKEN:
        raise RuntimeError("Set HF_TOKEN before running LLM inference.")
    return OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)


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


def execute_step(
    env: UniAdminClient,
    tracker: Dict[str, Any],
    tool_name: str,
    arguments: Dict[str, Any],
) -> UniAdminObservation:
    tracker["steps"] += 1
    action_str = format_action_str(tool_name, arguments)
    obs = env.step(tool_name=tool_name, arguments=arguments)
    reward = float(obs.reward or 0.0)
    tracker["rewards"].append(reward)
    tracker["last_error"] = obs.error_message
    log_step(tracker["steps"], action_str, reward, obs.done, obs.error_message)
    return obs


def build_task_result(task_id: str, tracker: Dict[str, Any], grader: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    grader = grader or {}
    return {
        "task_id": task_id,
        "difficulty": TASK_CONFIGS[task_id]["difficulty"],
        "score": float(grader.get("score", 0.0)),
        "steps": tracker["steps"],
        "rewards": list(tracker["rewards"]),
        "last_error": tracker["last_error"],
        "success": bool(tracker["success"]),
        "grader_result": grader,
    }


def run_task_with_mock(env: UniAdminClient, task_id: str, tracker: Dict[str, Any]) -> Dict[str, Any]:
    try:
        obs = env.reset(task_id=task_id)
        refs = dict(obs.metadata.get("task_refs", {}))

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
                obs = execute_step(env, tracker, tool_name, arguments)
                if tool_name == "search_courses":
                    search_results = json.loads(obs.tool_result) if obs.tool_result else {}
            execute_step(
                env,
                tracker,
                "submit_final_response",
                {
                    "message": "Available CS electives identified.",
                    "resolution_summary": {
                        "available_courses": [course["course_id"] for course in search_results.get("results", [])],
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
                execute_step(env, tracker, tool_name, arguments)
            execute_step(
                env,
                tracker,
                "submit_final_response",
                {"message": "Hostel room allocated.", "resolution_summary": {"allocated_room": refs["available_female_room"]}},
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
                execute_step(env, tracker, tool_name, arguments)
            execute_step(
                env,
                tracker,
                "submit_final_response",
                {
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
                execute_step(env, tracker, tool_name, arguments)
            execute_step(
                env,
                tracker,
                "submit_final_response",
                {
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
                execute_step(env, tracker, tool_name, arguments)
            execute_step(
                env,
                tracker,
                "submit_final_response",
                {
                    "message": "Graduation blockers resolved through real administrative actions.",
                    "resolution_summary": {
                        "fees_paid": True,
                        "probation_cleared": True,
                        "checkout_initiated": True,
                        "capstone_enrolled": capstone_course_id,
                    },
                },
            )
        elif task_id == "task_6_bulk_schedule":
            conflict_pairs = refs["student_conflict_pairs"]
            for student_id, course_id, _ in conflict_pairs:
                execute_step(env, tracker, "get_exam_schedule", {"student_id": student_id})
                alt_obs = execute_step(env, tracker, "find_exam_alternatives", {"student_id": student_id, "course_id": course_id})
                alt_data = json.loads(alt_obs.tool_result)
                alternatives = alt_data.get("alternatives", [])
                if alternatives:
                    choice = alternatives[0]
                    execute_step(
                        env,
                        tracker,
                        "check_reschedule_impact",
                        {
                            "course_id": course_id,
                            "new_date": choice["date"],
                            "new_time_slot": choice["time_slot"],
                            "new_room_id": choice["room_id"],
                        },
                    )
                    execute_step(
                        env,
                        tracker,
                        "reschedule_exam",
                        {
                            "course_id": course_id,
                            "new_date": choice["date"],
                            "new_time_slot": choice["time_slot"],
                            "new_room_id": choice["room_id"],
                        },
                    )
            execute_step(env, tracker, "search_faculty", {})
            execute_step(
                env,
                tracker,
                "submit_final_response",
                {"message": "All exam conflicts processed with schedule mutations.", "resolution_summary": {"resolved_students": 8}},
            )
        else:
            raise RuntimeError(f"Unsupported task id: {task_id}")
    except Exception as exc:  # noqa: BLE001
        tracker["success"] = False
        tracker["last_error"] = str(exc)

    grader = env.grader() or {}
    return build_task_result(task_id, tracker, grader)


def run_task_with_llm(env: UniAdminClient, model_client: OpenAI, task_id: str, tracker: Dict[str, Any]) -> Dict[str, Any]:
    try:
        obs = env.reset(task_id=task_id)
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": [{"type": "text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": [{"type": "text", "text": obs.task_description}]},
        ]
        max_steps = min(TASK_CONFIGS[task_id]["max_steps"], GLOBAL_MAX_STEPS)

        while not obs.done and tracker["steps"] < max_steps:
            try:
                tool_name, arguments, raw_response = llm_next_action(model_client, messages)
            except Exception as exc:  # noqa: BLE001
                raw_response = str(exc)
                tool_name = "submit_final_response"
                arguments = {"message": "Model request failed.", "resolution_summary": {"error": str(exc)}}
            obs = execute_step(env, tracker, tool_name, arguments)
            messages.append({"role": "assistant", "content": [{"type": "text", "text": raw_response}]})
            messages.append({"role": "user", "content": [{"type": "text", "text": format_observation(obs)}]})
    except Exception as exc:  # noqa: BLE001
        tracker["success"] = False
        tracker["last_error"] = str(exc)

    grader = env.grader() or {}
    return build_task_result(task_id, tracker, grader)


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
    base_url = args.env_base_url
    requested_agent = args.agent
    effective_agent, warning = resolve_agent_mode(requested_agent)
    results: List[Dict[str, Any]] = []
    start = time.time()
    fatal_error: Optional[str] = None

    try:
        if warning:
            print(sanitize_log_value(f"WARNING: {warning}"), file=sys.stderr, flush=True)

        if not base_url:
            base_url, server_process = boot_local_server()

        model_client = build_openai_client() if effective_agent == "llm" else None

        for task_id in TASK_CONFIGS:
            env = UniAdminClient(base_url=base_url, timeout=60.0)
            tracker = {"steps": 0, "rewards": [], "last_error": None, "success": True}
            result = build_task_result(task_id, tracker, None)
            model_name = MODEL_NAME if effective_agent == "llm" else "mock"
            log_start(task_id, BENCHMARK, model_name)
            try:
                if effective_agent == "mock":
                    result = run_task_with_mock(env, task_id, tracker)
                else:
                    assert model_client is not None
                    result = run_task_with_llm(env, model_client, task_id, tracker)
            finally:
                env.close()
                log_end(result["success"], result["steps"], result["score"], result["rewards"])
            results.append(result)
    except Exception as exc:  # noqa: BLE001
        fatal_error = str(exc)
        print(sanitize_log_value(f"ERROR: {fatal_error}"), file=sys.stderr, flush=True)
    finally:
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


if __name__ == "__main__":
    main()

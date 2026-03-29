from __future__ import annotations

from typing import Any, Dict, List, Optional

import httpx

from uniadmin.models import UniAdminObservation, UniAdminState, TaskInfo


class UniAdminClient:
    def __init__(self, base_url: str = "http://localhost:7860", timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    def health(self) -> Dict[str, Any]:
        resp = self._client.get(f"{self.base_url}/health")
        resp.raise_for_status()
        return resp.json()

    def tasks(self) -> List[Dict[str, Any]]:
        resp = self._client.get(f"{self.base_url}/tasks")
        resp.raise_for_status()
        return resp.json()

    def reset(self, task_id: Optional[str] = None) -> UniAdminObservation:
        payload = {"task_id": task_id} if task_id else {}
        resp = self._client.post(f"{self.base_url}/reset", json=payload)
        resp.raise_for_status()
        data = resp.json()
        obs_data = data.get("observation", data)
        return UniAdminObservation(**obs_data)

    def step(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        message_to_student: Optional[str] = None,
    ) -> UniAdminObservation:
        payload = {
            "tool_name": tool_name,
            "arguments": arguments or {},
        }
        if message_to_student:
            payload["message_to_student"] = message_to_student

        resp = self._client.post(f"{self.base_url}/step", json=payload)
        resp.raise_for_status()
        data = resp.json()
        obs_data = data.get("observation", data)
        return UniAdminObservation(**obs_data)

    def state(self) -> UniAdminState:
        resp = self._client.get(f"{self.base_url}/state")
        resp.raise_for_status()
        data = resp.json()
        state_data = data.get("state", data)
        return UniAdminState(**state_data)

    def grader(self) -> Optional[Dict[str, Any]]:
        resp = self._client.get(f"{self.base_url}/grader")
        resp.raise_for_status()
        data = resp.json()
        return data.get("grader_result")

    def close(self) -> None:
        try:
            self._client.post(f"{self.base_url}/close")
        except Exception:
            pass

    def __del__(self):
        try:
            self._client.close()
        except Exception:
            pass

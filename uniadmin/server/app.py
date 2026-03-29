from __future__ import annotations

import os
import traceback
from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from uniadmin.models import (
    UniAdminAction,
    UniAdminObservation,
    UniAdminState,
    TaskInfo,
    get_task_list,
)
from uniadmin.server.uniadmin_environment import UniAdminEnvironment


app = FastAPI(
    title="UniAdmin Environment",
    description="University Administrative Operations Environment for Agentic RL",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global environment instance
env = UniAdminEnvironment()



class ResetRequest(BaseModel):
    task_id: Optional[str] = None


class StepRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}
    message_to_student: Optional[str] = None


class ResetResponse(BaseModel):
    observation: Dict[str, Any]


class StepResponse(BaseModel):
    observation: Dict[str, Any]
    reward: Optional[float] = None
    done: bool = False


class StateResponse(BaseModel):
    state: Dict[str, Any]


class GraderResponse(BaseModel):
    grader_result: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    status: str = "ok"
    environment: str = "uniadmin"
    version: str = "1.0.0"



@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse()


@app.get("/tasks")
async def list_tasks():
    tasks = get_task_list()
    return [t.model_dump() for t in tasks]


@app.post("/reset")
async def reset(request: Optional[ResetRequest] = None):
    try:
        task_id = request.task_id if request is not None else None
        obs = env.reset(task_id=task_id)
        obs_dict = obs.model_dump()
        return {"observation": obs_dict}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/step")
async def step(request: StepRequest):
    try:
        action = UniAdminAction(
            tool_name=request.tool_name,
            arguments=request.arguments,
            message_to_student=request.message_to_student,
        )
        obs = env.step(action)
        obs_dict = obs.model_dump()
        return {
            "observation": obs_dict,
            "reward": obs.reward,
            "done": obs.done,
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state")
async def get_state():
    try:
        state = env.state()
        return {"state": state.model_dump()}
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/grader")
async def get_grader():
    result = env.get_grader_result()
    return {"grader_result": result}


@app.post("/close")
async def close_env():
    env.close()
    return {"status": "closed"}



if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 7860))
    uvicorn.run(app, host="0.0.0.0", port=port)

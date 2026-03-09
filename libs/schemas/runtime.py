from typing import Literal

from pydantic import BaseModel, Field


class ExecutionPlanStep(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    kind: Literal["retrieve_context", "analyze", "reason", "respond", "other"] = "other"
    description: str = Field(min_length=1, max_length=500)


class ExecutionPlan(BaseModel):
    version: str = "v1"
    goal: str = Field(min_length=1, max_length=500)
    steps: list[ExecutionPlanStep] = Field(min_length=1, max_length=12)

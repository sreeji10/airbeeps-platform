from pydantic import BaseModel


class UsageSummaryResponse(BaseModel):
    workspace_id: str
    project_id: str | None
    request_count: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float

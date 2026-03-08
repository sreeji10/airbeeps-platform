from dataclasses import dataclass

from libs.schemas.chat import ChatRunRequest, ChatRunResponse
from libs.tools.registry import ToolRegistry
from libs.utils.ids import make_id
from services.rag.service import RagService


class RuntimeService:
    def run(self, request: ChatRunRequest) -> ChatRunResponse:
        raise NotImplementedError


@dataclass
class RuntimeServiceImpl(RuntimeService):
    rag: RagService
    tools: ToolRegistry

    def run(self, request: ChatRunRequest) -> ChatRunResponse:
        retrieval_results = self.rag.retrieve(
            query=request.message,
            dataset_ids=request.dataset_ids,
            top_k=3,
        )
        step_log = [
            "planner: built baseline execution plan",
            "rag: fetched supporting context",
        ]

        used_tools: list[str] = []
        for tool_name in request.tool_names:
            if self.tools.has(tool_name):
                self.tools.execute(tool_name, request.message)
                used_tools.append(tool_name)
                step_log.append(f"tool: executed '{tool_name}'")

        step_log.append("runtime: synthesized final response")

        response = (
            "Baseline runtime completed. "
            f"Retrieved {len(retrieval_results)} context chunks and used {len(used_tools)} tools."
        )
        return ChatRunResponse(
            run_id=make_id("run"),
            response=response,
            steps=step_log,
            retrieval=retrieval_results,
            used_tools=used_tools,
        )

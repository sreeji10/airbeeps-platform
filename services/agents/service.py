from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import AgentConfig
from libs.schemas.agent import AgentCreateRequest
from libs.schemas.auth import AuthenticatedUser
from services.platform.service import PlatformService


@dataclass
class AgentService:
    session: AsyncSession

    async def create_agent(
        self,
        *,
        request: AgentCreateRequest,
        user: AuthenticatedUser,
    ) -> AgentConfig:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=request.workspace_id, user_id=user.user_id
        )
        agent = AgentConfig(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            name=request.name,
            description=request.description,
            planner_model=request.planner_model,
            generation_model=request.generation_model,
            fallback_model=request.fallback_model,
            prompt_template_id=request.prompt_template_id,
            enabled_tools=request.enabled_tools,
            dataset_ids=request.dataset_ids,
            execution_limits=request.execution_limits,
            created_by=user.user_id,
        )
        self.session.add(agent)
        await self.session.commit()
        await self.session.refresh(agent)
        return agent

    async def list_agents(
        self,
        *,
        workspace_id: str,
        project_id: str,
        user: AuthenticatedUser,
    ) -> list[AgentConfig]:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(AgentConfig)
            .where(
                AgentConfig.workspace_id == workspace_id,
                AgentConfig.project_id == project_id,
                AgentConfig.status == "active",
            )
            .order_by(AgentConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_agent(
        self,
        *,
        agent_id: str,
        workspace_id: str,
        user: AuthenticatedUser,
    ) -> AgentConfig | None:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(AgentConfig).where(
                AgentConfig.id == agent_id,
                AgentConfig.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

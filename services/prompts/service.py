from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import PromptTemplate
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.prompt import PromptTemplateCreateRequest
from services.platform.service import PlatformService


@dataclass
class PromptService:
    session: AsyncSession

    async def create_template(
        self,
        *,
        request: PromptTemplateCreateRequest,
        user: AuthenticatedUser,
    ) -> PromptTemplate:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=request.workspace_id, user_id=user.user_id
        )
        template = PromptTemplate(
            workspace_id=request.workspace_id,
            project_id=request.project_id,
            name=request.name,
            version=request.version,
            template=request.template,
            variables=request.variables,
            created_by=user.user_id,
        )
        self.session.add(template)
        await self.session.commit()
        await self.session.refresh(template)
        return template

    async def list_templates(
        self,
        *,
        workspace_id: str,
        project_id: str,
        user: AuthenticatedUser,
    ) -> list[PromptTemplate]:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(PromptTemplate)
            .where(
                PromptTemplate.workspace_id == workspace_id,
                PromptTemplate.project_id == project_id,
            )
            .order_by(PromptTemplate.name.asc(), PromptTemplate.version.desc())
        )
        return list(result.scalars().all())

    async def get_template(
        self,
        *,
        template_id: str,
        workspace_id: str,
        user: AuthenticatedUser,
    ) -> PromptTemplate | None:
        platform = PlatformService(self.session)
        await platform.ensure_workspace_access(
            workspace_id=workspace_id, user_id=user.user_id
        )
        result = await self.session.execute(
            select(PromptTemplate).where(
                PromptTemplate.id == template_id,
                PromptTemplate.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    def render(
        self,
        *,
        template: PromptTemplate,
        variables: dict[str, object] | None = None,
    ) -> str:
        payload = {key: str(value) for key, value in (variables or {}).items()}
        try:
            return template.template.format(**payload)
        except KeyError:
            # Keep template raw when optional placeholders are missing.
            return template.template

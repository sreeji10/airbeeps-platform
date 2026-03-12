from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.db.models import Dataset, DatasetFile, Project, Workspace, WorkspaceMember
from libs.schemas.auth import WorkspaceMembership


@dataclass
class DatasetFileCreate:
    workspace_id: str
    project_id: str
    dataset_name: str
    filename: str
    content_type: str | None
    size_bytes: int
    storage_bucket: str
    storage_path: str
    user_id: str


class PlatformService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_workspace(self, *, name: str, user_id: str) -> Workspace:
        workspace = Workspace(name=name, created_by=user_id)
        self.session.add(workspace)
        await self.session.flush()

        membership = WorkspaceMember(
            workspace_id=workspace.id, user_id=user_id, role="owner"
        )
        self.session.add(membership)
        await self.session.commit()
        await self.session.refresh(workspace)
        return workspace

    async def list_user_workspaces(self, *, user_id: str) -> list[WorkspaceMembership]:
        result = await self.session.execute(
            select(WorkspaceMember)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(WorkspaceMember.created_at)
        )
        members = result.scalars().all()
        return [
            WorkspaceMembership(workspace_id=item.workspace_id, role=item.role)
            for item in members
        ]

    async def list_workspaces(self, *, user_id: str) -> list[Workspace]:
        result = await self.session.execute(
            select(Workspace)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.asc())
        )
        return list(result.scalars().all())

    async def ensure_workspace_access(
        self, *, workspace_id: str, user_id: str
    ) -> WorkspaceMember:
        result = await self.session.execute(
            select(WorkspaceMember).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        membership = result.scalar_one_or_none()
        if membership is None:
            raise PermissionError("User is not a member of this workspace")
        return membership

    async def create_project(
        self,
        *,
        workspace_id: str,
        name: str,
        description: str | None,
        user_id: str,
    ) -> Project:
        await self.ensure_workspace_access(workspace_id=workspace_id, user_id=user_id)

        project = Project(
            workspace_id=workspace_id,
            name=name,
            description=description,
            created_by=user_id,
        )
        self.session.add(project)
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def list_projects(self, *, workspace_id: str, user_id: str) -> list[Project]:
        await self.ensure_workspace_access(workspace_id=workspace_id, user_id=user_id)
        result = await self.session.execute(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_dataset_with_file(
        self, payload: DatasetFileCreate
    ) -> tuple[Dataset, DatasetFile]:
        await self.ensure_workspace_access(
            workspace_id=payload.workspace_id, user_id=payload.user_id
        )

        result = await self.session.execute(
            select(Project).where(
                Project.id == payload.project_id,
                Project.workspace_id == payload.workspace_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise ValueError("Project not found in workspace")

        dataset = Dataset(
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            name=payload.dataset_name,
            created_by=payload.user_id,
            status="pending_ingestion",
        )
        self.session.add(dataset)
        await self.session.flush()

        file_record = DatasetFile(
            id=str(uuid4()),
            workspace_id=payload.workspace_id,
            project_id=payload.project_id,
            dataset_id=dataset.id,
            storage_bucket=payload.storage_bucket,
            storage_path=payload.storage_path,
            filename=payload.filename,
            content_type=payload.content_type,
            size_bytes=payload.size_bytes,
            uploaded_by=payload.user_id,
        )
        self.session.add(file_record)
        await self.session.commit()
        await self.session.refresh(dataset)
        await self.session.refresh(file_record)
        return dataset, file_record

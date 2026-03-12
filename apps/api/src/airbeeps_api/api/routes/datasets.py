from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from libs.schemas.auth import AuthenticatedUser
from libs.schemas.dataset import DatasetRead, DatasetUploadResponse
from services.platform.service import DatasetFileCreate, PlatformService
from services.storage.supabase_storage import StorageError
from sqlalchemy.ext.asyncio import AsyncSession

from airbeeps_api.api.auth import get_current_user
from airbeeps_api.db.session import get_db_session
from airbeeps_api.dependencies import ServiceContainer, get_container

router = APIRouter(prefix="/datasets", tags=["datasets"])


@router.get("", response_model=list[DatasetRead])
async def list_datasets(
    workspace_id: str,
    project_id: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "desc",
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> list[DatasetRead]:
    service = PlatformService(session)
    bounded_limit = min(max(limit, 1), 200)
    bounded_offset = max(offset, 0)
    rows = await service.list_datasets(
        workspace_id=workspace_id,
        project_id=project_id,
        user_id=user.user_id,
        status=status,
        limit=bounded_limit,
        offset=bounded_offset,
        sort_desc=sort != "asc",
    )
    return [
        DatasetRead(
            id=row.id,
            workspace_id=row.workspace_id,
            project_id=row.project_id,
            name=row.name,
            status=row.status,
            created_by=row.created_by,
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]


@router.post("/upload", response_model=DatasetUploadResponse)
async def upload_dataset_file(
    workspace_id: str = Form(...),
    project_id: str = Form(...),
    dataset_name: str = Form(...),
    file: UploadFile = File(...),
    user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
    container: ServiceContainer = Depends(get_container),
) -> DatasetUploadResponse:
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="File is empty")
    filename = file.filename or "upload.bin"

    try:
        stored = await container.storage.upload_bytes(
            workspace_id=workspace_id,
            project_id=project_id,
            filename=filename,
            content=content,
            content_type=file.content_type,
        )
    except StorageError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    service = PlatformService(session)
    try:
        dataset, file_record = await service.create_dataset_with_file(
            DatasetFileCreate(
                workspace_id=workspace_id,
                project_id=project_id,
                dataset_name=dataset_name,
                filename=filename,
                content_type=file.content_type,
                size_bytes=len(content),
                storage_bucket=stored.bucket,
                storage_path=stored.path,
                user_id=user.user_id,
            )
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return DatasetUploadResponse(
        dataset_id=dataset.id,
        file_id=file_record.id,
        storage_bucket=file_record.storage_bucket,
        storage_path=file_record.storage_path,
        uploaded_at=file_record.created_at.isoformat(),
    )

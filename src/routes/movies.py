from typing import Annotated
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.movies import (
    CertificationRequestSchema,
    CertificationResponseSchema
)
from services.movies import (
    create_certification_service,
    get_certifications,
    get_certification_by_id,
    update_certification_service,
    delete_certification_service
)
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)
from database import get_db
from security.dependencies import require_roles
from schemas.accounts import MessageResponseSchema

router = APIRouter()


@router.post(
    "/certifications",
    status_code=status.HTTP_201_CREATED,
    response_model=CertificationResponseSchema
)
async def create_certification(
    db: Annotated[AsyncSession, Depends(get_db)],
    certification_data: CertificationRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> CertificationResponseSchema:
    return await create_certification_service(
        db=db,
        certification_data=certification_data,
        current_user=current_user
    )


@router.get(
    "/certifications",
    status_code=status.HTTP_200_OK,
    response_model=list[CertificationResponseSchema]
)
async def list_certifications(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> list[CertificationResponseSchema]:
    return await get_certifications(
        db=db
    )


@router.get(
    "/certifications/{certification_id}",
    status_code=status.HTTP_200_OK,
    response_model=CertificationResponseSchema
)
async def get_certification(
    db: Annotated[AsyncSession, Depends(get_db)],
    certification_id: int
) -> CertificationResponseSchema:
    return await get_certification_by_id(
        db=db,
        certification_id=certification_id
    )


@router.patch(
    "/certifications/{certification_id}",
    status_code=status.HTTP_200_OK,
    response_model=CertificationResponseSchema
)
async def update_certification(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    certification_id: int,
    data: CertificationRequestSchema
) -> CertificationResponseSchema:
    return await update_certification_service(
        db=db,
        current_user=current_user,
        certification_id=certification_id,
        data=data
    )


@router.delete(
    "/certifications/{certification_id}",
    status_code=status.HTTP_200_OK,
    response_model=MessageResponseSchema
)
async def delete_certification(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    certification_id: int,
) -> MessageResponseSchema:
    return await delete_certification_service(
        db=db,
        current_user=current_user,
        certification_id=certification_id,
    )

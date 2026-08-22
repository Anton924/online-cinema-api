from typing import Annotated, Any

from fastapi import Depends, status, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.movies import (
    CertificationRequestSchema,
    CertificationResponseSchema
)
from database.models.movies import CertificationModel
from database import get_db
from security.dependencies import require_roles
from database.models.accounts import (
    UserModel,
    UserGroupEnum
)

from schemas.accounts import MessageResponseSchema


def update_instance(instance: Any, data: BaseModel) -> None:
    data = data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(instance, key, value)


async def create_certification_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    certification_data: CertificationRequestSchema,
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> CertificationResponseSchema:
    stmt = select(CertificationModel).where(
        CertificationModel.name == certification_data.name
    )

    result = await db.execute(stmt)
    certification = result.scalars().first()

    if certification:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A certification with this name {certification.name!r} already exists."
        )

    try:
        certification = CertificationModel(
            name=certification_data.name
        )

        db.add(certification)
        await db.commit()
        await db.refresh(certification)

        return CertificationResponseSchema.model_validate(certification)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the certification."
        ) from e


async def get_certifications(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[CertificationResponseSchema]:
    stmt = select(CertificationModel)
    result = await db.execute(stmt)
    certifications = result.scalars().all()

    if not certifications:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No certifications found."
        )

    certification_list = [
        CertificationResponseSchema.model_validate(certification)
        for certification in certifications
    ]

    return certification_list


async def get_certification_by_id(
    db: Annotated[AsyncSession, Depends(get_db)],
    certification_id: int
) -> CertificationResponseSchema:
    stmt = select(CertificationModel).where(
        CertificationModel.id == certification_id
    )

    result = await db.execute(stmt)
    certification = result.scalars().first()

    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with id {certification_id} not found."
        )

    return CertificationResponseSchema.model_validate(certification)


async def update_certification_service(
        db: Annotated[AsyncSession, Depends(get_db)],
        certification_id: int,
        data: CertificationRequestSchema,
        current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))]
) -> CertificationResponseSchema:
    stmt = select(CertificationModel).where(
        CertificationModel.id == certification_id
    )
    result = await db.execute(stmt)
    certification = result.scalars().first()

    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with id {certification_id} not found."
        )

    stmt = select(CertificationModel).where(
        CertificationModel.name == data.name,
        CertificationModel.id != certification_id
    )
    result = await db.execute(stmt)
    is_the_same_name = result.scalars().first()

    if is_the_same_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A certification with this name {data.name!r} already exists."
        )

    try:
        update_instance(certification, data=data)
        db.add(certification)
        await db.commit()
        await db.refresh(certification)

        return CertificationResponseSchema.model_validate(certification)
    except SQLAlchemyError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the certification."
        ) from e


async def delete_certification_service(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[UserModel, Depends(require_roles(UserGroupEnum.ADMIN, UserGroupEnum.MODERATOR))],
    certification_id: int,
) -> MessageResponseSchema:
    stmt = select(CertificationModel).where(
        CertificationModel.id == certification_id
    )
    result = await db.execute(stmt)
    certification = result.scalars().first()

    if not certification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Certification with id {certification_id} not found."
        )

    try:
        await db.delete(certification)
        await db.commit()
        return MessageResponseSchema(
            message=f"Certification {certification.name!r} was successfully deleted."
        )
    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete certification {certification.name!r} - it is still assigned to one or more movies."
        ) from e
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the certification."
        ) from e

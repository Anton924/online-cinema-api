from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database.models.accounts import UserModel
from database import get_db

from config.dependencies import get_jwt_auth_manager
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface
from exceptions import BaseSecurityError


async def get_current_user(
        db: Annotated[AsyncSession, Depends(get_db)],
        token: Annotated[str, Depends(get_token)],
        jwt_manager: Annotated[JWTAuthManagerInterface, Depends(get_jwt_auth_manager)]
) -> UserModel:
    try:
        payload = jwt_manager.decode_access_token(token)
    except BaseSecurityError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error)
        )

    result = await db.execute(select(UserModel).options(
        joinedload(UserModel.group),
        joinedload(UserModel.profile)
    ).where(
        UserModel.id == payload.get("user_id")
    ))

    user = result.scalars().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user

from typing import Annotated, Any, Callable, Coroutine

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from database import get_db
from database.models.accounts import UserModel, UserGroupEnum

from config.dependencies import get_jwt_auth_manager
from security.http import get_token
from security.interfaces import JWTAuthManagerInterface
from exceptions import BaseSecurityError

from database.models.movies import MovieModel


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
        ) from error

    result = await db.execute(select(UserModel).options(
        joinedload(UserModel.group),
        joinedload(UserModel.profile),
        joinedload(UserModel.favorite_movies).joinedload(MovieModel.certification)
    ).where(
        UserModel.id == payload.get("user_id")
    ))

    user = result.scalars().unique().first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return user


def require_roles(*allowed_roles: UserGroupEnum) -> Callable[..., Coroutine[Any, Any, UserModel]]:
    async def role_checker(
            current_user: Annotated[UserModel, Depends(get_current_user)]
    ) -> UserModel:
        if current_user.group.name not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action."
            )
        return current_user
    return role_checker

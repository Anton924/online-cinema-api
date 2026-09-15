from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

bearer_schema = HTTPBearer(auto_error=False)


def get_token(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_schema)
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header is missing"
        )
    return credentials.credentials

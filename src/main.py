from fastapi import FastAPI, status
from routes import accounts_router, movies_router, carts_router

app = FastAPI(
    title="Online Cinema API",
    description="FastAPI backend for browsing, purchasing and managing movies."
)

prefix = "/api/v1"

app.include_router(router=accounts_router, prefix=f"{prefix}/accounts", tags=["accounts"])
app.include_router(router=movies_router, prefix=f"{prefix}/movies", tags=["cinema"])
app.include_router(router=carts_router, prefix=f"{prefix}/carts", tags=["cart"])


@app.get("/health/", status_code=status.HTTP_200_OK)
def health() -> dict:
    return {
        "detail": "Connection configured!"
    }

from fastapi import FastAPI, status
from routes import (
    accounts_router,
    movies_router,
    carts_router,
    orders_router,
    payments_router,
    profiles_router
)

app = FastAPI(
    title="Online Cinema API",
    version="0.1.0",
    description="FastAPI backend for browsing, purchasing and managing movies.",
    openapi_tags=[
        {
            "name": "accounts",
            "description": "Registration, activation, login/logout, password change and reset.",
        },
        {
            "name": "profiles",
            "description": "User profile and avatar (MinIO/S3).",
        },
        {
            "name": "Movies",
            "description": "Movie catalog — browsing, search, filtering, CRUD.",
        },
        {
            "name": "Genres",
            "description": "Movie genres.",
        },
        {
            "name": "Stars",
            "description": "Actors.",
        },
        {
            "name": "Directors",
            "description": "Directors.",
        },
        {
            "name": "Certifications",
            "description": "Age certifications (PG-13, R, etc.).",
        },
        {
            "name": "Favorites",
            "description": "User's favorite movies.",
        },
        {
            "name": "Reactions",
            "description": "Likes/dislikes for movies.",
        },
        {
            "name": "Ratings",
            "description": "Movie ratings (1-10).",
        },
        {
            "name": "Comments",
            "description": "Movie comments, with nested replies.",
        },
        {
            "name": "cart",
            "description": "Shopping cart.",
        },
        {
            "name": "orders",
            "description": "Orders.",
        },
        {
            "name": "payments",
            "description": "Stripe checkout, payment history, refunds.",
        },
    ],
)

prefix = "/api/v1"

app.include_router(router=accounts_router, prefix=f"{prefix}/accounts", tags=["accounts"])
app.include_router(router=profiles_router, prefix=f"{prefix}/profiles", tags=["profiles"])
app.include_router(router=movies_router, prefix=f"{prefix}/movies")
app.include_router(router=carts_router, prefix=f"{prefix}/carts", tags=["cart"])
app.include_router(router=orders_router, prefix=f"{prefix}/orders", tags=["orders"])
app.include_router(router=payments_router, prefix=f"{prefix}/payments", tags=["payments"])


@app.get("/health/", status_code=status.HTTP_200_OK, tags=["health"])
def health() -> dict:
    """Basic liveness check confirming the API is up and configured."""
    return {
        "detail": "Connection configured!"
    }

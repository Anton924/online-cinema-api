from fastapi import FastAPI, status

app = FastAPI(
    title="Online Cinema API",
    description="FastAPI backend for browsing, purchasing and managing movies."
)


@app.get("/health/", status_code=status.HTTP_200_OK)
def health() -> dict:
    return {
        "detail": "Connection configured!"
    }

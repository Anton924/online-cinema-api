from pydantic import BaseModel, Field


class CertificationRequestSchema(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class CertificationResponseSchema(BaseModel):
    id: int
    name: str

    model_config = {
        "from_attributes": True
    }

from pydantic import BaseModel


class Chunk(BaseModel):
    id: str
    entity_id: str
    text: str
    token_count: int
    hash: str

    class Config:
        from_attributes = True

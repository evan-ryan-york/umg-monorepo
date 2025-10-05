from pydantic import BaseModel
from typing import List


class Embedding(BaseModel):
    chunk_id: str
    vec: List[float]
    model: str

    class Config:
        from_attributes = True

from pydantic import BaseModel
from typing import List
from models.entity import Entity
from models.edge import Edge


class EntityRelationshipItem(BaseModel):
    """A single relationship item containing an edge and the related entity"""
    edge: Edge
    entity: Entity

    class Config:
        from_attributes = True


class EntityRelationships(BaseModel):
    """Complete relationship data for an entity, including outgoing and incoming edges"""
    outgoing: List[EntityRelationshipItem]
    incoming: List[EntityRelationshipItem]

    class Config:
        from_attributes = True

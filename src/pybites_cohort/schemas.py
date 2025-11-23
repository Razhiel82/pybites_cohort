from typing import List

from pydantic import BaseModel, ConfigDict


class TagRead(BaseModel):
    id: int
    name: str

    class Config:
        model_config = ConfigDict(from_attributes=True)


class SnippetRead(BaseModel):
    id: int
    title: str
    code: str
    description: str
    favorite: bool
    language: str
    tags: List[TagRead] = []

    class Config:
        model_config = ConfigDict(from_attributes=True)


class SnippetCreate(BaseModel):
    title: str
    code: str
    description: str
    favorite: bool
    language: str
    tags: List[str] = []

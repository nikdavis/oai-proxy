from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel


class ContentType(str, Enum):
    WEBPAGE = "webpage"
    PDF = "pdf"
    VIDEO = "video"


class ResourceSubmission(BaseModel):
    url: str
    type: ContentType | None = None
    title: str | None = None


class Resource(BaseModel):
    id: int
    url: str
    title: str
    type: ContentType
    content: str
    token_count: int | None = None
    created_at: str
    updated_at: str


class ResourcesResponse(BaseModel):
    items: list[Resource]
    total: int


class ValidationError(BaseModel):
    loc: list[str | int]
    msg: str
    type: str


class HTTPValidationError(BaseModel):
    detail: list[ValidationError]

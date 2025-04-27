from typing import List, Optional
from enum import Enum
from pydantic import BaseModel
from datetime import datetime


class ContentType(str, Enum):
    WEBPAGE = "webpage"
    PDF = "pdf"
    VIDEO = "video"


class ResourceSubmission(BaseModel):
    url: str
    type: Optional[ContentType] = None
    title: Optional[str] = None


class Resource(BaseModel):
    id: int
    url: str
    title: str
    type: ContentType
    content: str
    token_count: Optional[int] = None
    created_at: str
    updated_at: str


class ResourcesResponse(BaseModel):
    items: List[Resource]
    total: int


class ValidationError(BaseModel):
    loc: List[str | int]
    msg: str
    type: str


class HTTPValidationError(BaseModel):
    detail: List[ValidationError]

from typing import List

from pydantic import BaseModel


class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

from pydantic import BaseModel
from typing import List

class Message(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str

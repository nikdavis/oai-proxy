from pydantic import BaseModel
from typing import List

class LLMResponse(BaseModel):
    choices: List[str]

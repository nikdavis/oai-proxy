from typing import List

from pydantic import BaseModel


class LLMResponse(BaseModel):
    choices: List[str]

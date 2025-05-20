from typing import Protocol


class ContextClientP(Protocol):
    async def get_context(self, key: str) -> list[str]:
        return []  # Default empty implementation

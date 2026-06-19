from abc import ABC, abstractmethod
from datetime import date

from ..models import User, Paper


class BaseNotifier(ABC):
    @abstractmethod
    async def send_digest(self, user: User, papers: list[Paper], digest_date: date) -> bool:
        """Send digest notification. Returns True on success."""

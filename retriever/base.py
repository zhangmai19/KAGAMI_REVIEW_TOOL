"""Abstract base class for paper retrievers."""

from abc import ABC, abstractmethod
from typing import List, Optional

from models.paper import Paper


class BaseRetriever(ABC):
    """Base class for all paper retrievers.

    Subclasses must implement the `search` method.
    """

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 100,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
    ) -> List[Paper]:
        """Search for papers matching the query.

        Args:
            query: Search query string.
            max_results: Maximum number of results to return.
            from_year: Start year filter (inclusive).
            to_year: End year filter (inclusive).

        Returns:
            List of Paper objects.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this retriever."""
        ...

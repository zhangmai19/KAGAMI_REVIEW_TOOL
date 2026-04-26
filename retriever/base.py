"""Abstract base class for paper retrievers."""

from abc import ABC, abstractmethod
from typing import List, Optional

from models.paper import Paper


class BaseRetriever(ABC):
    """Base class for all paper retrievers.

    Subclasses must implement the `search` method.

    The optional `keyword_groups` parameter enables TS-style boolean
    post-filtering (AND across groups, OR within groups).
    """

    @abstractmethod
    def search(
        self,
        query: str,
        max_results: int = 100,
        from_year: Optional[int] = None,
        to_year: Optional[int] = None,
        keyword_groups: Optional[List[List[str]]] = None,
    ) -> List[Paper]:
        """Search for papers matching the query.

        Args:
            query: Search query string (broad recall terms).
            max_results: Maximum number of results to return.
            from_year: Start year filter (inclusive).
            to_year: End year filter (inclusive).
            keyword_groups: Optional boolean filter groups.
                Each group is a list of terms (OR within group).
                Groups are combined with AND logic.
                When provided, retrievers should fetch more results
                and then apply boolean_filter() to narrow down.

        Returns:
            List of Paper objects.
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of this retriever."""
        ...

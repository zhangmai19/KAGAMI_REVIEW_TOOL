"""Paper chunking for LLM analysis within token limits."""

from typing import List

from models.paper import Paper
from parser.paper_normalizer import papers_to_numbered_text
from utils.token_counter import count_tokens
from utils.logging import get_logger

logger = get_logger(__name__)


def chunk_papers(
    papers: List[Paper],
    max_tokens: int = 12000,
    max_papers_per_chunk: int = 25,
    model: str = "gpt-4o-mini",
) -> List[List[Paper]]:
    """Split papers into chunks that fit within LLM token limits.

    Args:
        papers: List of Paper objects (must have IDs assigned).
        max_tokens: Maximum tokens per chunk.
        max_papers_per_chunk: Maximum papers per chunk.
        model: Model name for token counting.

    Returns:
        List of paper chunks, each a list of Paper objects.
    """
    chunks: List[List[Paper]] = []
    current_chunk: List[Paper] = []

    for paper in papers:
        tentative = current_chunk + [paper]
        text = papers_to_numbered_text(tentative)
        tokens = count_tokens(text, model=model)

        if tokens > max_tokens or len(tentative) > max_papers_per_chunk:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = [paper]
        else:
            current_chunk = tentative

    if current_chunk:
        chunks.append(current_chunk)

    logger.info(
        f"Split {len(papers)} papers into {len(chunks)} chunks "
        f"(max_tokens={max_tokens}, max_papers={max_papers_per_chunk})"
    )

    return chunks

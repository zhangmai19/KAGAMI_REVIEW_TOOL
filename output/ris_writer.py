"""RIS file writer for exporting paper records."""

from typing import List

from models.paper import Paper
from utils.logging import get_logger

logger = get_logger(__name__)


def write_ris_file(papers: List[Paper], output_path: str) -> None:
    """Write papers to an RIS format file.

    Args:
        papers: List of Paper objects.
        output_path: Output file path.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        for paper in papers:
            f.write("TY  - JOUR\n")

            if paper.title:
                f.write(f"TI  - {paper.title}\n")
                f.write(f"T1  - {paper.title}\n")

            if paper.abstract:
                f.write(f"AB  - {paper.abstract}\n")

            for author in paper.authors:
                f.write(f"AU  - {author}\n")

            if paper.year:
                f.write(f"PY  - {paper.year}\n")
                f.write(f"DA  - {paper.year}//\n")

            if paper.doi:
                f.write(f"DO  - {paper.doi}\n")

            if paper.venue:
                f.write(f"JO  - {paper.venue}\n")
                f.write(f"T2  - {paper.venue}\n")

            if paper.url:
                f.write(f"UR  - {paper.url}\n")

            for kw in paper.keywords:
                f.write(f"KW  - {kw}\n")

            f.write("ER  - \n\n")

    logger.info(f"RIS file written to {output_path} with {len(papers)} records")

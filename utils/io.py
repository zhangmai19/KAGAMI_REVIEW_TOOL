"""File I/O utilities."""

import json
from pathlib import Path
from typing import Any, Dict, List

from models.paper import Paper


def ensure_dir(path: str | Path) -> Path:
    """Ensure a directory exists and return its Path."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_jsonl(papers: List[Paper], file_path: str | Path) -> None:
    """Save a list of Paper objects to a JSONL file."""
    file_path = Path(file_path)
    ensure_dir(file_path.parent)

    with file_path.open("w", encoding="utf-8") as f:
        for paper in papers:
            f.write(paper.model_dump_json() + "\n")


def load_jsonl(file_path: str | Path) -> List[Dict[str, Any]]:
    """Load a JSONL file into a list of dictionaries."""
    file_path = Path(file_path)
    records = []

    with file_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))

    return records


def save_json(data: Any, file_path: str | Path, indent: int = 2) -> None:
    """Save data to a JSON file."""
    file_path = Path(file_path)
    ensure_dir(file_path.parent)

    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=indent)


def load_json(file_path: str | Path) -> Any:
    """Load data from a JSON file."""
    file_path = Path(file_path)

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_text(text: str, file_path: str | Path) -> None:
    """Save text to a file."""
    file_path = Path(file_path)
    ensure_dir(file_path.parent)

    file_path.write_text(text, encoding="utf-8")


def read_text(file_path: str | Path) -> str:
    """Read text from a file."""
    file_path = Path(file_path)
    return file_path.read_text(encoding="utf-8")

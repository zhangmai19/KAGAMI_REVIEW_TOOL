"""FastAPI server for AutoLitReview-Agent.

Run with: uvicorn ui.api_server:app --reload
"""

import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from agents.literature_review_agent import LiteratureReviewAgent

app = FastAPI(
    title="AutoLitReview-Agent API",
    description="API for automated literature review with evidence-grounded analysis",
    version="0.1.0",
)

# In-memory job storage (use a database in production)
jobs: Dict[str, Dict[str, Any]] = {}


class SearchRequest(BaseModel):
    """Request body for search-based review."""

    topic: str
    keywords: List[str] = Field(default_factory=list)
    databases: List[str] = Field(default_factory=lambda: ["openalex", "semantic_scholar"])
    max_papers: int = 150
    from_year: Optional[int] = None
    to_year: Optional[int] = None
    model: str = "gpt-4o-mini"
    max_tokens_per_chunk: int = 12000
    max_papers_per_chunk: int = 25


class FileReviewRequest(BaseModel):
    """Request body for file-based review."""

    topic: str
    model: str = "gpt-4o-mini"
    max_tokens_per_chunk: int = 12000
    max_papers_per_chunk: int = 25


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "AutoLitReview-Agent API",
        "version": "0.1.0",
        "docs": "/docs",
    }


@app.post("/api/review/upload")
async def review_from_upload(
    topic: str,
    file: UploadFile = File(...),
    model: str = "gpt-4o-mini",
    max_tokens_per_chunk: int = 12000,
    max_papers_per_chunk: int = 25,
):
    """Run a literature review from an uploaded file.

    Accepts RIS, BibTeX, or CSV files.
    """
    # Save uploaded file
    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        output_dir = tempfile.mkdtemp()
        agent = LiteratureReviewAgent(
            model=model,
            output_dir=output_dir,
            max_tokens_per_chunk=max_tokens_per_chunk,
            max_papers_per_chunk=max_papers_per_chunk,
        )

        result = agent.review_from_file(topic=topic, file_path=tmp_path)

        # Store job result
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "status": "completed",
            "result": result,
            "output_dir": output_dir,
        }

        return JSONResponse(
            content={"job_id": job_id, "status": "completed", "result": result}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.post("/api/review/search")
async def review_from_search(request: SearchRequest):
    """Run a literature review by searching academic databases."""
    try:
        output_dir = tempfile.mkdtemp()
        agent = LiteratureReviewAgent(
            model=request.model,
            output_dir=output_dir,
            max_tokens_per_chunk=request.max_tokens_per_chunk,
            max_papers_per_chunk=request.max_papers_per_chunk,
        )

        result = agent.review_from_search(
            topic=request.topic,
            keywords=request.keywords or [request.topic],
            databases=request.databases,
            max_papers=request.max_papers,
            from_year=request.from_year,
            to_year=request.to_year,
        )

        # Store job result
        job_id = str(uuid.uuid4())
        jobs[job_id] = {
            "status": "completed",
            "result": result,
            "output_dir": output_dir,
        }

        return JSONResponse(
            content={"job_id": job_id, "status": "completed", "result": result}
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    """Get the status of a review job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    return jobs[job_id]


@app.get("/api/jobs/{job_id}/report")
async def get_job_report(job_id: str, format: str = "markdown"):
    """Download the report for a completed review job."""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail="Job not found")

    job = jobs[job_id]
    if job["status"] != "completed":
        raise HTTPException(status_code=400, detail="Job not completed")

    output_dir = job.get("output_dir")
    if not output_dir:
        raise HTTPException(status_code=404, detail="Output directory not found")

    format_map = {
        "markdown": "final_report.md",
        "json": "final_report.json",
    }

    filename = format_map.get(format)
    if not filename:
        raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

    file_path = Path(output_dir) / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Report file not found: {filename}")

    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type=_get_media_type(format),
    )


def _get_media_type(format: str) -> str:
    """Get media type for response."""
    types = {
        "markdown": "text/markdown",
        "json": "application/json",
    }
    return types.get(format, "application/octet-stream")

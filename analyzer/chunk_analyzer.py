"""Chunk-level analysis of paper corpus."""

from typing import Any, Dict, List

from models.paper import Paper
from parser.paper_normalizer import papers_to_numbered_text
from analyzer.llm_client import LLMClient
from utils.logging import get_logger

logger = get_logger(__name__)

CHUNK_SYSTEM_PROMPT = """You are a systematic literature review assistant.

You must strictly follow the rules below.

GLOBAL RULES:
1. Use ONLY the provided paper records.
2. Each paper record contains an ID, title, year, and abstract.
3. You must not use external knowledge.
4. You must not infer details that are not explicitly supported by the title or abstract.
5. Every analytical claim must include one or more evidence IDs such as ["#3", "#8"].
6. Do not cite any paper ID that is not present in the input.
7. If the abstracts do not provide enough evidence for a requested category, write "insufficient_evidence".
8. Do not fabricate methods, theories, data types, results, or research gaps.
9. Prefer conservative synthesis over broad speculation.
10. Output valid JSON only.

If the information is not explicitly present in the provided title or abstract,
you must not include it.

Do not rely on common knowledge, prior knowledge, or assumptions.

A claim without an evidence ID is invalid.

A claim with a wrong or nonexistent evidence ID is invalid.

When uncertain, use "insufficient_evidence".
"""

CHUNK_USER_TEMPLATE = """You are analyzing one chunk of a larger systematic literature review corpus.

STRICT EVIDENCE RULES:
- Use only the papers in this chunk.
- Do not mention papers outside this chunk.
- Every claim must cite paper IDs from this chunk.
- If a category is not supported by abstracts, return an empty list or "insufficient_evidence".
- Do not create broad conclusions beyond this chunk.

CHUNK ID:
{chunk_id}

PAPERS:
{papers_text}

Return valid JSON using this schema:
{{
  "chunk_id": "{chunk_id}",
  "papers_covered": [],
  "topic_clusters": [
    {{
      "cluster_name": "string",
      "description": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "research_questions": [
    {{
      "question": "string",
      "description": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "method_categories": [
    {{
      "method_type": "string",
      "description": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "theoretical_frameworks": [
    {{
      "framework": "string",
      "description": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "data_types": [
    {{
      "data_type": "string",
      "description": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "key_findings": [
    {{
      "finding": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "research_gaps": [
    {{
      "gap": "string",
      "description": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "limitations": [
    {{
      "limitation": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "uncertain_or_missing": [
    {{
      "item": "string",
      "reason": "string",
      "evidence_ids": ["#1"]
    }}
  ]
}}
"""


class ChunkAnalyzer:
    """Analyze a chunk of papers using LLM."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def analyze_chunk(
        self,
        chunk_id: int,
        papers: List[Paper],
    ) -> Dict[str, Any]:
        """Analyze a single chunk of papers.

        Args:
            chunk_id: Chunk identifier.
            papers: List of papers in this chunk.

        Returns:
            Structured analysis result as a dictionary.
        """
        papers_text = papers_to_numbered_text(papers)

        user_prompt = CHUNK_USER_TEMPLATE.format(
            chunk_id=chunk_id,
            papers_text=papers_text,
        )

        logger.info(f"Analyzing chunk {chunk_id} with {len(papers)} papers")

        try:
            result = self.llm_client.complete_json(
                system_prompt=CHUNK_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            # Ensure chunk_id is set
            result["chunk_id"] = chunk_id
            return result
        except Exception as e:
            logger.error(f"Chunk {chunk_id} analysis failed: {e}")
            return {
                "chunk_id": chunk_id,
                "papers_covered": [p.id for p in papers if p.id],
                "error": str(e),
                "topic_clusters": [],
                "research_questions": [],
                "method_categories": [],
                "theoretical_frameworks": [],
                "data_types": [],
                "key_findings": [],
                "research_gaps": [],
                "limitations": [],
                "uncertain_or_missing": [],
            }

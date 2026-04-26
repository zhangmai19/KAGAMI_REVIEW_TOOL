"""Global synthesis of chunk-level analyses."""

import json
from typing import Any, Dict, List

from analyzer.llm_client import LLMClient
from utils.logging import get_logger

logger = get_logger(__name__)

GLOBAL_SYSTEM_PROMPT = """You are synthesizing chunk-level systematic review analyses.

Use only the provided chunk-level JSON.
Do not introduce new facts.
Every synthesized claim must preserve evidence IDs.
Output valid JSON only.

If the information is not explicitly present in the chunk analyses,
you must not include it.

Do not rely on common knowledge, prior knowledge, or assumptions.

A claim without an evidence ID is invalid.

A claim with a wrong or nonexistent evidence ID is invalid.

When uncertain, use "insufficient_evidence".
"""

GLOBAL_USER_TEMPLATE = """You are synthesizing chunk-level analyses into a global systematic literature review.

STRICT RULES:
1. Use only the provided chunk-level JSON analyses.
2. Do not introduce new claims that are not present in the chunk analyses.
3. Merge overlapping clusters, methods, data types, findings, and gaps.
4. Preserve all evidence IDs.
5. Every synthesized claim must include evidence_ids.
6. If a section lacks evidence, write "insufficient_evidence".
7. Do not cite IDs that do not appear in the chunk analyses.
8. Output valid JSON only.

INPUT CHUNK ANALYSES:
{chunk_json_list}

OUTPUT JSON SCHEMA:
{{
  "global_topic_clusters": [
    {{
      "cluster_name": "string",
      "synthesis": "string",
      "evidence_ids": ["#1", "#2"]
    }}
  ],
  "global_research_questions": [
    {{
      "question": "string",
      "synthesis": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "global_method_categories": [
    {{
      "method_type": "string",
      "synthesis": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "global_theoretical_frameworks": [
    {{
      "framework": "string",
      "synthesis": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "global_data_types": [
    {{
      "data_type": "string",
      "synthesis": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "global_key_findings": [
    {{
      "finding": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "global_research_gaps": [
    {{
      "gap": "string",
      "synthesis": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "global_limitations": [
    {{
      "limitation": "string",
      "evidence_ids": ["#1"]
    }}
  ],
  "coverage_check": {{
    "all_evidence_ids_used": [],
    "possibly_underused_ids": []
  }}
}}
"""


class Synthesizer:
    """Synthesize chunk-level analyses into a global review."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def synthesize(
        self,
        chunk_results: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Synthesize multiple chunk results into a global review.

        Args:
            chunk_results: List of chunk-level analysis results.

        Returns:
            Global synthesis dictionary.
        """
        chunk_json_list = json.dumps(
            chunk_results,
            ensure_ascii=False,
            indent=2,
        )

        user_prompt = GLOBAL_USER_TEMPLATE.format(
            chunk_json_list=chunk_json_list,
        )

        logger.info(f"Synthesizing {len(chunk_results)} chunk results")

        try:
            result = self.llm_client.complete_json(
                system_prompt=GLOBAL_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
                max_tokens=8192,
            )
            return result
        except Exception as e:
            logger.error(f"Global synthesis failed: {e}")
            raise

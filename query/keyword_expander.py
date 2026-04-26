"""Keyword expansion module using LLM."""

import json
from typing import Any, Dict, List, Optional

from analyzer.llm_client import LLMClient
from utils.logging import get_logger

logger = get_logger(__name__)

KEYWORD_EXPANSION_SYSTEM_PROMPT = """You are an academic search strategist.

Task:
Given a research topic and seed keywords, expand them into high-quality academic search terms.

Rules:
1. Group terms by concept.
2. Include synonyms, abbreviations, spelling variants, singular/plural forms, and related technical terms.
3. Include exclusion terms when a keyword is ambiguous.
4. Do not invent nonexistent academic terms.
5. Prefer terms that are likely to appear in titles, abstracts, or keywords.
6. Output valid JSON only.
"""

KEYWORD_EXPANSION_USER_TEMPLATE = """Research topic:
{topic}

Seed keywords:
{keywords}

Required JSON schema:
{{
  "concepts": [
    {{
      "concept": "string",
      "synonyms": ["string"],
      "variants": ["string"],
      "broader_terms": ["string"],
      "narrower_terms": ["string"],
      "exclude_terms": ["string"],
      "notes": "string"
    }}
  ]
}}
"""


class KeywordExpander:
    """Expand seed keywords into comprehensive academic search terms."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def expand(
        self,
        topic: str,
        seed_keywords: List[str],
    ) -> Dict[str, Any]:
        """Expand seed keywords into comprehensive search terms.

        Args:
            topic: Research topic.
            seed_keywords: List of seed keywords.

        Returns:
            Dictionary with expanded concepts and terms.
        """
        keywords_str = "\n".join(f"- {kw}" for kw in seed_keywords)

        user_prompt = KEYWORD_EXPANSION_USER_TEMPLATE.format(
            topic=topic,
            keywords=keywords_str,
        )

        try:
            result = self.llm_client.complete_json(
                system_prompt=KEYWORD_EXPANSION_SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.0,
            )
            logger.info(f"Expanded {len(seed_keywords)} keywords into {len(result.get('concepts', []))} concepts")
            return result
        except Exception as e:
            logger.error(f"Keyword expansion failed: {e}")
            # Fallback: return simple structure
            return {
                "concepts": [
                    {
                        "concept": kw,
                        "synonyms": [],
                        "variants": [kw, kw + "s"],
                        "broader_terms": [],
                        "narrower_terms": [],
                        "exclude_terms": [],
                        "notes": "Fallback expansion due to LLM error",
                    }
                    for kw in seed_keywords
                ]
            }

    def get_all_search_terms(self, expanded: Dict[str, Any]) -> List[str]:
        """Extract all search terms from expanded keywords.

        Returns a flat list of all terms for boolean query building.
        """
        terms = []
        for concept in expanded.get("concepts", []):
            terms.append(concept.get("concept", ""))
            terms.extend(concept.get("synonyms", []))
            terms.extend(concept.get("variants", []))
        return [t for t in terms if t]

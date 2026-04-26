"""Unified LLM client for analysis calls."""

import json
import os
import re
from typing import Any, Dict, Optional

from utils.logging import get_logger

logger = get_logger(__name__)


def _extract_json_from_text(text: str) -> Optional[str]:
    """Extract JSON content from text that may contain markdown fences or extra content.

    Tries in order:
    1. Direct parse (text is pure JSON)
    2. Extract from ```json ... ``` blocks
    3. Extract from ``` ... ``` blocks
    4. Find first { ... } or [ ... ] block
    """
    if not text or not text.strip():
        return None

    text = text.strip()

    # Try direct parse
    if text.startswith("{") or text.startswith("["):
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass

    # Try extracting from markdown code fences
    fence_match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
    if fence_match:
        candidate = fence_match.group(1).strip()
        try:
            json.loads(candidate)
            return candidate
        except json.JSONDecodeError:
            pass

    # Find first balanced { ... } or [ ... ]
    for opener, closer in [("{", "}"), ("[", "]")]:
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
            if depth == 0:
                candidate = text[start : i + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    break

    return None


class LLMClient:
    """Unified client for LLM API calls.

    Supports OpenAI-compatible APIs including proxies (e.g., Poe API).
    Automatically detects whether the API supports response_format
    and falls back to text-based JSON extraction if not.
    """

    # Known base URLs that do not support response_format
    _NO_JSON_FORMAT_HOSTS = {"api.poe.com", "poe.com"}

    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
    ):
        self.model = model or os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = base_url or os.getenv("OPENAI_BASE_URL")

        self._client = None
        self._supports_json_format: Optional[bool] = None

    @property
    def client(self):
        """Lazy initialization of the OpenAI client."""
        if self._client is None:
            from openai import OpenAI

            kwargs = {}
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.base_url:
                kwargs["base_url"] = self.base_url

            self._client = OpenAI(**kwargs)

        return self._client

    @property
    def supports_json_format(self) -> bool:
        """Check if the current API endpoint supports response_format=json_object."""
        if self._supports_json_format is not None:
            return self._supports_json_format

        if not self.base_url:
            # Official OpenAI API supports it
            self._supports_json_format = True
            return True

        # Check against known hosts that don't support it
        from urllib.parse import urlparse
        try:
            parsed = urlparse(self.base_url)
            host = parsed.hostname or ""
            for no_format_host in self._NO_JSON_FORMAT_HOSTS:
                if no_format_host in host:
                    self._supports_json_format = False
                    logger.info(
                        f"Detected non-OpenAI endpoint ({host}), "
                        f"disabling response_format=json_object"
                    )
                    return False
        except Exception:
            pass

        # Default to not using it for unknown endpoints
        self._supports_json_format = False
        return False

    def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> Dict[str, Any]:
        """Send a prompt and expect a JSON response.

        Automatically handles APIs that don't support response_format
        by extracting JSON from the text response.

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            Parsed JSON dictionary.

        Raises:
            ValueError: If no valid JSON can be extracted from the response.
        """
        kwargs = {
            "model": self.model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        # Only add response_format for APIs that support it
        if self.supports_json_format:
            kwargs["response_format"] = {"type": "json_object"}

        response = self.client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content

        if not content or not content.strip():
            raise ValueError(
                f"LLM returned empty content. Model: {self.model}, "
                f"Base URL: {self.base_url or 'default'}. "
                f"Please check your API key and model name."
            )

        # Try direct JSON parse first
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        # Try extracting JSON from text
        extracted = _extract_json_from_text(content)
        if extracted:
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                pass

        logger.error(
            f"Failed to parse LLM JSON response. "
            f"Model: {self.model}, Content length: {len(content)}"
        )
        logger.debug(f"Raw response (first 1000 chars): {content[:1000]}")
        raise ValueError(
            f"Could not extract valid JSON from LLM response. "
            f"Raw content starts with: {content[:200]}"
        )

    def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
    ) -> str:
        """Send a prompt and return raw text response.

        Args:
            system_prompt: System prompt.
            user_prompt: User prompt.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in response.

        Returns:
            Raw text response.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        return response.choices[0].message.content

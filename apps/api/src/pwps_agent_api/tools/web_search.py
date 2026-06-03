"""Web search tool — supplements local knowledge with internet search.

All results from this tool are tagged with source_type=web and low credibility.
They should be used as supplementary information, not as primary evidence
for high-risk fields.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    """Input for web search tool."""

    query: str = Field(description="Search query to find information on the web.")
    max_results: int = Field(default=5, description="Maximum number of results to return.")


class WebSearchTool(BaseTool):
    """Search the web for welding-related information.

    Results are tagged with low credibility (source_type=web).
    Use this tool to supplement local knowledge when:
    - Local knowledge base doesn't cover a specific topic
    - You need to verify a standard requirement
    - You need current information about materials or processes

    Do NOT use web search results as sole evidence for high-risk fields.
    """

    name: str = "web_search"
    description: str = (
        "Search the web for welding-related information. "
        "Input: search query. "
        "Returns: search results with titles, snippets, and URLs. "
        "Results have LOW credibility — use only as supplementary info."
    )
    args_schema: type[BaseModel] = WebSearchInput

    async def _arun(self, query: str, max_results: int = 5) -> str:
        """Execute web search."""
        try:
            results = await _duckduckgo_search(query, max_results)
            # Tag all results with low credibility
            for r in results:
                r["source_type"] = "web"
                r["credibility"] = 0.3
                r["limitations"] = "Web search result; verify against authoritative sources."
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            log.warning("Web search failed: %s", e)
            return json.dumps({"error": str(e), "results": []})

    def _run(self, query: str, max_results: int = 5) -> str:
        raise NotImplementedError("Use async version")


async def _duckduckgo_search(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    """Search using DuckDuckGo HTML API (no API key required)."""
    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; pWPS-Agent/1.0)",
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, data={"q": query}, headers=headers)
        resp.raise_for_status()
        html = resp.text

    # Simple HTML parsing for results
    results = []
    import re

    # Extract result blocks
    blocks = re.findall(
        r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>.*?'
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )

    for href, title, snippet in blocks[:max_results]:
        # Clean HTML tags
        title_clean = re.sub(r"<[^>]+>", "", title).strip()
        snippet_clean = re.sub(r"<[^>]+>", "", snippet).strip()

        # Decode DuckDuckGo redirect URL
        actual_url = href
        if "uddg=" in href:
            match = re.search(r"uddg=([^&]+)", href)
            if match:
                from urllib.parse import unquote

                actual_url = unquote(match.group(1))

        if title_clean and snippet_clean:
            results.append({
                "title": title_clean,
                "snippet": snippet_clean,
                "url": actual_url,
            })

    return results


async def _tavily_search(query: str, max_results: int = 5, api_key: str = "") -> list[dict[str, Any]]:
    """Search using Tavily API (requires API key)."""
    url = "https://api.tavily.com/search"
    payload = {
        "query": query,
        "max_results": max_results,
        "api_key": api_key,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

    results = []
    for item in data.get("results", []):
        results.append({
            "title": item.get("title", ""),
            "snippet": item.get("content", "")[:300],
            "url": item.get("url", ""),
        })

    return results

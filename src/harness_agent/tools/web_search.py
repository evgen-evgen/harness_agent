from __future__ import annotations

import os
from html.parser import HTMLParser
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import httpx

from harness_agent.risk import ToolRiskLevel
from harness_agent.tools.base import ToolResult


class WebSearchTool:
    name = "web_search"
    description = "Search the web for current public information."
    risk_level = ToolRiskLevel.READ_ONLY
    cacheable = True
    cache_version = "v2"
    input_schema: dict[str, Any] = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results.",
                "minimum": 1,
                "maximum": 10,
                "default": 5,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        *,
        brave_api_key: str | None = None,
        tavily_api_key: str | None = None,
        cache_ttl_seconds: int | None = 900,
    ) -> None:
        self.brave_api_key = brave_api_key
        self.tavily_api_key = tavily_api_key
        self.cache_ttl_seconds = cache_ttl_seconds

    async def run(self, query: str, max_results: int = 5) -> ToolResult:
        max_results = max(1, min(max_results, 10))
        if self.brave_api_key:
            return await self._brave(query, max_results)
        if self.tavily_api_key:
            return await self._tavily(query, max_results)
        return await self._duckduckgo(query, max_results)

    async def _brave(self, query: str, max_results: int) -> ToolResult:
        headers = {"X-Subscription-Token": self.brave_api_key or os.environ["BRAVE_SEARCH_API_KEY"]}
        params = {"q": query, "count": max_results}
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers=headers,
                params=params,
            )
            response.raise_for_status()
        data = response.json()
        results = data.get("web", {}).get("results", [])[:max_results]
        return ToolResult(ok=True, content=self._format_results(results), metadata={"provider": "brave"})

    async def _tavily(self, query: str, max_results: int) -> ToolResult:
        payload = {
            "api_key": self.tavily_api_key or os.environ["TAVILY_API_KEY"],
            "query": query,
            "max_results": max_results,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
        data = response.json()
        results = data.get("results", [])[:max_results]
        return ToolResult(ok=True, content=self._format_results(results), metadata={"provider": "tavily"})

    async def _duckduckgo(self, query: str, max_results: int) -> ToolResult:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": "1",
                    "skip_disambig": "1",
                },
            )
            response.raise_for_status()
            data = response.json()
            results = self._duckduckgo_results(data, max_results)
            if not results:
                response = await client.post(
                    "https://html.duckduckgo.com/html/",
                    data={"q": query},
                    headers={"User-Agent": "harness-agent/0.1"},
                )
                response.raise_for_status()
                results = self._duckduckgo_html_results(response.text, max_results)
        return ToolResult(
            ok=True,
            content=self._format_results(results),
            metadata={"provider": "duckduckgo", "result_count": len(results)},
        )

    @classmethod
    def _duckduckgo_results(cls, data: dict[str, Any], max_results: int) -> list[dict[str, str]]:
        results: list[dict[str, str]] = []
        abstract = data.get("AbstractText")
        abstract_url = data.get("AbstractURL")
        heading = data.get("Heading") or "DuckDuckGo result"
        if abstract:
            results.append({"title": heading, "url": abstract_url or "", "content": abstract})

        for item in data.get("Results", []):
            cls._append_duckduckgo_item(results, item)

        for topic in data.get("RelatedTopics", []):
            if "Topics" in topic:
                for item in topic.get("Topics", []):
                    cls._append_duckduckgo_item(results, item)
            else:
                cls._append_duckduckgo_item(results, topic)

        return results[:max_results]

    @staticmethod
    def _append_duckduckgo_item(results: list[dict[str, str]], item: dict[str, Any]) -> None:
        text = item.get("Text")
        url = item.get("FirstURL") or ""
        if not text:
            return
        title = text.split(" - ", 1)[0][:120]
        results.append({"title": title, "url": url, "content": text})

    @classmethod
    def _duckduckgo_html_results(cls, html: str, max_results: int) -> list[dict[str, str]]:
        parser = _DuckDuckGoHtmlParser(max_results=max_results)
        parser.feed(html)
        parser.close()
        return parser.results

    @staticmethod
    def _normalize_duckduckgo_url(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url)
        query = parse_qs(parsed.query)
        if "uddg" in query and query["uddg"]:
            return unquote(query["uddg"][0])
        return url

    @staticmethod
    def _format_results(results: list[dict[str, Any]]) -> str:
        if not results:
            return "No results."
        lines: list[str] = []
        for index, item in enumerate(results, start=1):
            title = item.get("title") or item.get("name") or "Untitled"
            url = item.get("url") or item.get("link") or ""
            snippet = item.get("description") or item.get("content") or ""
            lines.append(f"{index}. {title}\n   {url}\n   {snippet}".strip())
        return "\n\n".join(lines)


class _DuckDuckGoHtmlParser(HTMLParser):
    def __init__(self, *, max_results: int) -> None:
        super().__init__(convert_charrefs=True)
        self.max_results = max_results
        self.results: list[dict[str, str]] = []
        self._current: dict[str, str] | None = None
        self._capture_title = False
        self._capture_snippet = False
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_by_name = {name: value or "" for name, value in attrs}
        classes = set(attrs_by_name.get("class", "").split())
        if tag == "a" and "result__a" in classes:
            self._flush_current()
            self._current = {
                "title": "",
                "url": WebSearchTool._normalize_duckduckgo_url(attrs_by_name.get("href", "")),
                "content": "",
            }
            self._capture_title = True
            self._parts = []
            return
        if "result__snippet" in classes and self._current is not None:
            self._capture_snippet = True
            self._parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._capture_title and self._current is not None:
            self._current["title"] = self._clean_text(" ".join(self._parts))
            self._capture_title = False
            self._parts = []
            return
        if self._capture_snippet and tag in {"a", "td", "div"} and self._current is not None:
            self._current["content"] = self._clean_text(" ".join(self._parts))
            self._capture_snippet = False
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._capture_title or self._capture_snippet:
            self._parts.append(data)

    def close(self) -> None:
        self._flush_current()
        super().close()

    def _flush_current(self) -> None:
        if len(self.results) >= self.max_results or self._current is None:
            self._current = None
            return
        title = self._current.get("title", "")
        url = self._current.get("url", "")
        if title and url:
            self.results.append(self._current)
        self._current = None

    @staticmethod
    def _clean_text(text: str) -> str:
        return " ".join(text.split())

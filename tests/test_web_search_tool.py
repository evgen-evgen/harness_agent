from harness_agent.tools.registry import default_tool_registry
from harness_agent.config import RuntimeSettings
from harness_agent.tools.web_search import WebSearchTool


def test_web_search_tool_gets_keys_from_runtime_settings(tmp_path) -> None:
    settings = RuntimeSettings(
        _env_file=None,
        BRAVE_SEARCH_API_KEY="brave-test-key",
        WEB_SEARCH_CACHE_TTL_SECONDS=123,
        METRICS_PATH=tmp_path / "metrics.jsonl",
    )

    tool = default_tool_registry(settings=settings).get("web_search")

    assert tool.brave_api_key == "brave-test-key"
    assert tool.cacheable is True
    assert tool.cache_ttl_seconds == 123
    assert tool.cache_version == "v2"


def test_web_search_tool_normalizes_duckduckgo_results() -> None:
    results = WebSearchTool._duckduckgo_results(
        {
            "Heading": "Example",
            "AbstractText": "Abstract",
            "AbstractURL": "https://example.com",
            "RelatedTopics": [
                {"Text": "Topic one - description", "FirstURL": "https://example.com/1"},
                {"Topics": [{"Text": "Nested topic", "FirstURL": "https://example.com/2"}]},
            ],
        },
        max_results=2,
    )

    assert results == [
        {"title": "Example", "url": "https://example.com", "content": "Abstract"},
        {
            "title": "Topic one",
            "url": "https://example.com/1",
            "content": "Topic one - description",
        },
    ]


def test_web_search_tool_parses_duckduckgo_html_results() -> None:
    results = WebSearchTool._duckduckgo_html_results(
        """
        <html>
          <body>
            <a class="result__a" href="/l/?uddg=https%3A%2F%2Fexample.com%2Fone">First result</a>
            <a class="result__snippet">First snippet</a>
            <a class="result__a" href="https://example.com/two">Second result</a>
            <a class="result__snippet">Second snippet</a>
          </body>
        </html>
        """,
        max_results=1,
    )

    assert results == [
        {
            "title": "First result",
            "url": "https://example.com/one",
            "content": "First snippet",
        }
    ]

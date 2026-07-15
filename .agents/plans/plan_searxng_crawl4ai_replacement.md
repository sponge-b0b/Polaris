# Open-Source Web Retrieval Replacement Plan: SearXNG + Crawl4AI

## Summary

Replace the current Firecrawl RAG web fallback with a fully open-source two-stage web retrieval stack:

RagWebFallbackService
→ WebRetrievalProvider
→ SearXNG search/discovery client
→ Crawl4AI concurrent content acquisition client
→ sanitized transient RagRetrievedContext

This preserves Polaris architecture while removing Firecrawl cloud/API-key reliance.

References:

- SearXNG docs: https://docs.searxng.org/
- SearXNG search API: https://docs.searxng.org/dev/search_api.html
- Crawl4AI GitHub: https://github.com/unclecode/crawl4ai

## Key Architectural Decisions

- Remove Firecrawl completely; do not keep a fallback unless explicitly requested later.
- Use SearXNG only for query-to-URL discovery.
- Use Crawl4AI only for crawling, extraction, and clean Markdown acquisition.
- Keep both behind the existing WebRetrievalProvider boundary.
- Keep web fallback evidence transient and untrusted.
- Do not persist crawled web pages as curated RAG records unless a separate curated-ingestion policy explicitly promotes them.
- Do not expose SearXNG or Crawl4AI directly to RAG services, intelligence nodes, MCP tools, or CLI code.

## Implementation Steps

### Step 1 — Inventory and baseline current Firecrawl behavior ✅ Completed

- Locate all active Firecrawl references in code, tests, settings, CLI help text, README, and docs.
- Confirm current flow:
    - RagWebFallbackService
    - FirecrawlWebRetrievalProvider
    - FirecrawlWebClient
    - WebRetrievalProvider
    - RagRetrievedContext

- Run existing focused tests before replacement.

Verification:

uv run pytest -q tests/unit/integration/clients/rag/test_firecrawl_web_client.py tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py

### Step 2 — Replace dependencies and settings ✅ Completed

- Remove firecrawl-py.
- Add crawl4ai.
- Add or confirm httpx remains available for SearXNG.
- Replace Firecrawl settings with provider-neutral and open-source settings:

RAG_WEB_FALLBACK_ENABLED: bool = False
RAG_WEB_FALLBACK_MAX_RESULTS: int = 5

SEARXNG_BASE_URL: str = "http://localhost:8080"
SEARXNG_TIMEOUT_SECONDS: float = 15.0
SEARXNG_SAFE_SEARCH: int = 1
SEARXNG_LANGUAGE: str = "en"
SEARXNG_CATEGORIES: str = "general"

CRAWL4AI_TIMEOUT_SECONDS: float = 30.0
CRAWL4AI_HEADLESS: bool = True
CRAWL4AI_CACHE_ENABLED: bool = True
CRAWL4AI_MAX_CONCURRENCY: int = 4
CRAWL4AI_USER_AGENT: str | None = None

- Remove active FIRECRAWL_* settings from config/settings.py and .env.example.

Verification:

uv sync
uv run python -c "from config.settings import Settings; print(Settings().RAG_WEB_FALLBACK_ENABLED)"

### Step 3 — Add typed web retrieval DTOs ✅ Completed

Create shared typed internal DTOs for the integration layer:

@dataclass(frozen=True, slots=True)
class WebSearchCandidate:
    url: str
    title: str
    snippet: str | None
    rank: int
    score: float | None
    source_engine: str | None


@dataclass(frozen=True, slots=True)
class CrawledWebDocument:
    url: str
    title: str
    markdown: str
    content_hash: str
    fetched_at: datetime

Rules:

- SearXNG returns WebSearchCandidate.
- Crawl4AI returns CrawledWebDocument.
- The provider converts documents into RagRetrievedContext.
- No raw SearXNG or Crawl4AI SDK objects cross the client boundary.

Verification:

uv run pytest -q tests/unit/integration/clients/rag/

### Step 4 — Implement SearxngSearchClient ✅ Completed

Add a vendor/local-service client responsible for SearXNG search discovery.

Responsibilities:

- Call SearXNG /search.
- Request JSON format.
- Pass query, language, categories, safe-search, and result limit.
- Normalize results into WebSearchCandidate.
- Deduplicate malformed or empty URLs.
- Apply timeout handling.
- Do not sanitize content here; this client only discovers URLs.

Expected behavior:

query → candidate URLs

Verification:

- Unit test with mocked httpx.AsyncClient.
- Cover:
    - valid JSON results
    - missing title/snippet
    - duplicate URLs
    - empty result set
    - non-200 response
    - malformed JSON

### Step 5 — Implement Crawl4AiContentClient ✅ Completed

Add a Crawl4AI client responsible for concurrent content acquisition.

Responsibilities:

- Own Crawl4AI AsyncWebCrawler.
- Configure BrowserConfig.
- Configure CrawlerRunConfig.
- Crawl selected candidate URLs concurrently with a bounded concurrency limit.
- Prefer clean Markdown output.
- Drop empty or failed pages.
- Return typed CrawledWebDocument.
- Compute deterministic content_hash.

Expected behavior:

candidate URLs → clean Markdown documents

Verification:

- Unit test with fake Crawl4AI crawler/results.
- Cover:
    - successful markdown extraction
    - failed page ignored
    - empty markdown ignored
    - concurrency limit respected
    - content hash stable
    - title fallback to URL when missing

### Step 6 — Add composed open-source web retrieval provider ✅ Completed

Replace FirecrawlWebRetrievalProvider with a provider such as:

OpenSourceWebRetrievalProvider

Responsibilities:

1. Search SearXNG for candidate URLs.
2. Deduplicate candidates.
3. Crawl candidates with Crawl4AI.
4. Sanitize all Markdown using existing RAG security sanitation.
5. Convert sanitized documents into RagRetrievedContext.
6. Mark metadata as:

{
    "provider": "searxng+crawl4ai",
    "search_provider": "searxng",
    "crawl_provider": "crawl4ai",
    "transient": True,
    "untrusted": True,
}

7. Emit provider telemetry once at this canonical provider boundary.

Verification:

uv run pytest -q tests/unit/integration/providers/rag/

### Step 7 — Update DI and RAG graph wiring ✅ Completed

- Replace Firecrawl client/provider registration in:
    - integration/clients/rag/di.py
    - integration/providers/rag/di.py
    - application/rag/di.py

- Gate web fallback with RAG_WEB_FALLBACK_ENABLED.
- Keep RagWebFallbackService unchanged except for provider-neutral operation naming.
- Rename telemetry operation from Firecrawl-specific language to:

web_fallback_retrieval

Verification:

uv run pytest -q tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_package_imports.py

### Step 8 — Remove Firecrawl code and tests ✅ Completed

- Delete Firecrawl-specific client/provider modules.
- Replace Firecrawl tests with SearXNG, Crawl4AI, and composed provider tests.
- Remove Firecrawl package references from dependency files.
- Remove active Firecrawl mentions from docs, README, CLI help text, and settings.

Verification:

grep -R "Firecrawl\\|firecrawl\\|FIRECRAWL" -n application integration interfaces config tests README.md docs pyproject.toml

Expected result: no active Firecrawl references.

### Step 9 — Add optional live integration tests ✅ Completed

Add opt-in live tests that are skipped unless explicitly configured.

Required services for live validation:

SearXNG running locally
Crawl4AI browser dependencies installed
Network access available

Example environment:

RAG_WEB_FALLBACK_ENABLED=true
SEARXNG_BASE_URL=http://localhost:8080
CRAWL4AI_LIVE_TEST=true

Live test should verify:

1. SearXNG returns at least one candidate URL.
2. Crawl4AI extracts non-empty Markdown from a selected URL.
3. The composed provider returns sanitized RagRetrievedContext.
4. Metadata marks context as transient and untrusted.

Example command:

CRAWL4AI_LIVE_TEST=true uv run pytest -q tests/integration/rag/test_open_source_web_retrieval_live.py

### Step 10 — Update documentation ✅ Completed

- README.md
- docs/platform_rag_pipeline.md
- relevant MCP docs
- .env.example

Document:

- SearXNG handles search/discovery.
- Crawl4AI handles content acquisition.
- Web fallback is disabled by default.
- Web fallback requires explicit request permission and configuration.
- Web evidence is transient and untrusted.
- Crawl4AI setup may require:

uv run crawl4ai-setup
uv run crawl4ai-doctor

- If browser dependencies are missing:

uv run python -m playwright install --with-deps chromium

### Step 11 — Final verification ✅ Completed

Run:

uv run ruff check . --fix
uv run ruff format .
uv run mypy . --explicit-package-bases
uv run pytest -q tests/unit/application/rag tests/unit/integration/clients/rag tests/unit/integration/providers/rag
uv run graphify update .

Final acceptance criteria:

- Firecrawl dependency removed.
- Firecrawl settings removed.
- SearXNG search client implemented.
- Crawl4AI content client implemented.
- Composed provider implements existing WebRetrievalProvider.
- RAG fallback still returns sanitized transient RagRetrievedContext.
- No RAG service, intelligence node, MCP tool, or CLI command imports SearXNG or Crawl4AI directly.
- Documentation describes the open-source local web retrieval stack.
- Unit tests pass.
- Optional live test can validate SearXNG + Crawl4AI end to end.

## Assumptions

- Polaris should fully replace Firecrawl instead of keeping a temporary dual-provider path.
- SearXNG will be self-hosted when live web fallback is needed.
- Crawl4AI browser setup is an operational requirement, not a cloud dependency.
- General web fallback remains optional and disabled by default.
- Curated web ingestion remains separate from transient web fallback.
- No core/ changes are expected for this replacement.


## Step Results


### Step 1 — Inventory and baseline current Firecrawl behavior

Status: Completed.

Confirmed current Firecrawl flow:

```text
RagWebFallbackService
→ FirecrawlWebRetrievalProvider
→ FirecrawlWebClient
→ Firecrawl AsyncFirecrawl.search(..., sources=["web"], scrape_options={formats:["markdown"], only_main_content:true})
→ FirecrawlWebResult
→ sanitize_untrusted_text(...)
→ transient/untrusted RagRetrievedContext
```

Current active Firecrawl responsibilities:

- Query-to-web-result discovery.
- Markdown content acquisition through Firecrawl scrape options.
- Transient/untrusted RAG fallback context creation.
- Provider telemetry under provider name `firecrawl` and operation `web_fallback_search`.
- Application telemetry operation name `firecrawl_web_fallback`.
- Configuration gate via `FIRECRAWL_ENABLED`.

Inventory command output:

```text
## Active Firecrawl references (code/tests/docs/config)
.env.example:9:FIRECRAWL_API_KEY=
README.md:168:Optional provider/API credentials include Alpaca, Alpha Vantage, FRED, NewsAPI, Massive, Firecrawl, Ollama-compatible endpoints, and other data vendors listed in `.env.example`.
README.md:244:RAG uses PostgreSQL as the canonical source, Qdrant for hybrid vector projection, Neo4j for graph projection, and optional Firecrawl/BGE reranking depending on configuration and service availability.
README.md:279:- Firecrawl evidence is transient unless explicitly curated later.
application/rag/di.py:311:        web_provider: FirecrawlWebRetrievalProvider,
application/rag/di.py:323:            if settings.FIRECRAWL_ENABLED
application/rag/di.py:98:from integration.providers.rag.firecrawl_web_retrieval_provider import (
application/rag/di.py:99:    FirecrawlWebRetrievalProvider,
application/rag/retrieval/web_fallback_service.py:30:        operation = "firecrawl_web_fallback"
config/settings.py:66:    FIRECRAWL_API_KEY: Optional[str] = None
config/settings.py:67:    FIRECRAWL_ENABLED: bool = False
config/settings.py:68:    FIRECRAWL_API_URL: str = "https://api.firecrawl.dev"
config/settings.py:69:    FIRECRAWL_TIMEOUT_SECONDS: float = 30.0
docs/platform_future_architecture.md:283:* Firecrawl for search
docs/platform_mcp_server.md:331:Firecrawl, SerpApi, or any web provider as standalone tools. Web retrieval, when
docs/platform_mcp_server.md:34:- PostgreSQL, Qdrant, Neo4j, Firecrawl, providers, and runtime internals are not
docs/platform_mcp_server.md:368:- Firecrawl or web search as standalone tools
docs/platform_rag_pipeline.md:122:request transient Firecrawl evidence. After generation, Self-RAG reflection checks
docs/platform_rag_pipeline.md:161:raw vendor responses, arbitrary JSON, and Firecrawl pages must not be stored as
docs/platform_rag_pipeline.md:33:Qdrant, Neo4j, Firecrawl, embedding, or reranking clients.
docs/platform_rag_pipeline.md:388:| Firecrawl | `https://api.firecrawl.dev` when explicitly enabled |
docs/platform_rag_pipeline.md:44:embedding providers, reranking providers, Ollama model providers, and Firecrawl
docs/platform_rag_pipeline.md:515:  `--web`, and Firecrawl is enabled and configured;
docs/platform_rag_pipeline.md:523:## Firecrawl fallback
docs/platform_rag_pipeline.md:525:Firecrawl is disabled by default. Enable it explicitly in `.env`:
docs/platform_rag_pipeline.md:528:FIRECRAWL_ENABLED=true
docs/platform_rag_pipeline.md:529:FIRECRAWL_API_KEY=your-key
docs/platform_rag_pipeline.md:530:# FIRECRAWL_API_URL=https://api.firecrawl.dev
docs/platform_rag_pipeline.md:539:Both configuration and per-request permission are required. Firecrawl is not a
docs/platform_rag_pipeline.md:5:rebuildable projections; Firecrawl results are transient corrective evidence and
docs/platform_rag_pipeline.md:605:- CRAG grading, corrective rewrites, and Firecrawl fallback;
docs/platform_rag_pipeline.md:658:- **Firecrawl not used:** verify both `FIRECRAWL_ENABLED=true` and the request's
docs/platform_rag_pipeline.md:77:    -> optional corrective rewrite or transient Firecrawl fallback
integration/clients/rag/di.py:13:from integration.clients.rag.firecrawl_web_client import FirecrawlWebClient
integration/clients/rag/di.py:75:    def provide_firecrawl_client(
integration/clients/rag/di.py:78:    ) -> FirecrawlWebClient:
integration/clients/rag/di.py:79:        return FirecrawlWebClient(
integration/clients/rag/di.py:80:            api_key=settings.FIRECRAWL_API_KEY,
integration/clients/rag/di.py:81:            api_url=settings.FIRECRAWL_API_URL,
integration/clients/rag/di.py:82:            timeout_seconds=settings.FIRECRAWL_TIMEOUT_SECONDS,
integration/clients/rag/firecrawl_web_client.py:103:    return FirecrawlWebResult(
integration/clients/rag/firecrawl_web_client.py:11:class FirecrawlWebResult:
integration/clients/rag/firecrawl_web_client.py:22:class FirecrawlSdkSearchClient(Protocol):
integration/clients/rag/firecrawl_web_client.py:26:class FirecrawlWebSearchClient(Protocol):
integration/clients/rag/firecrawl_web_client.py:32:    ) -> tuple[FirecrawlWebResult, ...]: ...
integration/clients/rag/firecrawl_web_client.py:35:class FirecrawlWebClient:
integration/clients/rag/firecrawl_web_client.py:36:    """Vendor client for transient Firecrawl web search results."""
integration/clients/rag/firecrawl_web_client.py:44:        client: FirecrawlSdkSearchClient | None = None,
integration/clients/rag/firecrawl_web_client.py:51:            from firecrawl import AsyncFirecrawl
integration/clients/rag/firecrawl_web_client.py:53:            client = AsyncFirecrawl(
integration/clients/rag/firecrawl_web_client.py:65:    ) -> tuple[FirecrawlWebResult, ...]:
integration/clients/rag/firecrawl_web_client.py:84:        normalized: list[FirecrawlWebResult] = []
integration/clients/rag/firecrawl_web_client.py:92:def _normalize_result(payload: object) -> FirecrawlWebResult | None:
integration/providers/rag/di.py:13:from integration.clients.rag.firecrawl_web_client import FirecrawlWebClient
integration/providers/rag/di.py:152:        client: FirecrawlWebClient,
integration/providers/rag/di.py:154:    ) -> FirecrawlWebRetrievalProvider:
integration/providers/rag/di.py:155:        return FirecrawlWebRetrievalProvider(
integration/providers/rag/di.py:18:from integration.providers.rag.firecrawl_web_retrieval_provider import (
integration/providers/rag/di.py:19:    FirecrawlWebRetrievalProvider,
integration/providers/rag/firecrawl_web_retrieval_provider.py:15:class FirecrawlWebRetrievalProvider(WebRetrievalProvider):
integration/providers/rag/firecrawl_web_retrieval_provider.py:16:    """Normalize Firecrawl search results into transient untrusted RAG context."""
integration/providers/rag/firecrawl_web_retrieval_provider.py:20:        client: FirecrawlWebSearchClient,
integration/providers/rag/firecrawl_web_retrieval_provider.py:32:            "firecrawl",
integration/providers/rag/firecrawl_web_retrieval_provider.py:66:                            "provider": "firecrawl",
integration/providers/rag/firecrawl_web_retrieval_provider.py:83:                        "provider": "firecrawl",
integration/providers/rag/firecrawl_web_retrieval_provider.py:9:from integration.clients.rag.firecrawl_web_client import FirecrawlWebSearchClient
interfaces/cli/commands/rag_command.py:138:            help="Permit transient Firecrawl fallback when curated context is insufficient.",
pyproject.toml:68:    "firecrawl-py>=4.28.2",
tests/integration/mcp_server/test_transport_contracts.py:527:        "firecrawl",
tests/integration/mcp_server/test_transport_contracts.py:528:        "firecrawl_py",
tests/unit/application/rag/test_rag_package_imports.py:6:    "firecrawl",
tests/unit/application/rag/test_rag_service.py:113:    raw_web_payload = "RAW_FIRECRAWL_PAGE_BODY_DO_NOT_PERSIST"
tests/unit/application/rag/test_rag_service.py:128:            source_type="firecrawl_web",
tests/unit/config/test_rag_model_config.py:146:def test_firecrawl_web_fallback_is_disabled_by_default(
tests/unit/config/test_rag_model_config.py:152:    assert settings.FIRECRAWL_ENABLED is False
tests/unit/config/test_rag_model_config.py:153:    assert settings.FIRECRAWL_API_URL == "https://api.firecrawl.dev"
tests/unit/config/test_rag_model_config.py:154:    assert settings.FIRECRAWL_TIMEOUT_SECONDS == 30.0
tests/unit/config/test_rag_model_config.py:23:    "FIRECRAWL_ENABLED",
tests/unit/config/test_rag_model_config.py:24:    "FIRECRAWL_API_URL",
tests/unit/config/test_rag_model_config.py:25:    "FIRECRAWL_TIMEOUT_SECONDS",
tests/unit/core/bootstrap/test_rag_di_composition.py:107:    settings = Settings(FIRECRAWL_ENABLED=False)
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:11:class FakeFirecrawlSdkClient:
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:22:async def test_firecrawl_client_uses_official_async_search_contract() -> None:
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:23:    sdk = FakeFirecrawlSdkClient(
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:34:    client = FirecrawlWebClient(
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:36:        api_url="https://firecrawl.test",
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:61:async def test_firecrawl_client_normalizes_mapping_and_document_metadata() -> None:
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:62:    sdk = FakeFirecrawlSdkClient(
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:76:    client = FirecrawlWebClient(
tests/unit/integration/clients/rag/test_firecrawl_web_client.py:8:from integration.clients.rag.firecrawl_web_client import FirecrawlWebClient
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:15:class FakeFirecrawlWebClient:
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:16:    def __init__(self, results: tuple[FirecrawlWebResult, ...]) -> None:
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:25:    ) -> tuple[FirecrawlWebResult, ...]:
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:31:async def test_firecrawl_provider_sanitizes_and_marks_transient_untrusted_context() -> (
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:34:    client = FakeFirecrawlWebClient(
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:36:            FirecrawlWebResult(
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:49:    provider = FirecrawlWebRetrievalProvider(client)
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:5:from integration.clients.rag.firecrawl_web_client import FirecrawlWebResult
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:6:from integration.providers.rag.firecrawl_web_retrieval_provider import (
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:7:    FirecrawlWebRetrievalProvider,
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py:9:from integration.providers.rag.firecrawl_web_retrieval_provider import (

## Firecrawl/crawl-related paths
application/rag/retrieval/__pycache__/web_fallback_service.cpython-312.pyc
application/rag/retrieval/web_fallback_service.py
integration/clients/rag/__pycache__/firecrawl_web_client.cpython-312.pyc
integration/clients/rag/firecrawl_web_client.py
integration/providers/rag/__pycache__/firecrawl_web_retrieval_provider.cpython-312.pyc
integration/providers/rag/__pycache__/web_retrieval_provider.cpython-312.pyc
integration/providers/rag/firecrawl_web_retrieval_provider.py
integration/providers/rag/web_retrieval_provider.py
interfaces/api/websocket
tests/unit/application/rag/__pycache__/test_web_fallback_service.cpython-312-pytest-9.0.3.pyc
tests/unit/application/rag/test_web_fallback_service.py
tests/unit/integration/clients/rag/__pycache__/test_firecrawl_web_client.cpython-312-pytest-9.0.3.pyc
tests/unit/integration/clients/rag/test_firecrawl_web_client.py
tests/unit/integration/providers/rag/__pycache__/test_firecrawl_web_retrieval_provider.cpython-312-pytest-9.0.3.pyc
tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py
```

Baseline verification command:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/rag/test_firecrawl_web_client.py tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py
```

Baseline verification output:

```text
....                                                                     [100%]Running teardown with pytest sessionfinish...

4 passed in 0.23s
```

Notes:

- Firecrawl currently combines SearXNG's planned discovery role and Crawl4AI's planned acquisition role in one SDK call.
- Replacement must preserve two behaviors: query-to-URL discovery and clean Markdown extraction.
- `RagWebFallbackService` can remain the application boundary; the provider beneath it should change.
- Step 2 should replace Firecrawl configuration with provider-neutral `RAG_WEB_FALLBACK_ENABLED` plus SearXNG/Crawl4AI-specific settings.
- Step 2 will require `uv remove firecrawl-py` and `uv add crawl4ai`; no live SearXNG service is required until the optional live integration step.


### Step 2 — Replace dependencies and settings

Status: Completed.

Changed files:

```text
.env.example
config/settings.py
pyproject.toml
tests/unit/config/test_rag_model_config.py
tests/unit/core/bootstrap/test_rag_di_composition.py
uv.lock
```

Dependency updates performed:

```bash
uv remove firecrawl-py
```

Output:

```text
Resolved 285 packages in 932ms
   Building polaris @ file:///home/bobt/projects/polaris
      Built polaris @ file:///home/bobt/projects/polaris
Prepared 1 package in 576ms
Uninstalled 2 packages in 19ms
Installed 1 package in 1ms
 - firecrawl-py==4.32.0
 ~ polaris==0.1.0 (from file:///home/bobt/projects/polaris)
```

```bash
uv add crawl4ai
```

Output:

```text
Resolved 308 packages in 1.13s
   Building polaris @ file:///home/bobt/projects/polaris
Downloading unclecode-litellm (17.2MiB)
Downloading playwright (45.2MiB)
Downloading shapely (3.0MiB)
Downloading patchright (45.5MiB)
Downloading brotli (1.4MiB)
Downloading nltk (1.6MiB)
      Built polaris @ file:///home/bobt/projects/polaris
 Downloaded brotli
 Downloaded nltk
 Downloaded shapely
 Downloaded unclecode-litellm
 Downloaded playwright
 Downloaded patchright
Prepared 24 packages in 4.07s
Uninstalled 1 package in 0.42ms
Installed 24 packages in 552ms
 + aiofiles==25.1.0
 + alphashape==1.3.1
 + brotli==1.2.0
 + chardet==7.4.3
 + click-log==0.4.0
 + crawl4ai==0.9.2
 + cssselect==1.4.0
 + defusedxml==0.7.1
 + fake-useragent==2.2.0
 + humanize==4.16.0
 + lark==1.3.1
 + nltk==3.10.0
 + patchright==1.61.2
 + playwright==1.61.0
 + playwright-stealth==2.0.3
 ~ polaris==0.1.0 (from file:///home/bobt/projects/polaris)
 + pyee==13.0.1
 + pyopenssl==26.2.0
 + rank-bm25==0.2.2
 + rtree==1.4.1
 + shapely==2.1.2
 + snowballstemmer==2.2.0
 + trimesh==4.12.2
 + unclecode-litellm==1.81.13
```

Settings changes:

- Removed active Firecrawl settings from `Settings`:
  - `FIRECRAWL_API_KEY`
  - `FIRECRAWL_ENABLED`
  - `FIRECRAWL_API_URL`
  - `FIRECRAWL_TIMEOUT_SECONDS`
- Added provider-neutral fallback gate:
  - `RAG_WEB_FALLBACK_ENABLED: bool = False`
  - `RAG_WEB_FALLBACK_MAX_RESULTS: int = 5`
- Added SearXNG search/discovery settings:
  - `SEARXNG_BASE_URL: str = "http://localhost:8080"`
  - `SEARXNG_TIMEOUT_SECONDS: float = 15.0`
  - `SEARXNG_SAFE_SEARCH: int = 1`
  - `SEARXNG_LANGUAGE: str = "en"`
  - `SEARXNG_CATEGORIES: str = "general"`
- Added Crawl4AI content-acquisition settings:
  - `CRAWL4AI_TIMEOUT_SECONDS: float = 30.0`
  - `CRAWL4AI_HEADLESS: bool = True`
  - `CRAWL4AI_CACHE_ENABLED: bool = True`
  - `CRAWL4AI_MAX_CONCURRENCY: int = 4`
  - `CRAWL4AI_USER_AGENT: Optional[str] = None`

Environment example changes:

- Removed `FIRECRAWL_API_KEY`.
- Added a RAG web fallback section documenting SearXNG as the discovery service and Crawl4AI as the acquisition service.

Test updates:

- Updated `tests/unit/config/test_rag_model_config.py` to validate the new open-source web fallback defaults.
- Updated `tests/unit/core/bootstrap/test_rag_di_composition.py` to use `Settings(RAG_WEB_FALLBACK_ENABLED=False)` instead of the removed Firecrawl gate.

Verification commands:

```bash
uv sync
```

Output:

```text
Resolved 308 packages in 0.88ms
Checked 305 packages in 2ms
```

```bash
uv run python -c "from config.settings import Settings; print(Settings().RAG_WEB_FALLBACK_ENABLED)"
```

Output:

```text
False
```

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/config/test_rag_model_config.py
```

Output:

```text
.......                                                                  [100%]Running teardown with pytest sessionfinish...

7 passed in 0.20s
```

Targeted Firecrawl reference check for Step 2 files:

```bash
grep -n "firecrawl\|Firecrawl\|FIRECRAWL\|crawl4ai" pyproject.toml config/settings.py .env.example tests/unit/config/test_rag_model_config.py tests/unit/core/bootstrap/test_rag_di_composition.py | head -120
```

Output:

```text
pyproject.toml:81:    "crawl4ai>=0.9.2",
```

Notes:

- `config/settings.py` is a churn-heavy hotspot according to Repowise, so the change was kept surgical and limited to the Firecrawl-to-open-source configuration surface.
- Step 2 intentionally does not update DI or provider imports yet; those are planned for later steps.
- Until Steps 3–7 are completed, some existing code still references Firecrawl client/provider modules and Firecrawl-specific DI wiring.
- No live SearXNG or Crawl4AI service/browser verification was required for this step.

### Step 3 — Add typed web retrieval DTOs

Status: Completed.

Changed files:

- `integration/clients/rag/web_retrieval_models.py`
- `tests/unit/integration/clients/rag/test_web_retrieval_models.py`
- `.agents/plans/plan_searxng_crawl4ai_replacement.md`

Implementation summary:

- Added shared immutable integration DTOs for the open-source web retrieval boundary:
  - `WebSearchCandidate` for search/discovery results returned by the future SearXNG client.
  - `CrawledWebDocument` for clean Markdown documents returned by the future Crawl4AI client.
- Added lightweight validation so empty required text fields, negative ranks, negative scores, and blank optional source fields fail at construction time.
- Kept the DTOs provider-neutral and independent of raw SearXNG/Crawl4AI SDK or HTTP payloads.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check integration/clients/rag/web_retrieval_models.py tests/unit/integration/clients/rag/test_web_retrieval_models.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/clients/rag/web_retrieval_models.py tests/unit/integration/clients/rag/test_web_retrieval_models.py --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/rag/
```

Results:

- Ruff passed for the new DTO and test files.
- MyPy passed for the new DTO and test files.
- Focused RAG client test suite passed: `33 passed in 11.95s`.

Notes:

- No live SearXNG, Crawl4AI, browser, or Docker service was required for this step.
- Existing Firecrawl modules remain in place until later replacement steps remove or rename them.

### Step 4 — Implement SearxngSearchClient

Status: Completed.

Changed files:

- `integration/clients/rag/searxng_search_client.py`
- `tests/unit/integration/clients/rag/test_searxng_search_client.py`
- `.agents/plans/plan_searxng_crawl4ai_replacement.md`

Implementation summary:

- Added `SearxngSearchClient` as the SearXNG search/discovery client.
- The client calls `/search` with JSON format, query, language, categories, and safe-search parameters.
- The client normalizes JSON results into `WebSearchCandidate` instances.
- The client deduplicates URLs, skips malformed entries, supports injected `httpx.AsyncClient` for tests, and raises clearly for non-success responses and malformed JSON.
- Content sanitization remains out of this client by design; it only discovers candidate URLs.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check integration/clients/rag/searxng_search_client.py tests/unit/integration/clients/rag/test_searxng_search_client.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/clients/rag/searxng_search_client.py tests/unit/integration/clients/rag/test_searxng_search_client.py --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/rag/test_searxng_search_client.py
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/rag/
```

Results:

- Ruff passed for the new client and test files.
- MyPy passed for the new client and test files.
- New SearXNG client tests passed: `7 passed`.
- Focused RAG client suite passed: `40 passed in 7.17s`.

Notes:

- No live SearXNG service was required; Step 4 used mocked `httpx.AsyncClient` behavior only.
- The client returns typed discovery candidates only. Crawl4AI content acquisition is still deferred to Step 5.

### Step 5 — Implement Crawl4AiContentClient

Status: Completed.

Changed files:

- `integration/clients/rag/crawl4ai_content_client.py`
- `tests/unit/integration/clients/rag/test_crawl4ai_content_client.py`
- `.agents/plans/plan_searxng_crawl4ai_replacement.md`

Implementation summary:

- Added `Crawl4AiContentClient` as the Crawl4AI content-acquisition client.
- Added `Crawl4AiContentClientConfig` for timeout, headless mode, cache behavior, bounded concurrency, and optional user agent.
- The client owns Crawl4AI browser/run configuration when no crawler is injected.
- The client supports injected crawler objects for deterministic unit testing without launching a browser.
- Candidate URLs are deduplicated before crawling.
- Crawling is bounded by an `asyncio.Semaphore` using the configured `max_concurrency`.
- Failed pages, timed-out pages, and empty Markdown pages are ignored.
- Successful pages are normalized into `CrawledWebDocument` with deterministic SHA-256 content hashes.
- Title selection prefers crawler result metadata/title and falls back through the search candidate title to the URL.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check integration/clients/rag/crawl4ai_content_client.py tests/unit/integration/clients/rag/test_crawl4ai_content_client.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/clients/rag/crawl4ai_content_client.py tests/unit/integration/clients/rag/test_crawl4ai_content_client.py --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/rag/test_crawl4ai_content_client.py
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/clients/rag/
```

Results:

- Ruff passed for the new Crawl4AI client and test files.
- MyPy passed for the new Crawl4AI client and test files.
- New Crawl4AI client tests passed: `7 passed`.
- Focused RAG client suite passed: `47 passed in 8.08s`.

Notes:

- No live browser, Crawl4AI crawl, SearXNG service, or Docker service was required for this step; tests used a fake crawler.
- Provider-level sanitation and conversion into `RagRetrievedContext` remain deferred to Step 6.

### Step 6 — Add composed open-source web retrieval provider

Status: Completed.

Changed files:

- `integration/providers/rag/open_source_web_retrieval_provider.py`
- `tests/unit/integration/providers/rag/test_open_source_web_retrieval_provider.py`
- `.agents/plans/plan_searxng_crawl4ai_replacement.md`

Implementation summary:

- Added `OpenSourceWebRetrievalProvider` as the composed provider boundary over SearXNG discovery and Crawl4AI content acquisition.
- Added narrow provider-local protocols for `WebSearchClient` and `WebContentClient` so the provider depends on typed behavior, not concrete SDK payloads.
- The provider searches candidate URLs, crawls matching documents, sanitizes untrusted Markdown with the canonical RAG sanitizer, and converts results into `RagRetrievedContext`.
- Added transient and untrusted context metadata with the canonical provider labels:
  - `provider: searxng+crawl4ai`
  - `search_provider: searxng`
  - `crawl_provider: crawl4ai`
- Added URL deduplication, top-k limiting, source lineage, content hash metadata, fetched-at metadata, and security signal metadata.
- Provider telemetry is emitted once at this composed provider boundary using operation `web_fallback_retrieval`.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check integration/providers/rag/open_source_web_retrieval_provider.py tests/unit/integration/providers/rag/test_open_source_web_retrieval_provider.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/providers/rag/open_source_web_retrieval_provider.py tests/unit/integration/providers/rag/test_open_source_web_retrieval_provider.py --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/providers/rag/test_open_source_web_retrieval_provider.py
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/integration/providers/rag/
```

Results:

- Ruff passed for the new provider and test files.
- MyPy passed for the new provider and test files.
- New open-source provider tests passed: `5 passed`.
- Focused RAG provider suite passed: `39 passed in 7.02s`.

Notes:

- No live SearXNG, Crawl4AI/browser, or Docker service was required for this step; tests used fake search/content clients.
- DI wiring still points to the old Firecrawl provider until Step 7.
- Firecrawl source/test removal remains deferred to Step 8.

### Step 7 — Update DI and RAG graph wiring

Status: Completed.

Changed files:

- `integration/clients/rag/di.py`
- `integration/providers/rag/di.py`
- `application/rag/di.py`
- `application/rag/retrieval/web_fallback_service.py`
- `.agents/plans/plan_searxng_crawl4ai_replacement.md`

Implementation summary:

- Replaced Firecrawl client DI registration with separate SearXNG and Crawl4AI client registrations.
- Replaced Firecrawl provider DI registration with `OpenSourceWebRetrievalProvider`, composed from `SearxngSearchClient` and `Crawl4AiContentClient`.
- Updated RAG graph composition to inject `OpenSourceWebRetrievalProvider` behind the existing `RagWebFallbackService` boundary.
- Switched the application fallback gate from `FIRECRAWL_ENABLED` to the provider-neutral `RAG_WEB_FALLBACK_ENABLED`.
- Renamed application-level web fallback telemetry operation to `web_fallback_retrieval`.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check integration/clients/rag/di.py integration/providers/rag/di.py application/rag/di.py application/rag/retrieval/web_fallback_service.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy integration/clients/rag/di.py integration/providers/rag/di.py application/rag/di.py application/rag/retrieval/web_fallback_service.py --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_package_imports.py
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/core/bootstrap/test_rag_di_composition.py
```

Results:

- Ruff passed for all modified DI and web fallback files.
- MyPy passed for all modified DI and web fallback files: `Success: no issues found in 4 source files`.
- Required focused application RAG tests passed: `12 passed in 1.02s`.
- Additional DI composition regression passed: `1 passed in 9.36s` with one unrelated upstream `websockets.legacy` deprecation warning.

Notes:

- Repowise flagged `application/rag/di.py` as churn-heavy/high-risk, so this step was kept surgical and limited to DI type replacement plus the fallback gate rename.
- No live SearXNG, Crawl4AI/browser, or Docker service was required. DI composition instantiates clients but does not perform search, crawling, or browser startup.
- Firecrawl source files, tests, and documentation references still remain by design; those are deferred to Step 8.

### Step 8 — Remove Firecrawl code and tests

Status: Completed.

Changed files:

- Deleted `integration/clients/rag/firecrawl_web_client.py`
- Deleted `integration/providers/rag/firecrawl_web_retrieval_provider.py`
- Deleted `tests/unit/integration/clients/rag/test_firecrawl_web_client.py`
- Deleted `tests/unit/integration/providers/rag/test_firecrawl_web_retrieval_provider.py`
- Updated `interfaces/cli/commands/rag_command.py` help text to provider-neutral web fallback wording.
- Updated `tests/unit/application/rag/test_rag_service.py` to remove Firecrawl-specific transient payload/source labels.
- Updated `tests/unit/application/rag/test_rag_package_imports.py` and `tests/integration/mcp_server/test_transport_contracts.py` to forbid direct Crawl4AI/httpx infrastructure imports at application/MCP boundaries instead of Firecrawl imports.
- Updated `README.md`, `docs/platform_rag_pipeline.md`, `docs/platform_future_architecture.md`, and `docs/platform_mcp_server.md` to describe SearXNG + Crawl4AI instead of Firecrawl.
- Removed stale `__pycache__` artifacts that still contained Firecrawl strings and would otherwise make the verification grep fail.

Implementation summary:

- Removed the obsolete Firecrawl client/provider modules and their dedicated tests.
- Kept the canonical `WebRetrievalProvider` and `RagWebFallbackService` boundaries intact.
- Updated public-facing wording from Firecrawl-specific fallback to open-source web fallback.
- Updated architecture docs to state that SearXNG owns search/discovery and Crawl4AI owns content acquisition/Markdown extraction.
- Preserved MCP and application-layer constraints: transports must not import web-provider infrastructure directly.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check interfaces/cli/commands/rag_command.py tests/unit/application/rag/test_rag_package_imports.py tests/unit/application/rag/test_rag_service.py tests/integration/mcp_server/test_transport_contracts.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy interfaces/cli/commands/rag_command.py tests/unit/application/rag/test_rag_package_imports.py tests/unit/application/rag/test_rag_service.py tests/integration/mcp_server/test_transport_contracts.py --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/application/rag/test_rag_service.py tests/unit/application/rag/test_rag_package_imports.py tests/unit/integration/clients/rag tests/unit/integration/providers/rag tests/integration/mcp_server/test_transport_contracts.py
grep -R "Firecrawl\|firecrawl\|FIRECRAWL" -n application integration interfaces config tests README.md docs pyproject.toml .env.example || true
```

Results:

- Ruff passed for the modified Python boundary/test files.
- MyPy passed for the modified Python boundary/test files: `Success: no issues found in 4 source files`.
- Focused application, integration-client, integration-provider, and MCP transport tests passed: `105 passed in 12.50s`.
- Firecrawl verification grep returned no matches across the active application, integration, interface, config, test, README, docs, dependency, and example environment paths.

Notes:

- Repowise flagged `interfaces/cli/commands/rag_command.py`, `tests/unit/application/rag/test_rag_service.py`, and `tests/integration/mcp_server/test_transport_contracts.py` as churn-heavy, so edits were limited to Firecrawl removal/rewording and boundary import allowlist updates.
- No live SearXNG, Crawl4AI/browser, or Docker service was required for this removal step.
- Optional live validation remains deferred to Step 9.

### Step 9 — Add optional live integration tests

Status: Completed.

Changed files:

- `tests/integration/rag/test_open_source_web_retrieval_live.py`
- `.agents/plans/plan_searxng_crawl4ai_replacement.md`

Implementation summary:

- Added opt-in live integration tests for the SearXNG + Crawl4AI replacement stack.
- Tests are skipped unless `CRAWL4AI_LIVE_TEST=true` is set.
- Added coverage for the three required live-validation points:
  - SearXNG returns candidate URLs for a query.
  - Crawl4AI extracts non-empty Markdown from `https://example.com`.
  - `OpenSourceWebRetrievalProvider` composes live search and crawl results into sanitized transient `RagRetrievedContext` evidence.
- The provider live test verifies `web_fallback` route/source labels and transient/untrusted metadata including `provider`, `search_provider`, and `crawl_provider`.

Verification:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check tests/integration/rag/test_open_source_web_retrieval_live.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy tests/integration/rag/test_open_source_web_retrieval_live.py --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/rag/test_open_source_web_retrieval_live.py
```

Results:

- Ruff passed for the new live integration test file.
- MyPy passed for the new live integration test file: `Success: no issues found in 1 source file`.
- Opt-in live test command passed in local non-live mode with `3 skipped` because `CRAWL4AI_LIVE_TEST=true` was not set.

Live-service instructions:

To run the actual live validation, ensure SearXNG is running and reachable at `SEARXNG_BASE_URL`, Crawl4AI browser dependencies are installed, and outbound network access is available. Then run:

```bash
CRAWL4AI_LIVE_TEST=true UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/integration/rag/test_open_source_web_retrieval_live.py
```

Notes:

- I did not run the live test path because this step was not preceded by confirmation that SearXNG/browser dependencies were running and ready. The test is now available for explicit live validation.
- No production code was changed in this step.

### Step 10 — Update documentation

Status: Completed.

Updated documentation and local service setup for the open-source web fallback stack.

Changes made:

- `README.md` now documents optional `searxng` startup, Crawl4AI setup commands, browser dependency fallback, and the fact that web evidence is transient/untrusted unless explicitly curated.
- `docs/platform_rag_pipeline.md` now documents the SearXNG + Crawl4AI setup commands, the explicit dual gate for web fallback, the default SearXNG endpoint, and the local port split between SearXNG (`8888`) and BGE reranker (`8080`).
- `docs/platform_mcp_server.md` now clarifies that MCP only forwards the web-permission boundary and does not expose or configure SearXNG/Crawl4AI directly.
- `.env.example`, `config/settings.py`, and `tests/unit/config/test_rag_model_config.py` use `http://localhost:8888` as the canonical local SearXNG endpoint.
- `integration/clients/rag/crawl4ai_content_client.py` no longer passes `user_agent=None` into Crawl4AI `BrowserConfig`; optional browser headers are included only when configured.
- `docker-compose.yml` now maps host port `8888` to the current SearXNG container port `8080`.
- `config/searxng/settings.yml` now includes a valid local SearXNG configuration with JSON output enabled and a non-secret local-development placeholder `server.secret_key`.

Live-validation notes:

- Initial live validation exposed two real setup/runtime issues:
  - SearXNG was configured/documented as `localhost:8080`, which conflicts with the BGE reranker endpoint. The Polaris SearXNG default is now `localhost:8888`.
  - The current SearXNG image listens on container port `8080`, so the compose mapping needed to be `8888:8080`.
  - Crawl4AI raised a `BrowserConfig` type error when `user_agent=None` was passed explicitly; the client now omits optional browser fields unless configured.
- The SearXNG container was restarting because its mounted `settings.yml` lacked the required `server.secret_key`; the local config now starts successfully.
- The committed SearXNG secret key value is an intentional non-secret local-development placeholder, not a production credential. Shared/public SearXNG deployments must override it.

Verification run:

```bash
docker compose up -d searxng
docker compose ps searxng
UV_CACHE_DIR=/tmp/uv-cache timeout 8s uv run python - <<'PY'
import asyncio, httpx
async def main():
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.get(
            'http://localhost:8888/search',
            params={'q': 'example domain', 'format': 'json'},
        )
    print(r.status_code, r.headers.get('content-type'))
asyncio.run(main())
PY
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check config/settings.py tests/unit/config/test_rag_model_config.py integration/clients/rag/crawl4ai_content_client.py tests/integration/rag/test_open_source_web_retrieval_live.py
UV_CACHE_DIR=/tmp/uv-cache uv run mypy config/settings.py tests/unit/config/test_rag_model_config.py integration/clients/rag/crawl4ai_content_client.py tests/integration/rag/test_open_source_web_retrieval_live.py --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q tests/unit/config/test_rag_model_config.py tests/unit/integration/clients/rag/test_crawl4ai_content_client.py
docker compose config --quiet
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache timeout 90s uv run graphify update .
CRAWL4AI_LIVE_TEST=true UV_CACHE_DIR=/tmp/uv-cache timeout 90s uv run pytest -q tests/integration/rag/test_open_source_web_retrieval_live.py
```

Results:

- SearXNG probe: `200 application/json`.
- Ruff: passed.
- MyPy: passed for the targeted files.
- Unit tests: `14 passed`.
- Docker Compose config validation: passed.
- Graphify update: passed; `graph.json` and `GRAPH_REPORT.md` refreshed.
- Live SearXNG + Crawl4AI validation: `3 passed`.

Recommendation before Step 11:

- Keep SearXNG running only when live web fallback validation is needed. The normal RAG path remains curated-data first and web fallback remains disabled by default.

### Step 11 — Final verification

Status: Completed.

Final replacement verification completed for the SearXNG + Crawl4AI web fallback stack.

Additional cleanup made during verification:

- Replaced stale MCP prohibited-tool names from Firecrawl-specific entries to provider-neutral web entries:
  - `polaris_firecrawl_search` → `polaris_web_search`
  - `polaris_firecrawl_` → `polaris_web_`
- Removed generated RAG `__pycache__` directories after grep checks surfaced stale binary matches.

Acceptance checks:

- Firecrawl dependency removed from the dependency set.
- Firecrawl settings removed from active settings and `.env.example`.
- SearXNG search client is implemented.
- Crawl4AI content client is implemented.
- `OpenSourceWebRetrievalProvider` implements the existing `WebRetrievalProvider` boundary.
- RAG fallback still returns sanitized transient `RagRetrievedContext` evidence.
- No active application, integration, interface, config, test, README, docs, dependency, or MCP source references to Firecrawl remain. Historical plan files still retain prior planning history by design.
- No intelligence, interface, MCP, or core code imports SearXNG/Crawl4AI directly; the concrete provider is composed at the application DI boundary.
- Documentation describes SearXNG for search/discovery, Crawl4AI for content acquisition, disabled-by-default web fallback, explicit request permission, transient/untrusted web evidence, and local setup commands.

Verification run:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check . --fix
UV_CACHE_DIR=/tmp/uv-cache uv run ruff format .
UV_CACHE_DIR=/tmp/uv-cache timeout 120s uv run mypy . --explicit-package-bases
UV_CACHE_DIR=/tmp/uv-cache timeout 120s uv run pytest -q tests/unit/application/rag tests/unit/integration/clients/rag tests/unit/integration/providers/rag tests/unit/mcp_server/test_tool_allowlist.py
CRAWL4AI_LIVE_TEST=true UV_CACHE_DIR=/tmp/uv-cache timeout 90s uv run pytest -q tests/integration/rag/test_open_source_web_retrieval_live.py
GRAPHIFY_VIZ_NODE_LIMIT=10000 UV_CACHE_DIR=/tmp/uv-cache timeout 120s uv run graphify update .
grep -R "Firecrawl\|firecrawl\|FIRECRAWL" -n application integration interfaces config tests README.md docs pyproject.toml .env.example mcp_server --exclude-dir=__pycache__ --exclude-dir=.pytest_cache --exclude-dir=.mypy_cache --exclude='*.pyc' || true
grep -R "from integration.clients.rag.searxng_search_client\|from integration.clients.rag.crawl4ai_content_client\|from integration.providers.rag.open_source_web_retrieval_provider" -n intelligence interfaces mcp_server core || true
```

Results:

- Ruff check/fix: passed.
- Ruff format: passed; 5 files reformatted during the first final-format run, then no further changes.
- MyPy: `Success: no issues found in 1351 source files`.
- Focused unit regression: `265 passed`.
- Optional live SearXNG + Crawl4AI validation: `3 passed`.
- Graphify update: passed; final run reported no topology changes after the MCP allowlist cleanup.
- Active Firecrawl reference grep: no active matches.
- Direct SearXNG/Crawl4AI import audit outside composition boundaries: no matches.

Notes:

- SearXNG was live during the optional validation and remains useful only for explicit web-fallback testing or requests.
- The committed local SearXNG `server.secret_key` is a non-secret development placeholder; shared/public deployments must override it.
- Historical `.agents/plans/*` files still mention Firecrawl because they preserve previous implementation history and were intentionally not rewritten.

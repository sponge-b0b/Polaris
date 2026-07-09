from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class FedEventsClient:
    """Federal Reserve calendar, news, and RSS event client."""

    FED_URLS = {
        "fomc_calendar": "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm",
        "fed_news": "https://www.federalreserve.gov/newsevents.htm",
        "speeches_rss": "https://www.federalreserve.gov/feeds/press_all.xml",
    }

    def __init__(self, timeout: int = 10) -> None:
        self.timeout = timeout

    async def get_fed_events(self, days_ahead: int = 14) -> list[dict[str, Any]]:
        del days_ahead  # The source endpoints already define their available horizon.
        keys = tuple(self.FED_URLS)
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            results = await asyncio.gather(
                *(
                    self._get_events(url=url, client=client)
                    for url in self.FED_URLS.values()
                ),
                return_exceptions=True,
            )

        parsed_events: list[dict[str, Any]] = []
        failed_sources: list[str] = []
        for source, result in zip(keys, results):
            if isinstance(result, asyncio.CancelledError):
                raise result
            if isinstance(result, BaseException):
                failed_sources.append(source)
                logger.warning(
                    "Federal Reserve event source failed",
                    extra={"event_source": source, "error_type": type(result).__name__},
                    exc_info=(type(result), result, result.__traceback__),
                )
                continue

            parsed_events.extend(self._parse_source(source=source, text=result))

        if len(failed_sources) == len(keys):
            raise RuntimeError("All Federal Reserve event sources failed.")
        return self._normalize(parsed_events)

    async def _get_events(self, url: str, client: httpx.AsyncClient) -> str:
        response = await client.get(url)
        response.raise_for_status()
        return response.text

    def _parse_source(self, *, source: str, text: str) -> list[dict[str, Any]]:
        if source == "fomc_calendar":
            return self._scrape_fomc_calendar(text)
        if source == "fed_news":
            return self._scrape_fed_news(text)
        if source == "speeches_rss":
            return self._parse_rss_events(text)
        raise ValueError(f"Unsupported Federal Reserve event source: {source}")

    def _scrape_fomc_calendar(self, text: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(text, "html.parser")
        events: list[dict[str, Any]] = []
        for row in soup.find_all("tr"):
            columns = row.find_all("td")
            if len(columns) < 2:
                continue
            try:
                date_text = columns[0].get_text(strip=True)
                if "202" not in date_text:
                    continue
                event_time = datetime.strptime(date_text, "%Y-%m-%d").replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue
            events.append(
                {
                    "event": columns[1].get_text(strip=True),
                    "type": "fomc_meeting",
                    "timestamp": event_time.isoformat(),
                }
            )
        return events

    def _scrape_fed_news(self, text: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(text, "html.parser")
        events: list[dict[str, Any]] = []
        for link in soup.find_all("a"):
            event_text = link.get_text(strip=True)
            href = link.get("href", "")
            if not href or "newsevents" not in href:
                continue
            if any(
                keyword in event_text.lower()
                for keyword in ("fomc", "minutes", "speech", "chair")
            ):
                events.append(
                    {
                        "event": event_text,
                        "type": self._classify_event(event_text),
                        # The page does not expose a reliable timestamp per link.
                        "timestamp": None,
                    }
                )
        return events

    def _parse_rss_events(self, text: str) -> list[dict[str, Any]]:
        feed = feedparser.parse(text)
        return [
            {
                "event": entry.get("title", "Fed Event"),
                "type": self._classify_event(str(entry.get("title", ""))),
                "timestamp": entry.get("published") or None,
            }
            for entry in feed.entries[:20]
        ]

    def _classify_event(self, text: str) -> str:
        normalized = text.lower()
        if "fomc" in normalized:
            return "fomc_meeting"
        if "minutes" in normalized:
            return "minutes_release"
        if "speech" in normalized or "chair" in normalized:
            return "fed_speech"
        return "fed_event"

    def _normalize(self, events: list[dict[str, Any]]) -> list[dict[str, Any]]:
        impact_by_type = {
            "fomc_meeting": 1.0,
            "rate_decision": 1.0,
            "fed_speech": 0.85,
            "minutes_release": 0.75,
            "fed_event": 0.6,
        }
        return [
            {
                "name": event.get("event"),
                "event_type": "fed",
                "subtype": event_type,
                "timestamp": event.get("timestamp"),
                "symbol": "SPY",
                "impact": impact_by_type.get(event_type, 0.6),
                "direction_bias": "neutral",
                "source": "fed_events",
            }
            for event in events
            if (event_type := str(event.get("type", "unknown")))
        ]

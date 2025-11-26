import asyncio
import json
import logging
from typing import List

import httpx
from openai import OpenAI

from metadata_extractor.app.config import (
    HARDWARE_CRAWL_INTERVAL_SECONDS,
    HARDWARE_FEED_URL,
    HARDWARE_LLM_MODEL,
    HARDWARE_CRAWLER_PROMPT,
    OPENAI_API_KEY,
    OPENAI_LLM_MODEL,
)
from metadata_extractor.app.services.hardware_store import HardwareItem, upsert_hardware

logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

_crawler_task: asyncio.Task | None = None


async def _fetch_feed() -> str:
    async with httpx.AsyncClient(timeout=15.0) as http:
        resp = await http.get(HARDWARE_FEED_URL)
        resp.raise_for_status()
        return resp.text


async def _extract_items_from_feed(feed_html: str, source_url: str) -> List[HardwareItem]:
    """
    Ask the model to pull structured hardware items out of the HTML feed using the shared prompt.
    """
    prompt = HARDWARE_CRAWLER_PROMPT.format(
        source_url=source_url,
        html=feed_html[:15000],
    )
    response = client.responses.create(
        model=HARDWARE_LLM_MODEL or OPENAI_LLM_MODEL,
        input=prompt,
    )
    try:
        parsed = json.loads(response.output_text)
    except json.JSONDecodeError:
        return []

    items: List[HardwareItem] = []
    for raw in parsed if isinstance(parsed, list) else []:
        name = raw.get("name")
        if not name:
            continue
        items.append(
            {
                "name": name,
                "url": raw.get("url") or raw.get("link"),
                "price": raw.get("price"),
                "source": raw.get("source") or source_url,
            }
        )
    return items


async def crawl_once() -> int:
    """
    Fetch the trusted feed, ask the agent to extract items, and upsert into the DB.
    Returns the count of newly inserted rows.
    """
    try:
        html = await _fetch_feed()
        items = await _extract_items_from_feed(html, HARDWARE_FEED_URL)
        inserted = upsert_hardware(items)
        logger.info("Hardware crawl finished: %s items parsed, %s inserted", len(items), inserted)
        return inserted
    except Exception as exc:
        logger.exception("Hardware crawl failed: %s", exc)
        return 0


async def _run_periodic_crawl(interval_seconds: int) -> None:
    while True:
        await crawl_once()
        await asyncio.sleep(interval_seconds)


def start_periodic_crawl(interval_seconds: int | None = None) -> None:
    """
    Launch the background crawler loop if not already running.
    """
    global _crawler_task
    if _crawler_task and not _crawler_task.done():
        return
    interval = interval_seconds or HARDWARE_CRAWL_INTERVAL_SECONDS
    _crawler_task = asyncio.create_task(_run_periodic_crawl(interval))


async def stop_periodic_crawl() -> None:
    global _crawler_task
    if _crawler_task:
        _crawler_task.cancel()
        try:
            await _crawler_task
        except asyncio.CancelledError:
            pass
        _crawler_task = None

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import List
from urllib.parse import urljoin

import httpx
from openai import OpenAI

from config.settings import get_settings
from metadata_extractor.services.hardware_models import HardwareRecord
from metadata_extractor.services.hardware_store import upsert_hardware

logger = logging.getLogger(__name__)

settings = get_settings()

OPENAI_API_KEY = settings.openai_api_key
OPENAI_LLM_MODEL = settings.openai_model
HARDWARE_LLM_MODEL = os.getenv("HARDWARE_LLM_MODEL")
HARDWARE_FEED_URL = os.getenv("HARDWARE_FEED_URL", "https://example.com")
HARDWARE_FEED_FILE = os.getenv("HARDWARE_FEED_FILE")
HARDWARE_CRAWL_INTERVAL_SECONDS = int(os.getenv("HARDWARE_CRAWL_INTERVAL_SECONDS", "3600"))
HARDWARE_MAX_ITEMS = int(os.getenv("HARDWARE_MAX_ITEMS", "20"))
HARDWARE_LOG_FILE = os.getenv("HARDWARE_LOG_FILE")

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


def _read_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logger.warning("Prompt file missing: %s", path)
        return ""


HARDWARE_CRAWLER_PROMPT = _read_prompt("hardware_crawler_prompt.txt")
LINK_DISCOVERY_PROMPT = _read_prompt("link_discovery_prompt.txt")
REPAIR_PROMPT = _read_prompt("repair_prompt.txt")

client = OpenAI(api_key=OPENAI_API_KEY)

_crawler_task: asyncio.Task | None = None


def _maybe_attach_file_logger() -> None:
    """Attach a file handler for crawler logs if HARDWARE_LOG_FILE is set."""
    if not HARDWARE_LOG_FILE:
        return
    log_path = Path(HARDWARE_LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    already = any(
        isinstance(h, logging.FileHandler) and Path(getattr(h, "baseFilename", "")) == log_path
        for h in logger.handlers
    )
    if already:
        return
    handler = logging.FileHandler(log_path, encoding="utf-8")
    handler.setLevel(logger.level or logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.info("File logging enabled at %s", log_path)


def _log_llm_io(stage: str, content: str, limit: int = 1000) -> None:
    """Log LLM input/output with length and a safe preview."""
    preview = (content[:limit] + "...") if len(content) > limit else content
    logger.info("%s len=%s preview=%r", stage, len(content), preview)

def _log_html(stage: str, html: str, limit: int = 4000) -> None:
    """Log HTML length with a trimmed preview to avoid huge log lines."""
    preview = (html[:limit] + "...") if len(html) > limit else html
    logger.info("%s html_len=%s preview=%r", stage, len(html), preview)


def _sanitize_html(html: str) -> str:
    """
    Strip obvious noise (scripts/styles/comments) and collapse whitespace to reduce LLM trash.
    """
    import re

    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    cleaned = re.sub(r"(?is)<!--.*?-->", " ", cleaned)
    # Prefer body content if present.
    body_match = re.search(r"(?is)<body[^>]*>(.*)</body>", cleaned)
    if body_match:
        cleaned = body_match.group(1)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


async def _get_with_retries(url: str, max_attempts: int = 5, backoff_seconds: float = 5.0) -> str:
    """
    Fetch a URL with simple retry/backoff to handle occasional 429s.
    """
    _maybe_attach_file_logger()
    headers = {"User-Agent": "ChooseYourHardwareCrawler/1.0 (+https://example.com)"}
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(timeout=15.0, headers=headers) as http:
                resp = await http.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == max_attempts:
                break
            await asyncio.sleep(backoff_seconds * attempt)
    if last_error:
        raise last_error
    raise RuntimeError("Failed to fetch URL without specific error")


def _clean_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text[3:]
        text = text.strip()
        if text.lower().startswith("json"):
            text = text[4:]
            text = text.strip()
        if text.endswith("```"):
            text = text[:-3].strip()
    return text


def _extract_power_w(spec: dict[str, object]) -> float | None:
    for key in ("power_consumption_w", "tdp_w", "tdp", "tdp_watts", "power_watts", "power_limit_w"):
        if key not in spec:
            continue
        try:
            value = float(spec.get(key) or 0)
            if value > 0:
                return value
        except Exception:  # noqa: BLE001
            continue
    return None


def _fallback_links_from_html(feed_html: str, source_url: str, max_links: int = 5) -> List[str]:
    """
    Simple regex fallback to pull GPU detail links when the LLM fails to propose any.
    """
    import re

    hrefs = re.findall(r'href="([^"]+gpu-specs[^"]+)"', feed_html, flags=re.IGNORECASE)
    links: List[str] = []
    for href in hrefs:
        full = urljoin(source_url, href.strip())
        if full not in links:
            links.append(full)
        if len(links) >= max_links:
            break
    return links


async def _fetch_feed() -> str:
    if HARDWARE_FEED_FILE:
        try:
            return Path(HARDWARE_FEED_FILE).read_text(encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to read HARDWARE_FEED_FILE %s: %s", HARDWARE_FEED_FILE, exc)
    # Fall back to network fetch.
    return await _get_with_retries(HARDWARE_FEED_URL)


async def _fetch_page(url: str) -> str:
    return await _get_with_retries(url)


async def _discover_links(feed_html: str, source_url: str, max_links: int = 10) -> List[str]:
    """
    Ask the model to propose which links to follow from the feed page.
    Falls back to a regex extraction if the model yields nothing.
    """
    prompt = LINK_DISCOVERY_PROMPT.format(
        source_url=source_url,
        max_links=max_links,
        html=feed_html[:80000],
    )
    _log_html("Feed HTML for discovery", feed_html)
    _log_llm_io("LLM discover prompt", prompt)
    response = client.responses.create(
        model=HARDWARE_LLM_MODEL or OPENAI_LLM_MODEL,
        input=prompt,
    )
    _log_llm_io("LLM discover raw output", response.output_text or "")
    links: List[str] = []
    try:
        parsed = json.loads(response.output_text)
        candidate_list: List[str] = []
        if isinstance(parsed, list):
            candidate_list = parsed
        elif isinstance(parsed, dict):
            if isinstance(parsed.get("urls"), list):
                candidate_list = parsed.get("urls") or []
            elif isinstance(parsed.get("url"), str):
                candidate_list = [parsed.get("url")]
        for raw in candidate_list:
            if not isinstance(raw, str):
                continue
            cleaned = raw.strip()
            if not cleaned.startswith("http"):
                cleaned = "/" + cleaned.lstrip("/")  # ensure single leading slash for urljoin
            full = urljoin(source_url, cleaned)
            if full and full not in links:
                links.append(full)
    except json.JSONDecodeError:
        links = []

    if not links:
        links = _fallback_links_from_html(feed_html, source_url, max_links=max_links)

    limited = links[: max_links or 1]
    logger.info("Link discovery produced %d links (limited to %d)", len(limited), max_links or 1)
    return limited


async def _extract_items_from_feed(feed_html: str, source_url: str) -> List[HardwareRecord]:
    """
    Ask the model to pull structured hardware items out of the HTML feed using the shared prompt.
    """
    # Include more of the combined feed+detail HTML to give the LLM full context.
    sanitized = _sanitize_html(feed_html)
    html_slice = sanitized[:300000]
    prompt = HARDWARE_CRAWLER_PROMPT.format(
        source_url=source_url,
        html=html_slice,
    )
    logger.info("LLM extract prompt_len=%s feed_len=%s sanitized_len=%s", len(prompt), len(feed_html), len(sanitized))
    _log_html("Combined HTML for extract", sanitized)
    _log_llm_io("LLM extract prompt", prompt)

    response = client.responses.create(
        model=HARDWARE_LLM_MODEL or OPENAI_LLM_MODEL,
        input=prompt,
    )
    if not response.output_text:
        logger.warning("LLM returned empty output for hardware extraction")
        return []

    raw_output = response.output_text or ""
    logger.info("LLM extract raw_output_len=%s", len(raw_output))
    _log_llm_io("LLM extract raw output", raw_output)
    raw_text = _clean_json_text(raw_output)
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning("LLM output is not valid JSON (truncated): %s", raw_text[:500])

        # Quick salvage: try to slice the first JSON array present.
        start = raw_text.find("[")
        end = raw_text.rfind("]")
        if start != -1 and end != -1 and end > start:
            try:
                parsed = json.loads(raw_text[start : end + 1])
            except json.JSONDecodeError:
                parsed = None
        else:
            parsed = None

        if parsed is None:
            # Attempt repair once
            repair_prompt = REPAIR_PROMPT.format(raw=raw_text[:4000])
            _log_llm_io("LLM repair prompt", repair_prompt)
            repair_resp = client.responses.create(
                model=HARDWARE_LLM_MODEL or OPENAI_LLM_MODEL,
                input=repair_prompt,
            )
            repair_text = _clean_json_text(repair_resp.output_text or "")
            _log_llm_io("LLM repair raw output", repair_resp.output_text or "")
            try:
                parsed = json.loads(repair_text)
            except json.JSONDecodeError:
                # Last attempt: try to slice the first JSON array found.
                start = repair_text.find("[")
                end = repair_text.rfind("]")
                if start != -1 and end != -1 and end > start:
                    try:
                        parsed = json.loads(repair_text[start : end + 1])
                    except json.JSONDecodeError:
                        logger.warning(
                            "Repair attempt failed; skipping batch. Repair output (truncated): %s",
                            repair_resp.output_text[:500],
                        )
                        return []
                else:
                    logger.warning(
                        "Repair attempt failed; skipping batch. Repair output (truncated): %s",
                        repair_resp.output_text[:500],
                    )
                    return []

    if not isinstance(parsed, list):
        logger.warning("LLM output is not a list; skipping. Raw (truncated): %s", str(parsed)[:500])
        return []

    items: List[HardwareRecord] = []
    skipped = 0
    for raw in parsed if isinstance(parsed, list) else []:
        try:
            record = HardwareRecord.model_validate(
                {
                    **raw,
                    "url": raw.get("url") or raw.get("link"),
                    "source": raw.get("source") or source_url,
                }
            )
            power_w = _extract_power_w(record.spec)
            if power_w is not None:
                # Normalize power key for downstream filtering.
                record.spec["power_consumption_w"] = power_w
            items.append(record)
        except Exception as exc:  # noqa: BLE001
            skipped += 1
            logger.warning("Skipping invalid hardware item (%s): %s", raw.get("hardware_id", "unknown"), exc)
            continue
    if skipped:
        logger.info("Parsed %s items; skipped %s due to validation", len(items), skipped)
    return items


async def crawl_once() -> int:
    """
    Fetch the trusted feed, ask the agent to extract items, and write them into device_data.
    Returns the count of newly created files.
    """
    try:
        html = await _fetch_feed()
        detail_links = await _discover_links(html, HARDWARE_FEED_URL, max_links=10)
        detail_html = ""
        for link in detail_links:
            try:
                await asyncio.sleep(1.0)
                detail_html += f"\n\n<!-- PAGE {link} -->\n"
                page = await _fetch_page(link)
                detail_html += page
                logger.info("Fetched detail page %s (chars=%s)", link, len(page))
            except Exception as exc:  # noqa: BLE001
                logger.debug("Failed to fetch detail page %s: %s", link, exc)
                continue
        combined_html = html + "\n\n" + detail_html
        items = await _extract_items_from_feed(combined_html, HARDWARE_FEED_URL)
        written = upsert_hardware(items)
        logger.info("Hardware crawl finished: %s items parsed, %s written to device_data", len(items), written)
        return written
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

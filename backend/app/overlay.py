"""Spectra Overlay API — URL → fetch HTML → Gemini extracts structured elements for screen-reader / agent view."""

import asyncio
import json
import logging
import os
import re
import time
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["overlay"])

# Truncate HTML to stay within context — 20 KB is enough for nav/interactive elements
# and keeps Gemini latency low on large pages like BBC/WSJ. Reduced from 30KB for faster processing.
MAX_HTML_BYTES = 20_000
# Cache TTL — 1 hour for better performance across sessions
CACHE_TTL = 3600

# In-memory result cache: url → (monotonic_ts, result_dict)
_cache: dict[str, tuple[float, dict]] = {}
# In-flight task dedup: concurrent requests for the same URL share one Gemini call
_inflight: dict[str, "asyncio.Task[dict]"] = {}

SYSTEM_PROMPT = """You are Spectra, an assistant that extracts a structured view of a web page for screen-readers and AI agents.

Given HTML, return a JSON object with:
- "title": string (page title if present, else empty string)
- "elements": flat array of objects, maximum 50 most important elements. Each object must have:
  - "type": one of "button", "link", "input", "heading"
  - "text": visible or accessible text (label, placeholder, or inner text)
  - "role": short role. For headings use the heading level: "h1", "h2", "h3", "h4". For other elements use e.g. "primary_action", "nav", "footer_link", "search", "form_submit", "menu"
  - "selector": simple CSS selector if possible (e.g. "#signup", "nav a[href='/pricing']"), else empty string
  - "importance": one of "high", "medium", "low"

Prioritize high-importance elements first. Include only the top 50 most critical interactive or structural elements for navigation and screen-readers (buttons, links, inputs, headings). Skip decorative, redundant, or low-value items.
Return only valid JSON, no markdown fence, no explanation."""

USER_PROMPT_TEMPLATE = """Extract the structured elements from this page HTML.

URL: {url}

HTML (truncated):
{html}"""


class AnalysePageRequest(BaseModel):
    url: HttpUrl


def _strip_noise(html: str) -> str:
    """Remove script/style/svg/comments — keeps interactive elements, cuts ~70% of bloat."""
    # Remove block tags with content
    for tag in ("script", "style", "svg", "noscript"):
        html = re.sub(rf"<{tag}[\s>].*?</{tag}>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    # Remove HTML comments
    html = re.sub(r"<!--.*?-->", " ", html, flags=re.DOTALL)
    # Collapse whitespace
    html = re.sub(r"\s{2,}", " ", html)
    return html


def _trim_html(html: str, max_bytes: int = MAX_HTML_BYTES) -> str:
    """Strip noise then trim to max_bytes at a tag boundary."""
    html = _strip_noise(html)
    if len(html.encode("utf-8")) <= max_bytes:
        return html
    encoded = html.encode("utf-8")
    trimmed = encoded[:max_bytes].decode("utf-8", errors="ignore")
    last_gt = trimmed.rfind(">")
    if last_gt > max_bytes // 2:
        trimmed = trimmed[: last_gt + 1]
    return trimmed


async def _fetch_html(url: str) -> tuple[str, str]:
    """Async fetch URL, return (title_or_empty, trimmed_html). Optimized with shorter timeout."""
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; Spectra-Overlay/1.0; screen-reader analysis; +https://spectra.aqta.ai)",
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Encoding": "gzip, deflate",  # Enable compression
    }
    async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        html = resp.text
    title = ""
    m = re.search(r"<title[^>]*>([^<]*)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    return title, _trim_html(html)


def _gemini_sync(user_content: str) -> Any:
    """Blocking Gemini call — run via asyncio.to_thread. Supports both API key and Vertex AI."""
    from google import genai
    from google.genai import types

    api_key = os.environ.get("GOOGLE_API_KEY")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "europe-west1")

    if api_key:
        client = genai.Client(api_key=api_key)
    elif project:
        client = genai.Client(vertexai=True, project=project, location=location)
    else:
        raise ValueError("GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT must be set")

    return client.models.generate_content(
        model="gemini-2.5-flash",
        contents=user_content,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0,
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )


async def _call_gemini(html: str, url: str) -> dict[str, Any]:
    """Call Gemini in a thread with a hard timeout. Returns structured result dict."""
    if not os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT must be set for overlay analysis.",
        )

    user_content = USER_PROMPT_TEMPLATE.format(url=url, html=html)
    try:
        response = await asyncio.wait_for(
            asyncio.to_thread(_gemini_sync, user_content),
            timeout=20.0,  # Reduced from 30s for faster failure feedback
        )
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Gemini request timed out after 20s.")
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Gemini overlay request failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {str(e)}")

    text = (response.text or "").strip()
    # Strip optional markdown code fence
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    try:
        out = json.loads(text)
    except json.JSONDecodeError as e:
        logger.warning("Gemini returned invalid JSON: %s", e)
        raise HTTPException(status_code=502, detail="Gemini returned invalid JSON")
    if not isinstance(out, dict):
        raise HTTPException(status_code=502, detail="Gemini response was not a JSON object")
    if not isinstance(out.get("elements"), list):
        out["elements"] = []
    return {
        "url": url,
        "title": out.get("title") or "",
        "elements": out.get("elements") or [],
    }


async def _analyse_uncached(url: str) -> dict:
    """Fetch HTML and analyse with Gemini. Optimized with parallel preparation."""
    try:
        # Fetch HTML
        title_from_page, html = await _fetch_html(url)
    except httpx.HTTPError as e:
        logger.warning("Overlay fetch failed for %s: %s", url, e)
        raise HTTPException(status_code=400, detail=f"Could not fetch URL: {str(e)}")
    except Exception as e:
        logger.warning("Overlay fetch error for %s: %s", url, e)
        raise HTTPException(status_code=400, detail=f"Fetch error: {str(e)}")
    
    # Call Gemini with the fetched HTML
    result = await _call_gemini(html, url)
    
    # Use page title if Gemini didn't extract one
    if not result["title"] and title_from_page:
        result["title"] = title_from_page
    
    # Limit to top 50 elements for faster rendering
    if len(result.get("elements", [])) > 50:
        result["elements"] = result["elements"][:50]
    
    return result


@router.post("/analyse-page")
async def analyse_page(body: AnalysePageRequest):
    """
    Fetch page HTML, send to Gemini to extract structured elements for the Spectra Overlay.
    Results are cached 30 min; concurrent requests for the same URL share one Gemini call.
    """
    url = str(body.url)

    # Cache hit — return immediately, zero Gemini cost
    now = time.monotonic()
    cached = _cache.get(url)
    if cached and (now - cached[0]) < CACHE_TTL:
        logger.debug("Overlay cache hit: %s", url)
        return cached[1]

    # In-flight dedup — piggyback on an already-running task for this URL
    existing = _inflight.get(url)
    if existing and not existing.done():
        return await asyncio.shield(existing)

    task: asyncio.Task[dict] = asyncio.create_task(_analyse_uncached(url))
    _inflight[url] = task
    try:
        result = await asyncio.shield(task)
        _cache[url] = (time.monotonic(), result)
        return result
    finally:
        _inflight.pop(url, None)

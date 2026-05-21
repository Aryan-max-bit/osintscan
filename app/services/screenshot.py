"""
Optional screenshot capture for found profiles using Playwright.
Disabled when SCREENSHOTS_ENABLED=false in .env.
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from app.config import Config


def _safe_filename(site_name: str, username: str) -> str:
    """Build a filesystem-safe screenshot filename."""
    safe_site = re.sub(r"[^\w\-]", "_", site_name)[:40]
    safe_user = re.sub(r"[^\w\-]", "_", username)[:40]
    return f"{safe_user}_{safe_site}.png"


async def _capture_one(url: str, output_path: Path) -> bool:
    """Capture a single page screenshot (async Playwright)."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return False

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page(
                viewport={"width": 1280, "height": 720},
                user_agent=Config.USER_AGENT,
            )
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=Config.SCREENSHOT_TIMEOUT,
            )
            await page.screenshot(path=str(output_path), full_page=False)
            await browser.close()
        return True
    except Exception:
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        return False


async def capture_screenshots_async(
    username: str,
    results: list[dict[str, Any]],
    max_shots: int = 10,
) -> list[dict[str, Any]]:
    """
    Capture screenshots for found profiles (limited to max_shots for speed).
    Adds screenshot_path to each result dict when successful.
    """
    if not Config.SCREENSHOTS_ENABLED:
        return results

    os.makedirs(Config.SCREENSHOTS_DIR, exist_ok=True)
    found = [r for r in results if r.get("status") == "found"][:max_shots]

    async def process_one(r: dict) -> dict:
        path = Path(Config.SCREENSHOTS_DIR) / _safe_filename(
            r["site_name"], username
        )
        ok = await _capture_one(r["url"], path)
        if ok:
            r["screenshot_path"] = f"/screenshots/{path.name}"
        return r

    if found:
        await asyncio.gather(*[process_one(r) for r in found])

    return results


def capture_screenshots(
    username: str,
    results: list[dict[str, Any]],
    max_shots: int = 10,
) -> list[dict[str, Any]]:
    """Synchronous wrapper for screenshot capture."""
    return asyncio.run(
        capture_screenshots_async(username, results, max_shots)
    )

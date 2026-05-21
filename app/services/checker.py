"""
Async username checker — queries many sites concurrently via aiohttp.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import aiohttp

from app.config import Config


def load_sites() -> list[dict[str, Any]]:
    """Load platform definitions from sites.json."""
    path = Path(Config.SITES_JSON)
    if not path.exists():
        raise FileNotFoundError(f"Sites file not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("sites", [])


def _build_url(site: dict, username: str) -> str:
    """Replace {username} placeholder in URL template."""
    return site["url"].replace("{username}", username)


async def _check_one(
    session: aiohttp.ClientSession,
    site: dict,
    username: str,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    """
    Check a single site for the username.
    Detection modes: status_code, message (body text), url (redirect).
    """
    site_name = site["name"]
    url = _build_url(site, username)
    start = time.perf_counter()

    result = {
        "site_name": site_name,
        "url": url,
        "status": "not_found",
        "response_time_ms": 0,
        "error_message": None,
        "category": site.get("category", "other"),
    }

    async with semaphore:
        try:
            async with session.get(
                url,
                allow_redirects=True,
                ssl=False,
            ) as resp:
                elapsed_ms = (time.perf_counter() - start) * 1000
                result["response_time_ms"] = round(elapsed_ms, 2)
                body = await resp.text(errors="ignore")
                final_url = str(resp.url)

                detect = site.get("detect", "status_code")
                if detect == "status_code":
                    expected = site.get("exists_status", 200)
                    if resp.status == expected:
                        result["status"] = "found"
                    elif resp.status in site.get("not_found_status", [404]):
                        result["status"] = "not_found"
                    else:
                        # Ambiguous — treat as not found unless body hints exist
                        result["status"] = "not_found"

                elif detect == "message":
                    exists_msg = site.get("exists_msg", "")
                    not_exists_msg = site.get("not_exists_msg", "")
                    if exists_msg and exists_msg in body:
                        result["status"] = "found"
                    elif not_exists_msg and not_exists_msg in body:
                        result["status"] = "not_found"
                    elif resp.status == 200:
                        result["status"] = "found"
                    else:
                        result["status"] = "not_found"

                elif detect == "url":
                    # e.g. GitHub redirects invalid users
                    if site.get("exists_url_contains") and site["exists_url_contains"] in final_url:
                        result["status"] = "found"
                    elif site.get("not_exists_url_contains") and site["not_exists_url_contains"] in final_url:
                        result["status"] = "not_found"
                    elif resp.status == 200:
                        result["status"] = "found"
                    else:
                        result["status"] = "not_found"

        except asyncio.TimeoutError:
            result["status"] = "error"
            result["error_message"] = "Request timed out"
            result["response_time_ms"] = round(
                (time.perf_counter() - start) * 1000, 2
            )
        except aiohttp.ClientError as e:
            result["status"] = "error"
            result["error_message"] = str(e)[:200]
            result["response_time_ms"] = round(
                (time.perf_counter() - start) * 1000, 2
            )
        except Exception as e:
            result["status"] = "error"
            result["error_message"] = str(e)[:200]
            result["response_time_ms"] = round(
                (time.perf_counter() - start) * 1000, 2
            )

    return result


async def check_username_async(username: str) -> list[dict[str, Any]]:
    """
    Scan all configured sites for a username using concurrent async HTTP.
    Returns a list of result dicts sorted: found first, then by response time.
    """
    sites = load_sites()
    semaphore = asyncio.Semaphore(Config.MAX_CONCURRENT_REQUESTS)
    timeout = aiohttp.ClientTimeout(total=Config.REQUEST_TIMEOUT)
    headers = {"User-Agent": Config.USER_AGENT}

    connector = aiohttp.TCPConnector(limit=Config.MAX_CONCURRENT_REQUESTS)
    async with aiohttp.ClientSession(
        timeout=timeout,
        headers=headers,
        connector=connector,
    ) as session:
        tasks = [
            _check_one(session, site, username, semaphore)
            for site in sites
        ]
        results = await asyncio.gather(*tasks)

    # Sort: found profiles first, then fastest responses
    status_order = {"found": 0, "not_found": 1, "error": 2}
    results.sort(
        key=lambda r: (
            status_order.get(r["status"], 3),
            r.get("response_time_ms") or 9999,
        )
    )
    return results


def check_username(username: str) -> list[dict[str, Any]]:
    """
    Synchronous wrapper for Flask routes.
    Runs the async checker in a new event loop.
    """
    return asyncio.run(check_username_async(username))

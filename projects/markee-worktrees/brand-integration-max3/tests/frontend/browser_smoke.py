#!/usr/bin/env python3
"""Browser smoke and screenshots through the real FastAPI application."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8765"
OUT = Path("/tmp/markee-max3-brand-screenshots")
OUT.mkdir(parents=True, exist_ok=True)
ASSETS = (
    "/",
    "/static/styles.css",
    "/static/script.js",
    "/static/assets/brand-v2/logos/markee-wordmark-dark.svg",
    "/app/",
    "/app/styles.css",
    "/app/app.js",
    "/assets/brand-v2/logos/markee-wordmark-dark.svg",
)

results = {"http": {}, "pages": {}, "errors": []}
with sync_playwright() as playwright:
    request = playwright.request.new_context(base_url=BASE)
    for path in ASSETS:
        response = request.get(path)
        results["http"][path] = response.status
        if response.status != 200:
            results["errors"].append(f"HTTP {response.status}: {path}")

    browser = playwright.chromium.launch(headless=True)
    for name, path, viewport in (
        ("landing-desktop", "/", {"width": 1440, "height": 1000}),
        ("landing-mobile", "/", {"width": 390, "height": 844}),
        ("dashboard-login-desktop", "/app/#/login", {"width": 1440, "height": 1000}),
        ("dashboard-login-mobile", "/app/#/login", {"width": 390, "height": 844}),
    ):
        context = browser.new_context(viewport=viewport, reduced_motion="reduce")
        page = context.new_page()
        page_errors = []
        failed = []
        page.on("pageerror", lambda error, target=page_errors: target.append(str(error)))
        page.on(
            "requestfailed",
            lambda req, target=failed: target.append(
                f"{req.url}: {req.failure or 'request failed'}"
            ),
        )
        response = page.goto(BASE + path, wait_until="networkidle", timeout=60_000)
        page.wait_for_timeout(500)
        wordmark = page.locator(
            'img[src*="brand-v2/logos/markee-wordmark-dark.svg"]:visible'
        ).first
        wordmark.wait_for(state="visible", timeout=10_000)
        natural = wordmark.evaluate(
            "el => ({complete: el.complete, naturalWidth: el.naturalWidth, naturalHeight: el.naturalHeight})"
        )
        screenshot = OUT / f"{name}.png"
        page.screenshot(path=str(screenshot), full_page=name.startswith("landing"))
        results["pages"][name] = {
            "url": page.url,
            "status": response.status if response else None,
            "title": page.title(),
            "wordmark": natural,
            "page_errors": page_errors,
            "request_failures": [
                item
                for item in failed
                if urlparse(item.split(": ", 1)[0]).hostname == "127.0.0.1"
            ],
            "screenshot": str(screenshot),
        }
        if response is None or response.status != 200 or page_errors or not natural["naturalWidth"]:
            results["errors"].append(f"page failed: {name}")
        context.close()
    browser.close()

print(json.dumps(results, indent=2, ensure_ascii=False))
raise SystemExit(1 if results["errors"] else 0)

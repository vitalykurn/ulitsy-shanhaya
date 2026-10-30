# -*- coding: utf-8 -*-
"""Publish the static site through Netlify Drop and print the public URL."""

import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
ZIP_PATH = ROOT.parent / "ulitsy-shanhaya.zip"
SKIP_SUFFIXES = {".py", ".txt"}
SKIP_NAMES = {"credits.json", "check_build.py"}


def build_zip():
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in ROOT.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() in SKIP_SUFFIXES or path.name in SKIP_NAMES:
                continue
            if path.name.startswith("_"):
                continue
            archive.write(path, path.relative_to(ROOT).as_posix())
    print("zip", ZIP_PATH.stat().st_size)


def publish():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False, channel="chrome")
        page = browser.new_page()
        page.goto("https://app.netlify.com/drop", wait_until="domcontentloaded", timeout=60000)
        page.get_by_text("Drop here").wait_for(timeout=30000)
        inputs = page.locator("input")
        count = inputs.count()
        print("inputs", count)
        for index in range(count):
            item = inputs.nth(index)
            print(
                index,
                item.get_attribute("type"),
                item.get_attribute("name"),
                item.get_attribute("id"),
                item.get_attribute("accept"),
            )
        def on_response(response):
            if "api.netlify.com" in response.url or "netlify.app" in response.url:
                print("RESP", response.status, response.url[:180])

        page.on("response", on_response)
        page.locator("#drop-hero-file").set_input_files(str(ZIP_PATH), timeout=20000)
        print("uploaded, waiting")
        try:
            page.wait_for_url("**/*netlify.app**", timeout=120000)
        except Exception:
            page.wait_for_timeout(5000)
        print("PAGE", page.url)
        body = page.locator("body").inner_text(timeout=10000)
        print(body[:1500])
        browser.close()


if __name__ == "__main__":
    build_zip()
    publish()

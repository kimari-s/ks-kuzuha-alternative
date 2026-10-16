"""Browser check of a running bundle (UI + PHP API in one folder).

    python check.py http://localhost:8790/          # smoke: load, post, list
    python check.py http://localhost:8790/ --full   # + reply, delete, search, tag filter, settings, language
    python check.py http://localhost:8790/ --site-dir <served bbs/>   # + runtime config.json edit

Every run also checks the footer release, feature gating against a stubbed
/v1/meta, and that the board loads on a non-localhost plain-http origin
(a hostname mapped to the server with Chromium's host resolver rules:
not a secure context, so no crypto.randomUUID). With --site-dir (the folder
the server serves), config.json is edited in place and the new board name
must show without a rebuild; the file is restored afterwards.

--full posts several times in a row, so the server must run with
post_cooldown 0 (api/config.php). Any browser console error or failed
request fails the check. Needs playwright (Chromium).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from playwright.sync_api import Browser, Page, expect, sync_playwright

TIMEOUT_MS = 10_000
# A name that is not localhost: Chromium treats http:// on it as insecure.
INSECURE_HOST = "kska-smoke.test"
OPTIONAL = {"link_preview": "/v1/links/by-urls", "presence": "/v1/presence", "active_count": "/v1/active_count"}
UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def post_block(page: Page, text: str):
    """The post element whose body contains `text`."""
    return page.locator("div.m").filter(has=page.locator("pre.msgnormal", has_text=text))


def open_menu(page: Page, text: str):
    block = post_block(page, text).first
    block.locator("summary.post-menu").click()
    return block


def new_page(browser: Browser, errors: list[str], requests: list[str] | None = None, locale: str = "ja-JP") -> Page:
    """A page (in a fresh context: empty localStorage) whose console errors,
    failed requests and HTTP errors go to `errors`. `locale` is the
    browser's language (navigator.languages)."""
    page = browser.new_page(locale=locale)
    page.set_default_timeout(TIMEOUT_MS)
    page.on("console", lambda m: m.type == "error" and errors.append(f"console: {m.text}"))
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: errors.append(f"requestfailed: {r.url} {r.failure}"))
    page.on("response", lambda r: r.status >= 400 and errors.append(f"HTTP {r.status}: {r.url}"))
    page.on("dialog", lambda d: d.accept())
    if requests is not None:
        page.on("request", lambda r: requests.append(r.url))
    return page


def called(requests: list[str], path: str) -> bool:
    return any(urlsplit(u).path.endswith(path) for u in requests)


def step(name: str) -> None:
    print(f"  ok  {name}")


def run(base: str, full: bool, headed: bool, site_dir: Path | None) -> int:
    errors: list[str] = []
    tag = f"smoke-{uuid.uuid4().hex[:6]}"
    author = "テスト名無し"
    body = f"スモークテスト {uuid.uuid4().hex[:8]}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        page = new_page(browser, errors)

        # Load: the board renders and the API answers through ./api.
        page.goto(base)
        expect(page.locator("#contents1")).to_be_visible()
        expect(page.locator(".bbsstats")).to_contain_text("件")
        step("load board")

        # Post with a poster name and a tag: posting while the list is
        # narrowed to a tag attaches that tag (the UI has no tag field).
        page.goto(f"{base}#/?tags={tag}")
        page.locator("#name1").fill(author)
        page.locator("#contents1").fill(body)
        page.locator("input[name=post]").click()
        block = post_block(page, body)
        expect(block).to_have_count(1)
        expect(block.locator(".poster-link")).to_have_text(author)
        step("post (author + text + tag)")

        # The post is in the unfiltered list too.
        page.goto(base)
        expect(post_block(page, body)).to_have_count(1)
        step("post shown in list")

        if full:
            # Reply from the ■ menu.
            reply = f"返信 {uuid.uuid4().hex[:8]}"
            open_menu(page, body).get_by_role("link", name="レス").click()
            page.locator("#reply-body").fill(reply)
            page.locator("#reply-name").fill("返信者")
            page.locator(".inline-reply input[type=submit]").click()
            rblock = post_block(page, reply)
            expect(rblock).to_have_count(1)
            expect(rblock.locator(".q")).to_contain_text(f"> {body}")
            step("reply (quotes the parent)")

            # Delete own post (the reply).
            rblock = open_menu(page, reply)
            rblock.get_by_role("link", name="流す").click()
            expect(page.locator("pre.msgnormal", has_text="流されました").first).to_be_visible()
            page.reload()
            expect(post_block(page, reply)).to_have_count(0)
            step("delete own post")

            # Search by keyword.
            page.goto(f"{base}#/?mode=search")
            page.locator("#sq").fill(body.split()[1])
            page.locator(".searchform input[type=submit]").click()
            expect(post_block(page, body)).to_have_count(1)
            step("search")

            # Tag filter: show tags, click the post's tag chip.
            other = f"タグなし {uuid.uuid4().hex[:8]}"
            page.goto(base)
            page.locator("#contents1").fill(other)
            page.locator("input[name=post]").click()
            expect(post_block(page, other)).to_have_count(1)
            post_block(page, body).locator("a.tag-chip", has_text=tag).click()
            expect(page).to_have_url(f"{base}#/?tags={tag}")
            expect(post_block(page, body)).to_have_count(1)
            expect(post_block(page, other)).to_have_count(0)
            step("tag filter")

            # Settings page renders and a setting sticks.
            page.goto(f"{base}#/settings")
            box = page.get_by_label("タグを表示する")
            expect(box).to_be_visible()
            box.set_checked(not box.is_checked())
            page.goto(base)
            # .first: the deleted reply still lists, quoting this post.
            expect(post_block(page, body).first).to_be_visible()
            step("settings page")

            # Theme-coloured controls: off by default, on darkens the text
            # fields, and the choice survives a reload.
            html = page.locator("html")
            expect(html).to_have_attribute("data-controls", "standard")
            white = page.locator("#contents1").evaluate("e => getComputedStyle(e).backgroundColor")
            page.goto(f"{base}#/settings")
            controls = page.get_by_label("テーマの色で表示する")
            expect(controls).not_to_be_checked()
            controls.check()
            expect(html).to_have_attribute("data-controls", "custom")
            page.reload()
            expect(page.get_by_label("テーマの色で表示する")).to_be_checked()
            expect(html).to_have_attribute("data-controls", "custom")
            page.goto(base)
            expect(html).to_have_attribute("data-controls", "custom")
            dark = page.locator("#contents1").evaluate("e => getComputedStyle(e).backgroundColor")
            if dark == white or dark in ("rgb(255, 255, 255)", "rgba(0, 0, 0, 0)"):
                errors.append(f"theme.controls custom: post field background {dark!r} is not the theme colour")
            page.goto(f"{base}#/settings")
            page.get_by_label("テーマの色で表示する").uncheck()
            expect(html).to_have_attribute("data-controls", "standard")
            step(f"theme-coloured controls (custom: {dark}), kept after reload")

        # Footer: the release from bbs/config.json, About block: the API meta.
        page.goto(f"{base}#/settings")
        expect(page.locator(".copyright")).to_have_text(re.compile(r"^kimari-s/ks-kuzuha-alternative v\d+\.\d+\.\d+"))
        expect(page.locator(".about")).to_contain_text("protocol kssw")
        expect(page.locator(".about")).to_contain_text("profile min")
        step("footer release + About (/v1/meta)")

        check_features(browser, base, full, errors)
        if full:
            check_language(browser, base, errors)
        if site_dir is not None:
            check_runtime_config(page, base, site_dir)
        time.sleep(0.5)  # let trailing requests (presence) settle
        browser.close()

        check_plain_http(p, base, headed, errors)

    if errors:
        print("FAIL: browser errors:", *errors, sep="\n  ", file=sys.stderr)
        return 1
    print("OK")
    return 0


def settle(page: Page) -> None:
    """Let the first-load requests (meta, counts, presence ping) go out. The
    board polls, so the network never goes idle; wait a fixed time."""
    page.wait_for_timeout(2000)


def check_features(browser: Browser, base: str, full: bool, errors: list[str]) -> None:
    """Optional endpoints follow /v1/meta "features"; none listed = none called."""
    # Stubbed meta listing no optional feature.
    stub_reqs: list[str] = []
    page = new_page(browser, errors, stub_reqs)
    stub = {"protocol": "kssw", "version": "1", "profile": "min", "impl": "php", "impl_version": "0.0.0-smoke", "features": []}
    page.route("**/api/v1/meta", lambda route: route.fulfill(status=200, content_type="application/json", body=json.dumps(stub)))
    link_body = None
    if full:
        link_body = f"リンク https://example.com/{uuid.uuid4().hex[:8]}"
        page.goto(base)
        page.locator("#contents1").fill(link_body)
        page.locator("input[name=post]").click()
        expect(post_block(page, link_body)).to_have_count(1)
    stub_reqs.clear()
    page.goto(base)
    page.reload()
    expect(page.locator(".bbsstats")).to_contain_text("件")
    settle(page)
    expect(page.locator(".bbsstats")).not_to_contain_text("参加者")
    gated = [f for f in OPTIONAL if f != "link_preview" or full]
    hit = [OPTIONAL[f] for f in gated if called(stub_reqs, OPTIONAL[f])]
    if hit:
        errors.append(f"features []: still called {hit}")
    page.goto(f"{base}#/settings")
    expect(page.locator(".about")).to_contain_text("features -")
    page.close()
    step(f"features [] (stub): no {', '.join(gated)} calls, no participant count")

    # Real meta: a feature is called when listed, or when "features" is absent (older API).
    real_reqs: list[str] = []
    page = new_page(browser, errors, real_reqs)
    meta = page.request.get(base + "api/v1/meta").json()
    listed = meta.get("features")
    page.goto(base)
    expect(page.locator(".bbsstats")).to_contain_text("件")
    settle(page)
    for f in gated:
        want = listed is None or f in listed
        if called(real_reqs, OPTIONAL[f]) != want:
            errors.append(f"real meta features={listed}: {OPTIONAL[f]} called={not want}, expected {want}")
    page.close()
    step(f"features as served ({'absent: all assumed' if listed is None else listed})")


def expect_language(page: Page, lang: str) -> None:
    """<html lang> and the settings page's language label are `lang`."""
    expect(page.locator("html")).to_have_attribute("lang", lang)
    page.goto(page.url.split("#")[0] + "#/settings")
    expect(page.locator("label[for=st-locale]")).to_have_text({"en": "Language", "ja": "言語"}[lang])


def check_language(browser: Browser, base: str, errors: list[str]) -> None:
    """Locale order: ?lang=, saved choice, browser language (localeAuto),
    config locale. The bundle's config.json says "locale": "ja"."""
    def board(locale: str, query: str = "", config: dict | None = None) -> Page:
        page = new_page(browser, errors, locale=locale)
        if config is not None:
            cfg = {**page.request.get(base + "config.json").json(), **config}
            page.route("**/config.json", lambda r: r.fulfill(status=200, content_type="application/json", body=json.dumps(cfg)))
        page.goto(base + query)
        expect(page.locator(".bbsstats").first).to_be_visible()
        return page

    # ?lang=en on a ja board in a ja browser: English, gone from the URL, kept on reload.
    page = board("ja-JP", "?lang=en")
    expect(page.locator("html")).to_have_attribute("lang", "en")
    if "lang=" in page.url:
        errors.append(f"?lang=en left in the URL: {page.url}")
    page.reload()
    expect_language(page, "en")
    page.goto(base)
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.close()
    step("?lang=en: English, URL cleaned, kept after reload")

    # Together with the legacy ?tag=.
    page = board("ja-JP", "?lang=en&tag=smoke-lang")
    expect(page).to_have_url(f"{base}#/?tags=smoke-lang")
    expect_language(page, "en")
    page.close()
    step("?lang=en&tag=: English + tag filter")

    # Unknown ?lang= is ignored (left alone).
    page = board("ja-JP", "?lang=xx")
    expect_language(page, "ja")
    if "lang=xx" not in page.url:
        errors.append(f"?lang=xx was removed: {page.url}")
    page.close()
    step("?lang=xx ignored")

    # Browser language, no choice: en-US -> English, ja-JP -> Japanese.
    page = board("en-US")
    expect_language(page, "en")
    page.close()
    page = board("ja-JP")
    expect_language(page, "ja")
    page.close()
    step("browser language: en-US -> en, ja-JP -> ja")

    # A saved choice (here from ?lang=ja) beats the browser's language.
    page = board("en-US", "?lang=ja")
    page.goto(base)
    expect_language(page, "ja")
    page.close()
    step("saved choice beats browser language")

    # localeAuto false: config locale ja, whatever the browser.
    page = board("en-US", config={"localeAuto": False})
    expect_language(page, "ja")
    page.close()
    step("localeAuto false: config locale")

    # localeSwitch false: ?lang= holds for that load, not saved.
    page = board("ja-JP", "?lang=en", config={"localeSwitch": False, "localeAuto": False})
    expect(page.locator("html")).to_have_attribute("lang", "en")
    page.goto(base)
    page.reload()
    expect(page.locator("html")).to_have_attribute("lang", "ja")
    page.close()
    step("localeSwitch false: ?lang= not saved")


def check_runtime_config(page: Page, base: str, site_dir: Path) -> None:
    """Editing bbs/config.json changes the board without a rebuild."""
    path = site_dir / "config.json"
    original = path.read_text(encoding="utf-8")

    def put(text: str) -> None:
        # Write, then wait until the server serves it (a docker bind mount
        # can lag behind the host for a moment).
        path.write_text(text, encoding="utf-8")
        deadline = time.monotonic() + 10
        while page.request.get(base + "config.json", headers={"Cache-Control": "no-cache"}).text() != text:
            if time.monotonic() > deadline:
                raise RuntimeError("server does not serve the edited config.json")
            time.sleep(0.2)

    try:
        cfg = json.loads(original)
        name = f"スモーク板-{uuid.uuid4().hex[:6]}"
        cfg["network"] = name
        put(json.dumps(cfg, ensure_ascii=False))
        page.goto(base)
        page.reload()
        expect(page.locator(".pagetitle")).to_contain_text(name)
        expect(page).to_have_title(re.compile(re.escape(name)))
        step("config.json edit shows without rebuild")

        # The title is network＠mainTags; an empty network leaves ＠<tags>.
        board = f"スモーク-{uuid.uuid4().hex[:6]}"
        for network, want in ((name, f"{name}＠{board}"), ("", f"＠{board}")):
            cfg["network"] = network
            cfg["mainTags"] = [board]
            cfg["defaultTags"] = [board]
            put(json.dumps(cfg, ensure_ascii=False))
            page.reload()
            expect(page.locator(".pagetitle > a").first).to_have_text(want)
            expect(page).to_have_title(re.compile("^" + re.escape(want)))
            step(f"title network＠mainTags: {want}")

        # Broken JSON: the build-time config, the board still loads.
        put("{ broken")
        page.reload()
        expect(page.locator(".bbsstats")).to_contain_text("件")
        expect(page.locator(".pagetitle")).not_to_contain_text(name)
        step("broken config.json falls back")
    finally:
        path.write_text(original, encoding="utf-8")


def check_plain_http(p, base: str, headed: bool, errors: list[str]) -> None:
    """The board loads on http:// with a non-localhost name (no secure context)."""
    parts = urlsplit(base)
    insecure = urlunsplit(parts._replace(netloc=f"{INSECURE_HOST}:{parts.port}"))
    browser = p.chromium.launch(headless=not headed, args=[f"--host-resolver-rules=MAP {INSECURE_HOST} 127.0.0.1"])
    try:
        page = new_page(browser, errors)
        page.goto(insecure)
        expect(page.locator("#contents1")).to_be_visible()
        expect(page.locator(".bbsstats")).to_contain_text("件")
        if page.evaluate("window.isSecureContext"):
            errors.append(f"{insecure} is a secure context; the plain-http check proves nothing")
        if page.evaluate("typeof crypto.randomUUID") != "undefined":
            errors.append(f"{insecure}: crypto.randomUUID present; the fallback is not exercised")
        settle(page)
        cid = page.evaluate("localStorage.getItem('ks-kuzuha-alternative.client_id')")
        if cid is not None and not UUID4.match(cid):
            errors.append(f"client_id {cid!r} is not a UUID v4")
        step(f"plain http on {INSECURE_HOST} (no secure context, client_id {cid})")
    finally:
        browser.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("base", help="URL of the bundle folder, ending with /")
    ap.add_argument("--full", action="store_true", help="also reply, delete, search, tag filter, settings")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--site-dir", type=Path, help="the served bbs/ folder: also check a runtime config.json edit")
    a = ap.parse_args()
    base = a.base if a.base.endswith("/") else a.base + "/"
    return run(base, a.full, a.headed, a.site_dir)


if __name__ == "__main__":
    sys.exit(main())

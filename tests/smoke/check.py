"""Browser check of a running bundle (UI + PHP API in one folder).

    python check.py http://localhost:8790/          # smoke: load, post, list
    python check.py http://localhost:8790/ --full   # + reply, delete, search, tag filter, settings, language, view links
    python check.py http://localhost:8790/ --site-dir <served bbs/>   # + runtime config.json edit

Every run also checks the footer release, the About page (link row entry,
about.html filled from /v1/meta with each row linked to its source, in
Japanese and English; the settings page without About block, link row or
About link), feature gating against a stubbed /v1/meta, and that the
board loads on a non-localhost plain-http origin
(a hostname mapped to the server with Chromium's host resolver rules:
not a secure context, so no crypto.randomUUID). With --site-dir (the folder
the server serves): config.json (absent, as shipped) is created from
config.example.json and edited in place, and the new board name must show
without a rebuild; a broken or mistyped one must show a notice on the
settings page; the file is removed afterwards. Then api/.htaccess loses its
deny rules: the settings page must warn that private files are reachable
(and the board show its banner), and stop once it is restored. The admin
page's password setup form (no hash configured) must give a config line.
--shots DIR saves screenshots of those.

--full also checks the header's View menu (with screenshots, desktop and
phone, under --shots). --full posts several times in a row, so the server must run with
post_cooldown 0 (api/config.php). Any browser console error or failed
request fails the check, except the expected misses: config.json while
there is none, and the self-check's probes of private files (403 / 404).
Needs playwright (Chromium).
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
# ks-kuzuha-ui src/selfCheck.ts PRIVATE_PATHS, plus its random control path.
PRIVATE_PATHS = ["config.php", ".htaccess", "lib/app.php", "lib/schema.sql", "data/", "data/kssw.sqlite3"]
SHOTS: Path | None = None
UUID4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


def post_block(page: Page, text: str):
    """The post element whose body contains `text`."""
    return page.locator("div.m").filter(has=page.locator("pre.msgnormal", has_text=text))


def open_menu(page: Page, text: str):
    block = post_block(page, text).first
    block.locator("summary.post-menu").click()
    return block


def expected_miss(url: str, status: int | None = None) -> bool:
    """A 4xx the UI asks for on purpose: config.json while there is none
    (404), the security self-check's probes (403 / 404 when all is well)."""
    path = urlsplit(url).path
    if status not in (None, 403, 404):
        return False
    if path.endswith("/config.json"):
        return status in (None, 404)
    if "/api/" not in path:
        return False
    rel = path.split("/api/", 1)[1]
    return rel in PRIVATE_PATHS or rel.startswith("kssw-self-check-")


def console_error(m) -> str | None:
    if m.type != "error":
        return None
    # The browser's own line for an expected 4xx ("Failed to load resource").
    if m.text.startswith("Failed to load resource") and expected_miss(m.location.get("url", "")):
        return None
    return f"console: {m.text}"


def new_page(browser: Browser, errors: list[str], requests: list[str] | None = None, locale: str = "ja-JP") -> Page:
    """A page (in a fresh context: empty localStorage) whose console errors,
    failed requests and HTTP errors go to `errors`. `locale` is the
    browser's language (navigator.languages)."""
    page = browser.new_page(locale=locale)
    page.set_default_timeout(TIMEOUT_MS)
    page.on("console", lambda m: (e := console_error(m)) and errors.append(e))
    page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
    page.on("requestfailed", lambda r: errors.append(f"requestfailed: {r.url} {r.failure}"))
    page.on("response", lambda r: r.status >= 400 and not expected_miss(r.url, r.status) and errors.append(f"HTTP {r.status}: {r.url}"))
    page.on("dialog", lambda d: d.accept())
    if requests is not None:
        page.on("request", lambda r: requests.append(r.url))
    return page


def called(requests: list[str], path: str) -> bool:
    return any(urlsplit(u).path.endswith(path) for u in requests)


def step(name: str) -> None:
    print(f"  ok  {name}")


def shot(page: Page, name: str, locator=None) -> None:
    if SHOTS is None:
        return
    SHOTS.mkdir(parents=True, exist_ok=True)
    path = SHOTS / f"{name}.png"
    (locator or page).screenshot(path=str(path), **({} if locator else {"full_page": True}))
    print(f"      screenshot {path}")


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

        # Footer: the release from the build (the name without owner).
        page.goto(f"{base}#/settings")
        expect(page.locator(".copyright")).to_have_text(re.compile(r"^ks-kuzuha-alternative v\d+\.\d+\.\d+"))
        step("footer release")
        check_about(browser, base, errors)

        check_features(browser, base, full, errors)
        if full:
            check_language(browser, base, errors)
            check_view_links(browser, base, errors)
            check_view_menu(browser, base, errors)
        check_no_notices(page, base, "no config.json")
        check_admin_setup(browser, base, errors)
        if site_dir is not None:
            check_runtime_config(page, base, site_dir)
            check_security(browser, base, site_dir, errors)
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
    page.goto(f"{base}about.html")
    expect(page.locator("section[data-lang=ja] [data-meta=features]")).to_have_text("-")
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


def check_about(browser: Browser, base: str, errors: list[str]) -> None:
    """The link row's default entry (広報室 / About) opens about.html, which
    shows the release, the UI version and the API's /v1/meta in the board's
    language; the settings page has no About block, no link row and no link to it."""
    for lang, query, label, heading in (("ja", "", "広報室", "広報室"), ("en", "?lang=en", "About", "About")):
        page = new_page(browser, errors)
        meta = page.request.get(base + "api/v1/meta").json()
        page.goto(f"{base}{query}#/")
        link = page.locator(".link_row").get_by_role("link", name=label, exact=True)
        expect(link).to_have_attribute("href", "about.html")
        link.click()
        page.wait_for_url("**/about.html")
        sec = page.locator(f"section[data-lang={lang}]")
        expect(sec.locator("h1")).to_have_text(heading)
        expect(page.locator(f"section:not([data-lang={lang}])")).to_be_hidden()
        expect(page.locator("html")).to_have_attribute("lang", lang)
        expect(sec.locator("[data-meta=impl_version]")).to_have_text(meta["impl_version"])
        expect(sec.locator("[data-meta=protocol]")).to_have_text("kssw")
        expect(sec.locator('[data-k="release"]')).to_have_text(re.compile(r"^ks-kuzuha-alternative v\d+\.\d+\.\d+"))
        # Each row links to its source: release.url, the UI's repository, impl_url.
        expect(sec.locator('[data-k="release"] a')).to_have_attribute("href", "https://github.com/kimari-s/ks-kuzuha-alternative")
        expect(sec.locator('a[data-k="ui-repo"]')).to_have_attribute("href", re.compile(r"^https://github\.com/kimari-s/ks-kuzuha-ui"))
        api_name = sec.locator('[data-k="api-name"]')
        expect(api_name).to_have_text(f"{meta['impl']} {meta['impl_version']}")
        if meta.get("impl_url"):
            expect(api_name.locator("a")).to_have_attribute("href", meta["impl_url"])
        expect(sec.locator(".ui-version")).to_have_text(re.compile(r"^\d+\.\d+\.\d+"))
        page.goto(f"{base}#/settings")
        expect(page.locator(".settings-form")).to_have_count(1)
        expect(page.locator(".about")).to_have_count(0)
        # Settings shows only settings: no link row, no About link.
        expect(page.locator(".link_row")).to_have_count(0)
        expect(page.locator(f'main a[href$="about.html"]')).to_have_count(0)
        page.close()
        step(f"{lang}: link row {label} -> about.html (impl_version {meta['impl_version']}); settings without link row or About link")


def expect_language(page: Page, lang: str) -> None:
    """<html lang> and the settings page's language label are `lang`."""
    expect(page.locator("html")).to_have_attribute("lang", lang)
    page.goto(page.url.split("#")[0] + "#/settings")
    expect(page.locator("label[for=st-locale]")).to_have_text({"en": "Language", "ja": "言語"}[lang])


def check_language(browser: Browser, base: str, errors: list[str]) -> None:
    """Locale order: ?lang=, saved choice, browser language (localeAuto),
    config locale. The bundle's build-time config says "locale": "ja"."""
    def board(locale: str, query: str = "", config: dict | None = None) -> Page:
        page = new_page(browser, errors, locale=locale)
        if config is not None:
            cfg = dict(config)  # over the build-time config (the zip has no config.json)
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


def check_view_links(browser: Browser, base: str, errors: list[str]) -> None:
    """Search / settings: the header item of the shown view is the accent,
    underlined and aria-current, and a toggle: a focusable link that does
    what "« Back" does, returning to the board view it came from (with its
    filter), or #/ when the view was opened directly. In search mode the
    header has no Post item (Back covers it). A tag filter leads the heading
    (#tag, then the board name, smaller); the settings page does not repeat
    its name after the title."""
    accent = "e => { const p = document.createElement('i'); p.style.color = 'var(--accent)'; " \
        "e.append(p); const c = getComputedStyle(p).color; p.remove(); return c; }"
    for lang, query, search, settings, back, post, hint in (
        ("ja", "", "検索", "設定", "« 戻る", "投稿", "{}（戻る）"),
        ("en", "?lang=en", "Search", "Settings", "« Back", "Post", "{} (back)"),
    ):
        page = new_page(browser, errors)
        page.goto(f"{base}{query}#/?tags=smoke-view")
        title = page.locator(".pagetitle")
        expect(title.locator(":scope > *").first).to_have_text("#smoke-view")
        expect(title.locator("a.board-name")).to_be_visible()
        sizes = title.evaluate("e => [getComputedStyle(e.querySelector('.title-tag')).fontSize, "
                               "getComputedStyle(e.querySelector('.board-name')).fontSize]")
        if float(sizes[1].rstrip("px")) >= float(sizes[0].rstrip("px")):
            errors.append(f"{lang} tag heading: board name {sizes[1]} not smaller than the tag {sizes[0]}")
        expect(page).to_have_title(re.compile(r"^#smoke-view - "))
        header = page.locator(".link_upper")
        want = header.evaluate(accent)

        def current(label: str):
            cur = header.locator("[aria-current=page]")
            expect(cur).to_have_text(label)
            expect(cur).to_have_attribute("title", hint.format(label))
            expect(header.get_by_role("link", name=hint.format(label), exact=True)).to_have_count(1)
            state = cur.evaluate("e => [e.tagName, e.tabIndex, getComputedStyle(e).color, getComputedStyle(e).textDecorationLine]")
            if state[0] != "A" or state[1] < 0 or state[2] != want or "underline" not in state[3]:
                errors.append(f"{lang} current {label} item {state}, accent {want}")
            return cur

        # Search: the current item clicked goes back to the filtered board.
        header.get_by_role("link", name=search, exact=True).click()
        expect(page).to_have_url(re.compile(r"mode=search"))
        expect(header.get_by_role("link", name=post, exact=True)).to_have_count(0)
        cur = current(search)
        cur.hover()
        hovered = cur.evaluate("e => getComputedStyle(e).color")
        if hovered != want:
            errors.append(f"{lang} current search item hovered {hovered}, accent {want}")
        cur.click()
        expect(page).to_have_url(f"{base}#/?tags=smoke-view")
        # ... and by keyboard.
        header.get_by_role("link", name=search, exact=True).click()
        current(search).focus()
        page.keyboard.press("Enter")
        expect(page).to_have_url(f"{base}#/?tags=smoke-view")
        # "« Back" does the same.
        header.get_by_role("link", name=search, exact=True).click()
        page.locator(".back-link").get_by_role("link", name=back, exact=True).click()
        expect(page).to_have_url(f"{base}#/?tags=smoke-view")
        # Settings: the same toggle.
        header.get_by_role("link", name=settings, exact=True).click()
        expect(title).not_to_contain_text(settings)
        current(settings).click()
        expect(page).to_have_url(f"{base}#/?tags=smoke-view")
        header.get_by_role("link", name=settings, exact=True).click()
        page.locator(".back-link").get_by_role("link", name=back, exact=True).click()
        expect(page).to_have_url(f"{base}#/?tags=smoke-view")
        # Opened directly (a fresh load): Back and the current item go to the board's default view.
        for view, label in (("#/settings", settings), ("#/?mode=search&tags=smoke-view", search)):
            for how in ("back", "current"):
                page.goto(f"{base}{view}")
                page.reload()
                if how == "back":
                    page.locator(".back-link").get_by_role("link", name=back, exact=True).click()
                else:
                    current(label).click()
                expect(page).to_have_url(f"{base}#/")
        page.close()
        step(f"{lang}: #tag heading; no {post} in search mode; search / settings current item "
             f"(accent + underline, a link like {back}) to the filtered board or #/")


def check_view_menu(browser: Browser, base: str, errors: list[str]) -> None:
    """The header's "View" drop-down (the ■ menu's look): Standard and
    Tree; the view being shown is greyed out and not a link; picking the
    other switches and keeps ?tags=; Escape and a click outside close it."""
    for lang, query, view, standard, tree in (
        ("ja", "", "表示", "標準", "ツリー"),
        ("en", "?lang=en", "View", "Standard", "Tree"),
    ):
        for device, size in (("desktop", {"width": 1280, "height": 720}), ("phone", {"width": 390, "height": 844})):
            if lang == "en" and device == "phone":
                continue
            page = new_page(browser, errors)
            page.set_viewport_size(size)
            page.goto(f"{base}{query}#/?tags=smoke-view")
            menu = page.locator(".link_upper details.view-menu")
            summary = menu.locator("summary")
            expect(summary).to_have_text(view)
            items = menu.locator(".post-menu-items")
            expect(items).to_be_hidden()
            summary.click()
            expect(items).to_be_visible()
            off = items.locator(".menu-off")
            expect(off).to_have_text(standard)
            expect(off).to_have_attribute("aria-disabled", "true")
            if items.get_by_role("link", name=standard, exact=True).count() != 0:
                errors.append(f"{lang} view menu: the current view is a link")
            colors = page.evaluate("""() => {
                const off = document.querySelector('.view-menu .menu-off');
                const on = document.querySelector('.view-menu .post-menu-items a');
                return [getComputedStyle(off).color, getComputedStyle(on).color];
            }""")
            if colors[0] == colors[1]:
                errors.append(f"{lang} view menu: current view not dimmed ({colors})")
            shot(page, f"view-menu-{lang}-{device}")
            off.click()
            expect(page).to_have_url(f"{base}#/?tags=smoke-view")
            # Escape closes, focus back on the summary.
            page.keyboard.press("Escape")
            expect(items).to_be_hidden()
            # Keyboard: open with Enter on the summary, pick Tree.
            summary.focus()
            page.keyboard.press("Enter")
            expect(items).to_be_visible()
            items.get_by_role("link", name=tree, exact=True).click()
            expect(page).to_have_url(f"{base}#/tree?tags=smoke-view")
            expect(items).to_be_hidden()
            summary.click()
            expect(items.locator(".menu-off")).to_have_text(tree)
            # A click outside closes it (once the menu's listener is up,
            # after the open has rendered).
            page.wait_for_timeout(200)
            page.evaluate("document.body.dispatchEvent(new MouseEvent('mousedown', {bubbles: true}))")
            expect(items).to_be_hidden()
            summary.click()
            items.get_by_role("link", name=standard, exact=True).click()
            expect(page).to_have_url(f"{base}#/?tags=smoke-view")
            page.close()
        step(f"{lang}: header {view} menu: current view greyed out, {standard} / {tree} switch keeping ?tags=, Escape / click outside close")


def wait_served(page: Page, url: str, want, what: str) -> None:
    """Until url answers as want(response) (a docker bind mount can lag
    behind the host for a moment)."""
    deadline = time.monotonic() + 10
    while not want(page.request.get(url, headers={"Cache-Control": "no-cache"}, max_redirects=0)):
        if time.monotonic() > deadline:
            raise RuntimeError(f"server does not serve {what}")
        time.sleep(0.2)


def settings_notices(page: Page, base: str):
    """The settings page, once its self-check has had time to answer."""
    page.goto(f"{base}#/settings")
    page.reload()
    expect(page.locator(".settings-form")).to_be_visible()
    page.wait_for_timeout(1500)
    return page.locator("[data-notice=config]"), page.locator("[data-notice=selfcheck]")


def check_no_notices(page: Page, base: str, what: str) -> None:
    config, selfcheck = settings_notices(page, base)
    expect(config).to_have_count(0)
    expect(selfcheck).to_have_count(0)
    page.goto(base)
    expect(page.locator(".bbsstats")).to_contain_text("件")
    expect(page.locator(".selfcheck-banner")).to_have_count(0)
    step(f"{what}: board works, no notice on the settings page")


def check_runtime_config(page: Page, base: str, site_dir: Path) -> None:
    """bbs/config.json, absent as shipped, is created from
    config.example.json; edits change the board without a rebuild; a
    broken or mistyped file shows a notice on the settings page."""
    path = site_dir / "config.json"
    if path.exists():
        raise RuntimeError(f"{path} exists before the check: the zip must not ship it")
    example = (site_dir / "config.example.json").read_text(encoding="utf-8")

    def put(text: str) -> None:
        path.write_text(text, encoding="utf-8")
        wait_served(page, base + "config.json", lambda r: r.ok and r.text() == text, "the edited config.json")

    try:
        put(example)
        check_no_notices(page, base, "config.json copied from config.example.json")

        cfg = json.loads(example)
        name = f"スモーク板-{uuid.uuid4().hex[:6]}"
        cfg["network"] = name
        put(json.dumps(cfg, ensure_ascii=False))
        page.goto(base)
        page.reload()
        expect(page.locator(".pagetitle")).to_contain_text(name)
        expect(page).to_have_title(re.compile(re.escape(name)))
        step("config.json edit shows without rebuild")

        # The title is network＠boardTags; an empty network leaves ＠<tags>.
        board = f"スモーク-{uuid.uuid4().hex[:6]}"
        for network, want in ((name, f"{name}＠{board}"), ("", f"＠{board}")):
            cfg["network"] = network
            cfg["boardTags"] = [board]
            put(json.dumps(cfg, ensure_ascii=False))
            page.reload()
            expect(page.locator(".pagetitle > a").first).to_have_text(want)
            expect(page).to_have_title(re.compile("^" + re.escape(want)))
            step(f"title network＠boardTags: {want}")

        # A wrong type: that key is dropped (the rest applies) and named.
        put(json.dumps({"network": name, "boardTags": "x", "showTagz": True}, ensure_ascii=False))
        page.goto(base)
        page.reload()
        expect(page.locator(".pagetitle")).to_contain_text(name)
        notice, _ = settings_notices(page, base)
        expect(notice).to_be_visible()
        expect(notice).to_contain_text("config.json")
        expect(notice).to_contain_text("「boardTags」は array")
        expect(notice).to_contain_text("showTagz")
        step("wrong type in config.json: key dropped, settings notice names it")

        # Broken JSON: the build-time config, the board still loads, and the
        # settings page says where the file broke.
        put('{\n  "network": "x",\n  broken\n}')
        page.goto(base)
        page.reload()
        expect(page.locator(".bbsstats")).to_contain_text("件")
        expect(page.locator(".pagetitle")).not_to_contain_text(name)
        notice, _ = settings_notices(page, base)
        expect(notice).to_be_visible()
        expect(notice).to_contain_text("JSON")
        expect(notice).to_contain_text("3 行目")
        shot(page, "settings-config-notice", notice)
        step("broken config.json falls back; settings notice with line and column")
    finally:
        path.unlink(missing_ok=True)
    wait_served(page, base + "config.json", lambda r: r.status == 404, "a 404 for the removed config.json")
    check_no_notices(page, base, "config.json removed again")


def check_security(browser: Browser, base: str, site_dir: Path, errors: list[str]) -> None:
    """api/.htaccess without its deny rules (as if not in effect): the
    settings page warns, the board shows the banner for the session; with
    the shipped .htaccess back, neither."""
    ht = site_dir / "api" / ".htaccess"
    original = ht.read_text(encoding="utf-8")
    keep, skip = [], False
    for line in original.splitlines():
        if line.startswith("<FilesMatch"):
            skip = True
        if not skip and not line.startswith("Options -Indexes") and "(lib|data)" not in line:
            keep.append(line)
        if line.startswith("</FilesMatch>"):
            skip = False
    stripped = "\n".join(keep) + "\n"
    db = base + "api/data/kssw.sqlite3"
    page = new_page(browser, errors)
    try:
        ht.write_text(stripped, encoding="utf-8")
        wait_served(page, db, lambda r: r.status in (200, 206), "the database with the stripped .htaccess")
        _, warn = settings_notices(page, base)
        expect(warn).to_be_visible()
        expect(warn).to_contain_text("data/kssw.sqlite3")
        expect(warn).to_contain_text(".htaccess")
        shot(page, "settings-security-warning")
        page.goto(base)
        banner = page.locator(".selfcheck-banner")
        expect(banner).to_be_visible()
        shot(page, "board-security-banner", page.locator("header + .selfcheck-banner"))
        banner.locator("a").click()
        expect(page).to_have_url(f"{base}#/settings")
        expect(page.locator("[data-notice=selfcheck]")).to_be_visible()
        step("api/.htaccess not in effect: settings warning, board banner")
    finally:
        ht.write_text(original, encoding="utf-8")
    wait_served(page, db, lambda r: r.status in (403, 404), "a 403 for the database again")
    _, warn = settings_notices(page, base)
    expect(warn).to_have_count(0)
    page.goto(base)
    expect(page.locator(".bbsstats")).to_contain_text("件")
    expect(page.locator(".selfcheck-banner")).to_have_count(0)
    page.close()
    step("api/.htaccess back: no warning, no banner")


def check_admin_setup(browser: Browser, base: str, errors: list[str]) -> None:
    """admin.php without admin_password_hash: the setup form makes the
    config.php line (the smoke config has no hash; admin_allow_http)."""
    page = new_page(browser, errors)
    page.goto(base + "api/admin.php")
    expect(page.locator("h1")).to_have_text("Set up the admin password")
    pw = f"smoke password {uuid.uuid4().hex[:8]}"
    page.locator("input[name=password]").fill(pw)
    page.locator("input[name=password2]").fill(pw)
    shot(page, "admin-setup-form")
    page.get_by_role("button", name="Make the config.php line").click()
    line = page.locator("textarea")
    expect(line).to_have_value(re.compile(r"^'admin_password_hash' => '\$2y\$\d\d\$[./A-Za-z0-9]{53}',$"))
    if pw in page.content():
        errors.append("admin setup: the page shows the password")
    shot(page, "admin-setup-result")
    page.close()
    step("admin.php setup form: config.php line computed")


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
    ap.add_argument("--site-dir", type=Path, help="the served bbs/ folder: also check config.json and the .htaccess warning")
    ap.add_argument("--shots", type=Path, help="save screenshots here")
    a = ap.parse_args()
    global SHOTS
    SHOTS = a.shots
    base = a.base if a.base.endswith("/") else a.base + "/"
    return run(base, a.full, a.headed, a.site_dir)


if __name__ == "__main__":
    sys.exit(main())

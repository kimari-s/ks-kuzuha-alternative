"""Smoke test of a built zip: extract it, serve bbs/ with Apache + PHP 7.4
in docker (tests/smoke/Dockerfile), and run check.py against it.

    python tests/smoke/run.py build/ks-kuzuha-alternative-0.2.0-alpha.1.zip [--full]

The zip's .sha256 next to it is verified first. The site is served at
http://localhost:<port>/bbs/ (a secure context, like HTTPS); check.py also
opens it under a non-localhost name over plain http, creates, edits and
removes bbs/config.json to check the runtime config (the zip ships only
bbs/config.example.json), and edits api/.htaccess to check the settings
page's security warning. Then the admin CLI shipped in
tools/ (outside bbs/): a token made with `kssw-admin token new` is put
into api/config.php (with admin_allow_http, as the test is plain http), and
`capabilities`, `posts list` and `posts delete --dry-run` must work against
the container. --full also sets post_cooldown 0 and runs every check.
Needs docker and playwright (Chromium).

Each run extracts into a new folder (.scratch/smoke/run-<time>/): Docker
Desktop (macOS) can show a bind mount of a folder that was deleted and
re-created at the same path as empty, so a run right after another served
nothing (404) until the file sharing caught up.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
IMAGE = "ks-kuzuha-alternative-smoke"


def sh(*cmd: str, check: bool = True) -> subprocess.CompletedProcess:
    print("[smoke] $ " + " ".join(cmd), file=sys.stderr, flush=True)
    return subprocess.run(cmd, check=check)


def verify_sha(zip_path: Path) -> None:
    sha_file = zip_path.with_name(zip_path.name + ".sha256")
    want = sha_file.read_text(encoding="ascii").split()[0]
    got = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    if want != got:
        sys.exit(f"SHA-256 mismatch: {sha_file} says {want}, zip is {got}")
    print(f"[smoke] sha256 ok {got}", file=sys.stderr)


def wait_for(url: str, seconds: float = 60) -> dict:
    """GET url until it answers 200 with a JSON object. Anything else
    (connection refused, any 4xx / 5xx, not JSON) is retried while the
    server starts; at the deadline the last answer is reported."""
    deadline = time.monotonic() + seconds
    last = "no answer"
    while True:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                body = r.read()
            doc = json.loads(body)
            if isinstance(doc, dict):
                return doc
            last = f"200 but not a JSON object: {body[:200]!r}"
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read()[:200]!r}"
        except Exception as e:  # not up yet, or not JSON
            last = repr(e)
        if time.monotonic() > deadline:
            sys.exit(f"{url} not ready after {seconds:.0f} s: {last}")
        time.sleep(0.5)


def wait_mounted(name: str, path: str, seconds: float = 30) -> None:
    """The container sees the bundle at path (the bind mount is not empty)."""
    deadline = time.monotonic() + seconds
    while True:
        p = subprocess.run(["docker", "exec", name, "test", "-f", path], capture_output=True)
        if p.returncode == 0:
            return
        if time.monotonic() > deadline:
            sys.exit(f"container {name} does not see {path}: the bind mount looks empty (docker file sharing)")
        time.sleep(0.5)


def check_cli_shipped(zip_path: Path, cli: Path) -> None:
    """tools/kssw-admin is in the zip, outside bbs/, executable, with its README."""
    if not cli.is_file() or not (cli.parent / "README.txt").is_file():
        sys.exit("bundle lacks tools/kssw-admin or tools/README.txt")
    with zipfile.ZipFile(zip_path) as z:
        info = next(i for i in z.infolist() if i.filename.endswith("/tools/kssw-admin"))
        mode = info.external_attr >> 16 & 0o777
        if mode != 0o755:
            sys.exit(f"tools/kssw-admin has mode {mode:o} in the zip, want 755")
    if not cli.read_text(encoding="utf-8").startswith("#!/usr/bin/env python3"):
        sys.exit("tools/kssw-admin: no python3 shebang")
    print("[smoke] tools/kssw-admin shipped (0755, outside bbs/)", file=sys.stderr)


def kssw_admin(cli: Path, args: list[str], url: str | None = None, token: str | None = None) -> tuple[int, dict | None, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("KSSW_")}
    if url:
        env["KSSW_URL"] = url
    if token:
        env["KSSW_ADMIN_TOKEN"] = token
    p = subprocess.run([sys.executable, str(cli), *args], capture_output=True, text=True, env=env, timeout=60)
    if token and args[0] != "token" and (token in p.stdout or token in p.stderr):
        sys.exit("kssw-admin printed the token")
    try:
        doc = json.loads(p.stdout) if p.stdout.strip() else None
    except ValueError:
        doc = None
    return p.returncode, doc, p.stderr


def admin_token(cli: Path) -> dict:
    code, doc, err = kssw_admin(cli, ["token", "new"])
    if code != 0 or not doc or not doc.get("config_line", "").startswith("'admin_token_sha256' => '"):
        sys.exit(f"kssw-admin token new failed: {code} {err}")
    return doc


def check_admin_cli(cli: Path, api: str, token: str) -> None:
    meta = wait_for(api + "/v1/meta")
    if "admin" not in meta.get("features", []):
        sys.exit(f"/v1/meta does not list admin with a token configured: {meta}")
    code, doc, err = kssw_admin(cli, ["capabilities"], api, token)
    if code != 0 or not doc or "deletePosts" not in doc.get("operations", []):
        sys.exit(f"kssw-admin capabilities: exit {code} {doc} {err}")
    print(f"[smoke] kssw-admin capabilities: {doc['impl']} {doc['impl_version']} {doc['features']}", file=sys.stderr)
    code, _, err = kssw_admin(cli, ["capabilities"], api, "wrong-token")
    if code != 2 or '"unauthorized"' not in err:
        sys.exit(f"kssw-admin with a wrong token: exit {code} {err}")
    code, doc, err = kssw_admin(cli, ["posts", "list", "--status", "active", "--page-size", "1"], api, token)
    if code != 0 or not doc or not doc["items"]:
        sys.exit(f"kssw-admin posts list: exit {code} {doc} {err} (the browser check should have posted)")
    post = doc["items"][0]
    code, doc, err = kssw_admin(cli, ["posts", "delete", "--dry-run", post["id"]], api, token)
    if code != 0 or not doc or doc["dry_run"] is not True or doc["results"][0]["result"] != "changed":
        sys.exit(f"kssw-admin posts delete --dry-run: exit {code} {doc} {err}")
    with urllib.request.urlopen(f"{api}/v1/posts/{post['id']}", timeout=10) as r:
        if json.load(r)["status"] != "active":
            sys.exit("posts delete --dry-run deleted the post")
    print(f"[smoke] kssw-admin posts delete --dry-run ok ({post['id']} still active)", file=sys.stderr)


def check_discovery(origin: str) -> None:
    """GET /.well-known/kssw (the shipped static file) is JSON and its API
    base leads to this board's /v1/meta."""
    with urllib.request.urlopen(origin + "/.well-known/kssw", timeout=10) as r:
        ctype = r.headers.get("Content-Type", "")
        doc = json.load(r)
    if not ctype.startswith("application/json"):
        sys.exit(f"/.well-known/kssw: Content-Type {ctype!r}, want application/json")
    if doc.get("protocol") != "kssw" or not doc.get("apis"):
        sys.exit(f"/.well-known/kssw: unexpected {doc}")
    api = doc["apis"][0]
    base = urllib.parse.urljoin(origin + "/.well-known/kssw", api["base"]).rstrip("/")
    meta = wait_for(base + "/v1/meta")
    if api.get("version") != "1" or meta.get("protocol") != "kssw":
        sys.exit(f"/.well-known/kssw entry {api} does not lead to a kssw 1 API ({meta})")
    print(f"[smoke] /.well-known/kssw -> {base}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("zip")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--port", type=int, default=int(os.environ.get("SMOKE_PORT", "8791")))
    ap.add_argument("--keep", action="store_true", help="leave the container running")
    ap.add_argument("--shots", default=os.environ.get("SMOKE_SHOTS"), help="save screenshots of the warnings and the admin setup here")
    a = ap.parse_args()

    zip_path = Path(a.zip).resolve()
    verify_sha(zip_path)

    # Earlier runs' folders go; the parent stays (see the module docstring).
    smoke_dir = ROOT / ".scratch" / "smoke"
    smoke_dir.mkdir(parents=True, exist_ok=True)
    for old in smoke_dir.iterdir():
        if old.is_dir():
            shutil.rmtree(old)
        else:
            old.unlink()
    work = smoke_dir / f"run-{time.time_ns()}"
    work.mkdir()
    with zipfile.ZipFile(zip_path) as z:
        tops = {n.split("/", 1)[0] for n in z.namelist()}
        if len(tops) != 1:
            sys.exit(f"zip must have one top folder, has {sorted(tops)}")
        z.extractall(work)
    top = work / tops.pop()
    site = top / "bbs"
    for must in ["index.html", "config.example.json", "api/index.php", "api/.htaccess", "api/config.example.php"]:
        if not (site / must).is_file():
            sys.exit(f"bundle lacks bbs/{must}")
    # Settings are the operator's: an upload over the old folder keeps them.
    for never in ["config.json", "api/config.php"]:
        if (site / never).exists():
            sys.exit(f"bundle ships bbs/{never}; it must ship only the example")
    cli = top / "tools" / "kssw-admin"
    check_cli_shipped(zip_path, cli)

    # What a mod_php host needs: a data/ the web server user can write
    # (the container runs Apache as www-data, the files belong to us).
    (site / "api" / "data").mkdir()
    os.chmod(site / "api" / "data", 0o777)
    token = admin_token(cli)
    (site / "api" / "config.php").write_text(
        "<?php\nreturn [\n    " + token["config_line"] + "\n    'admin_allow_http' => true,\n"
        + ("    'post_cooldown' => 0,\n" if a.full else "") + "];\n",
        encoding="utf-8",
    )

    # The optional discovery document, placed as README.txt says (the
    # static file and its .htaccess in <document root>/.well-known/).
    well_known = top / "well-known"
    for must in ["kssw", ".htaccess"]:
        if not (well_known / must).is_file():
            sys.exit(f"bundle lacks well-known/{must}")

    sh("docker", "build", "-q", "-t", IMAGE, str(HERE))
    name = f"kska-smoke-{a.port}"
    subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    sh("docker", "run", "-d", "--rm", "--name", name, "-p", f"127.0.0.1:{a.port}:80",
       "-v", f"{site}:/var/www/html/bbs", "-v", f"{well_known}:/var/www/html/.well-known", IMAGE)
    try:
        wait_mounted(name, "/var/www/html/bbs/api/index.php")
        wait_mounted(name, "/var/www/html/.well-known/kssw")
        base = f"http://localhost:{a.port}/bbs/"
        meta = wait_for(base + "api/v1/meta")
        print(f"[smoke] meta {meta}", file=sys.stderr)
        if meta.get("protocol") != "kssw" or meta.get("version") != "1" or meta.get("profile") != "min":
            sys.exit(f"unexpected /v1/meta: {meta}")
        check_discovery(f"http://localhost:{a.port}")
        # Private files stay private behind .htaccess.
        for path in ["api/config.example.php", "api/lib/schema.sql", "api/lib/app.php", "api/data/kssw.sqlite3"]:
            try:
                urllib.request.urlopen(base + path, timeout=5)
                sys.exit(f"{path} is served; .htaccess not effective")
            except urllib.error.HTTPError as e:
                if e.code not in (403, 404):
                    sys.exit(f"{path}: HTTP {e.code}")
        cmd = [sys.executable, str(HERE / "check.py"), base, "--site-dir", str(site)] + (["--full"] if a.full else []) \
            + (["--shots", a.shots] if a.shots else [])
        code = subprocess.run(cmd).returncode
        if code != 0:
            return code
        # After the browser check, which has posted (the CLI must not get in
        # the way of its post cooldown).
        check_admin_cli(cli, base + "api", token["token"])
        return 0
    finally:
        if not a.keep:
            subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL)


if __name__ == "__main__":
    sys.exit(main())

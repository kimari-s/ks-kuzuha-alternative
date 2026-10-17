#!/usr/bin/env python3
"""Build the ks-kuzuha-alternative zip from a manifest.

    python3 dist/build.py                                  # dist/php-min.toml, URLs from the manifest
    python3 dist/build.py --src ks-sw-api=../ks-sw-api     # clone from a local repo (pinned commit)
    python3 dist/build.py --worktree ks-kuzuha-ui=../ks-kuzuha-ui  # use a directory as it is (dev only)
    python3 dist/build.py --site-config config/demo.json --suffix demo

Steps: fetch every component at its pinned commit into build/src/, build the
UI with the manifest's (neutral) build-time config: [ui].config, the board
defaults [ui].defaults and "release" from [bundle.release], merged into
build/ui-config.json; copy [[files]] into build/stage/<top>/; write the board
defaults as the operator's template (bbs/config.example.json) and, with
--site-config only (the demo), a runtime bbs/config.json; write
build/<name>-<version>[-<suffix>].zip and its .sha256 (sha256sum format).

The plain zip ships no bbs/config.json: the operator copies
config.example.json to config.json, so uploading a new release over the old
one never replaces their settings.

The zip is deterministic for the same inputs: entries sorted, fixed
timestamps (SOURCE_DATE_EPOCH, else the newest pinned commit's time), fixed
modes (0644 files, 0755 directories and `executable` files). Needs Python 3.11+, git, and Node/npm
for the UI build.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
import tomllib
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent.parent  # this repo


def log(msg: str) -> None:
    print(f"[build] {msg}", file=sys.stderr, flush=True)


def run(cmd: list[str], cwd: Path | None = None, env: dict[str, str] | None = None, capture: bool = False) -> str:
    log("$ " + " ".join(cmd) + (f"  (in {cwd})" if cwd else ""))
    res = subprocess.run(cmd, cwd=cwd, env=env, check=True, text=True, stdout=subprocess.PIPE if capture else None)
    return res.stdout.strip() if capture else ""


@dataclass
class Component:
    name: str
    url: str
    commit: str
    path: Path | None = None  # checkout location once fetched
    dirty_ok: bool = False  # --worktree: used as is, commit not enforced


def parse_pairs(values: list[str], flag: str) -> dict[str, str]:
    out = {}
    for v in values:
        name, sep, path = v.partition("=")
        if not sep or not name or not path:
            sys.exit(f"{flag} expects <component>=<path>, got {v!r}")
        out[name] = path
    return out


def fetch(c: Component, src_dir: Path) -> None:
    """Clone c.url and check out c.commit into src_dir/<name> (fresh each run)."""
    dest = src_dir / c.name
    if dest.exists():
        shutil.rmtree(dest)
    run(["git", "clone", "--quiet", "--no-checkout", c.url, str(dest)])
    run(["git", "-c", "advice.detachedHead=false", "checkout", "--quiet", c.commit], cwd=dest)
    head = run(["git", "rev-parse", "HEAD"], cwd=dest, capture=True)
    if head != c.commit:
        sys.exit(f"{c.name}: checked out {head}, manifest pins {c.commit}")
    c.path = dest


def commit_time(c: Component) -> int:
    assert c.path is not None
    try:
        return int(run(["git", "show", "-s", "--format=%ct", c.commit], cwd=c.path, capture=True))
    except subprocess.CalledProcessError:
        return 0


def build_ui(manifest: dict, comps: dict[str, Component], config: Path) -> None:
    ui = manifest["ui"]
    c = comps[ui["component"]]
    assert c.path is not None
    env = {k: v for k, v in os.environ.items() if not k.startswith(("VITE_", "KUZUHA_"))}
    env["KUZUHA_CONFIG"] = str(config)
    out = c.path / ui["output"]
    if out.exists():
        shutil.rmtree(out)
    if not c.dirty_ok or not (c.path / "node_modules").is_dir():
        run(list(ui["install"]), cwd=c.path, env=env)
    run(list(ui["build"]), cwd=c.path, env=env)
    if not (out / "index.html").is_file():
        sys.exit(f"UI build wrote no {out}/index.html")


def excluded(rel: PurePosixPath, patterns: list[str]) -> bool:
    """A pattern starting with "/" is anchored: it matches the whole path
    relative to `from` (or its leading directory). Other patterns also match
    any single path segment."""
    s = str(rel)
    for p in patterns:
        if p.startswith("/"):
            a = p[1:]
            if fnmatch.fnmatchcase(s, a) or fnmatch.fnmatchcase(rel.parts[0], a) and len(rel.parts) > 1:
                return True
        elif fnmatch.fnmatchcase(s, p) or any(fnmatch.fnmatchcase(part, p) for part in rel.parts):
            return True
    return False


def resolve_from(spec: str, comps: dict[str, Component]) -> Path:
    where, sep, rel = spec.partition(":")
    if not sep:
        sys.exit(f"files.from must be <component>:<path> or self:<path>, got {spec!r}")
    base = ROOT if where == "self" else comps[where].path
    if base is None:
        sys.exit(f"unknown component {where!r} in {spec!r}")
    return base / rel


def stage(manifest: dict, comps: dict[str, Component], top_dir: Path) -> None:
    global_ex = manifest.get("global", {}).get("exclude", [])
    for entry in manifest["files"]:
        src = resolve_from(entry["from"], comps)
        to = entry["to"]
        ex = global_ex + entry.get("exclude", [])
        if entry["from"].endswith("/"):
            if not src.is_dir():
                sys.exit(f"{entry['from']}: not a directory ({src})")
            for f in sorted(src.rglob("*")):
                rel = PurePosixPath(f.relative_to(src).as_posix())
                if f.is_dir() or excluded(rel, ex):
                    continue
                dest = top_dir / to / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(f, dest)
        else:
            if not src.is_file():
                sys.exit(f"{entry['from']}: not a file ({src})")
            dest = top_dir / to
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            if entry.get("executable"):
                dest.chmod(0o755)


def read_object(path: Path) -> dict:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        sys.exit(f"{path}: not a JSON object")
    return cfg


def release_of(manifest: dict) -> dict:
    """[bundle.release] with {name} / {version} substituted, plus the version."""
    bundle = manifest["bundle"]
    sub = {"name": bundle["name"], "version": bundle["version"]}
    rel = {k: str(v).format(**sub) for k, v in bundle.get("release", {}).items()}
    release = {"name": rel.get("name", bundle["name"]), "version": bundle["version"]}
    if "url" in rel:
        release["url"] = rel["url"]
    return release


def ui_build_config(manifest: dict, base: Path, defaults: Path, out: Path) -> Path:
    """The build-time UI config: base, then the board defaults ("$" comment
    keys left out), then "release". Without a config.json the board looks
    exactly like with an unedited copy of config.example.json, and the
    release in the footer follows the build, not the operator's file."""
    cfg = read_object(base)
    cfg.update({k: v for k, v in read_object(defaults).items() if not k.startswith("$")})
    cfg["release"] = release_of(manifest)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def write_json_file(src: Path, dest: Path, key: str) -> None:
    """A runtime file next to index.html, copied from src (checked to be an object)."""
    cfg = read_object(src)
    if dest.exists():
        sys.exit(f"{dest} already staged by [[files]]; it is written from [ui].{key}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(cfg, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_zip(stage_dir: Path, top: str, zip_path: Path, epoch: int) -> None:
    # Zip timestamps are local-time fields without a zone; store UTC.
    stamp = time.gmtime(max(epoch, 315532800))[:6]  # zip cannot go before 1980
    root = stage_dir / top
    paths = sorted(p.relative_to(stage_dir).as_posix() for p in root.rglob("*"))
    with zipfile.ZipFile(zip_path, "w") as z:
        for name in [top, *paths]:
            p = stage_dir / name
            if p.is_dir():
                info = zipfile.ZipInfo(name + "/", stamp)
                info.external_attr = (0o40755 << 16) | 0x10
                info.create_system = 3
                z.writestr(info, b"")
            else:
                info = zipfile.ZipInfo(name, stamp)
                # 0755 only where [[files]] said executable (stage() chmods it).
                info.external_attr = (0o100755 if p.stat().st_mode & 0o100 else 0o100644) << 16
                info.create_system = 3
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, p.read_bytes(), compresslevel=9)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", default=str(ROOT / "dist/php-min.toml"))
    ap.add_argument("--src", action="append", default=[], metavar="NAME=PATH",
                    help="clone this component from a local repo instead of its URL (pinned commit still enforced)")
    ap.add_argument("--worktree", action="append", default=[], metavar="NAME=PATH",
                    help="use this directory as is, no clone or checkout (dev builds only; the zip is marked)")
    ap.add_argument("--ui-config", help="build-time UI config instead of the manifest's [ui].config (KUZUHA_CONFIG)")
    ap.add_argument("--site-config", help="also ship this runtime UI config as bbs/config.json (the demo); the plain zip has none")
    ap.add_argument("--suffix", default="", help="appended to the zip name: <name>-<version>-<suffix>.zip")
    ap.add_argument("--out", default=str(ROOT / "build"), help="output directory (default build/)")
    a = ap.parse_args()

    manifest = tomllib.loads(Path(a.manifest).read_text(encoding="utf-8"))
    bundle = manifest["bundle"]
    srcs = parse_pairs(a.src, "--src")
    trees = parse_pairs(a.worktree, "--worktree")
    comps = {n: Component(n, c["url"], c["commit"]) for n, c in manifest["components"].items()}
    for n in [*srcs, *trees]:
        if n not in comps:
            sys.exit(f"unknown component {n!r}; manifest has {', '.join(comps)}")

    out = Path(a.out).resolve()
    src_dir = out / "src"
    src_dir.mkdir(parents=True, exist_ok=True)
    dev = False
    for c in comps.values():
        if c.name in trees:
            c.path = Path(trees[c.name]).resolve()
            c.dirty_ok = True
            dev = True
            head = run(["git", "rev-parse", "HEAD"], cwd=c.path, capture=True)
            log(f"{c.name}: using {c.path} as is (HEAD {head[:12]}, pinned {c.commit[:12]})")
        else:
            if c.name in srcs:
                c.url = str(Path(srcs[c.name]).resolve())
            fetch(c, src_dir)

    def given_or_manifest(cli: str | None, key: str) -> Path:
        p = Path(cli or manifest["ui"][key])
        return (p if p.is_absolute() else (Path.cwd() / p if cli else ROOT / p)).resolve()

    defaults = given_or_manifest(None, "defaults")
    build_ui(manifest, comps, ui_build_config(manifest, given_or_manifest(a.ui_config, "config"), defaults, out / "ui-config.json"))
    site_config = Path(a.site_config).resolve() if a.site_config else None

    version = bundle["version"]
    top = bundle["top"].format(name=bundle["name"], version=version)
    stem = f"{bundle['name']}-{version}" + (f"-{a.suffix}" if a.suffix else "") + ("-dev" if dev else "")
    stage_dir = out / "stage" / stem
    if stage_dir.exists():
        shutil.rmtree(stage_dir)
    (stage_dir / top).mkdir(parents=True)
    stage(manifest, comps, stage_dir / top)
    write_json_file(defaults, stage_dir / top / manifest["ui"]["defaults_to"], "defaults")
    if site_config is not None:
        write_json_file(site_config, stage_dir / top / manifest["ui"]["site_config_to"], "site_config_to")

    if "SOURCE_DATE_EPOCH" in os.environ:
        epoch = int(os.environ["SOURCE_DATE_EPOCH"])
    else:
        epoch = max(commit_time(c) for c in comps.values())
    zip_path = out / f"{stem}.zip"
    write_zip(stage_dir, top, zip_path, epoch)
    digest = hashlib.sha256(zip_path.read_bytes()).hexdigest()
    sha_path = zip_path.with_name(zip_path.name + ".sha256")
    sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="ascii")

    log(f"wrote {zip_path} ({zip_path.stat().st_size} bytes)")
    print(f"{digest}  {zip_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

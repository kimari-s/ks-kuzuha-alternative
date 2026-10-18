# ks-kuzuha-alternative

A kuzuha-style message board (in the line of Ayashii World, あやしいわーるど) that runs on **ordinary shared hosting: upload it by FTP and it works**.

- UI: [ks-kuzuha-ui](https://github.com/kimari-s/ks-kuzuha-ui) (JavaScript that runs in the browser: newest-first listing, tree view, past-log search, anonymous posting)
- API: [ks-sw-api](https://github.com/kimari-s/ks-sw-api) (PHP + SQLite; no database server, no long-running process). The PHP reference implementation of **kssw**, derived from the [6umi.net](https://6umi.net) API

**kssw** is the agreement (protocol) between the UI and the API. Its specification is [ks-sw-spec](https://github.com/kimari-s/ks-sw-spec). Any UI and any API that speak kssw can be combined.

Each release is one zip that puts these two together in a single folder.

Demo: <https://demo.newsupers.net/kuzuha-alternative/> (in English: <https://demo.newsupers.net/kuzuha-alternative/?lang=en>)

The demo is an example installation on a free shared host (XREA Free). The ads you see there are inserted automatically by XREA as a condition of the free plan; they are not there to make money for this project (see "Hosts with mandatory ads" below).

> **This is not the official KuzuhaScript.** It is a separate implementation modelled on the look and feel of KuzuhaScript.
> It is not compatible with the old kuzuha settings files, past logs or CGI.

## Requirements

| Item | Requirement |
|---|---|
| PHP | 7.4 or later (8.x is fine), with PDO and **pdo_sqlite** enabled (enabled by default on most shared hosts) |
| Web server | Apache, with **`.htaccess` allowed and mod_rewrite enabled** |
| HTTPS | **Recommended.** `http://` works, but posts are sent unencrypted. If your host offers free SSL, use `https://` |
| Other | No MySQL or other database. No Composer, no SSH (FTP is enough to install) |

Check whether PHP has `pdo_sqlite` in your host's control panel or with `phpinfo()`.

**Watch out for the PHP version used on the web.** Even when the control panel or `php -v` over SSH shows 7.4 or later, some hosts run an older version on the web by default (XREA's default is 7.0). If PHP is too old, opening `api/v1/meta` returns an error with `"code":"php_version"` and the version. In that case, switch PHP to 7.4 or later (8.x recommended) in your host's control panel.

## What is in the zip

```
ks-kuzuha-alternative-0.2.0-alpha.1/
├── README.txt             short instructions
├── LICENSES/              licences of each component
├── tools/                 admin command (use it on your own computer; do not put it on the server)
│   ├── kssw-admin
│   └── README.txt
├── well-known/            optional: a pointer for /.well-known/ at the domain root ("Discovery file" below)
│   ├── kssw
│   └── .htaccess
└── bbs/                   ← put this on the server (any folder name)
    ├── index.html         the board
    ├── about.html         the About page ("About page and custom pages" below)
    ├── assets/            the UI's JavaScript and CSS
    ├── fonts/             UDEV Gothic (monospaced font that keeps the tree view's box-drawing lines aligned)
    ├── favicon.svg, favicon-32.png, apple-touch-icon.png  the icon (replace them to use your own)
    ├── config.example.json  board name, colours and other settings: copy to config.json to change them
    └── api/               the PHP API
        ├── index.php
        ├── admin.php      minimal admin page (fallback)
        ├── .htaccess      URL rewriting, and blocks access to settings and the database
        ├── config.example.php
        └── lib/
```

The UI calls `api/` in the same folder (same domain, so no CORS setup is needed).

## Install (FTP)

1. Download `ks-kuzuha-alternative-<version>.zip` from [Releases](https://github.com/kimari-s/ks-kuzuha-alternative/releases) and extract it.
	- To check it has not been tampered with: the `.sha256` file next to it must match the output of `sha256sum` (on Windows, `certutil -hashfile <zip> SHA256`).
2. Upload the `bbs/` folder, with everything in it, by FTP. Example: `public_html/bbs/`.
	- Any folder name works (`kuzuha/`, or directly at the domain root).
	- **Make sure `api/.htaccess` is uploaded.** Some FTP programs hide files that start with a dot. Without `.htaccess` the API does not work, and the settings file can be read from outside.
	- There is no `config.json` in the zip: the board starts with the default settings. To change them, see "Changing the board name and colours" below.
	- Transfer mode "auto" or "binary" is fine (the fonts must be sent in binary).
3. Open `https://your-domain/bbs/api/v1/meta` in a browser. If you see something like the following, the API is working (other fields such as `impl_version` follow).

	```
	{"protocol":"kssw","version":"1","profile":"min","impl":"php", ...}
	```

4. Open `https://your-domain/bbs/`. If you can post, the board works.
5. Open the board's settings page (設定 / Settings in the header). It checks from your browser that the files the API keeps private (settings, database) cannot be fetched from outside. **If a red security warning appears**, `api/.htaccess` is missing or not in effect: upload it (turn on "show hidden files" in your FTP program) and reload. The settings page also says when `config.json` has a mistake.

The database file and its tables are created automatically on the first post (strictly, on the first request).

### Discovery file (optional)

kssw UIs and tools can learn where a domain's API is by reading `https://your-domain/.well-known/kssw` (kssw specification §6). **The board works without it.** Do this only if you can write to the domain root (the top of your public folder):

1. Upload `kssw` and `.htaccess` from the zip's `well-known/` folder to a `.well-known/` folder directly under your public folder (e.g. `public_html/.well-known/kssw`).
	- If `.well-known/` already exists (for SSL certificates, for example) and already has an `.htaccess`, do not overwrite it; append the contents of ours to the end of it.
2. If `bbs/` is not at the domain root, change `"base": "/bbs/api"` in `kssw` to the URL path of the API folder (e.g. `/kuzuha/api`).
3. Open `https://your-domain/.well-known/kssw`. If it shows what you wrote, you are done.

If you can put an `.htaccess` at the domain root, you can instead have the API answer it through a rewrite rather than placing the file. How to write it is in ks-sw-api's `php/well-known/README.md`.

## Changing the board name and colours

Copy `bbs/config.example.json` to **`bbs/config.json`** (same folder), edit it, and upload it by FTP. The change shows the next time the board is opened (no rebuild needed). Open it in a text editor and save it as **UTF-8**. Without `config.json` the board uses the values in `config.example.json`, which are also built in.

```json
{
  "network": "Ayashii World",
  "boardTags": ["My board"],
  "theme": { "hue": 30, "accentHue": 200, "accentStrength": 0.6 }
}
```

With this example the title becomes "Ayashii World＠My board" and the background turns brownish. Keys you leave out keep their defaults. The default `network` (as in `config.example.json`) is `あやしいわーるど` (Ayashii World).

The part of the title after `＠` is the board's tag (`boardTags`). Posts get this tag, and the listing (Local) shows the posts that carry it. If `boardTags` is empty, the title is just `network` and every post is listed.

- If you rename the board (its tag) later, earlier posts keep the old tag and drop out of the listing. To keep showing them, list the old tag too for a while (e.g. `"boardTags": ["New name", "Old name"], "postTags": ["New name"]`; the title becomes "New name+Old name").
- To use something other than `＠`, write e.g. `"messages": { "network.at": "{network} / {tags}" }`.

| Key | Meaning |
|---|---|
| `network` | The part of the title before `＠`. With `""` the title is `＠<tag>` |
| `theme.hue` | Background hue (0–360; 195, the default, is a blue-green blackboard colour) |
| `theme.accentHue` / `theme.accentStrength` | Hue (0–360) and strength (0–1; 0 is white) of the colour shown when buttons and the like are pressed |
| `theme.controls` | Colours of input fields and text selection: `standard` (default; the browser's usual white inputs) or `custom` (theme colours: inputs in a dark shade of the background hue, selected text in the accent colour) |
| `locale` | Fallback UI language (`ja` or `en`; `ja` as shipped). See "Language" below |
| `localeAuto` | `false` stops the UI from following the viewer's browser language |
| `boardTags` / `postTags` / `excludeTags` | The board's tags (the part of the title after `＠`; posts get them and the listing shows their posts) / tags added to posts when they differ from `boardTags` / tags whose posts are hidden from the listing (e.g. `["Chat"]`) |
| `localTags` / `scope` | Tags whose posts make up the Local listing (default: `boardTags`; e.g. add the tags bots post under without putting them in the title) / the listing a viewer starts with: `local` or `global` (every post). Viewers can switch on the settings page |
| `tagsMode` / `showTags` | How tags are shown (`full`, `nofilter`, `minimal`) / the initial state of "Show tags" |
| `memo` | A line or two at the top of the listing, in a frame titled Memo (メモ), by tag: `{"<tag>": "<text>"}`. The board's own listing takes its first board tag (e.g. `"memo": { "My board": "Be nice" }`); a listing narrowed to one tag takes that tag |
| `about` | Your own text on the About page (広報室), in place of its first line, by language: `{"ja": "…", "en": "…"}`. Plain text; line breaks kept; URLs and `[text](https://…)` become links |
| `links` | Links shown under the header and under the post form. `links.related` is the row under the post form ("About page and custom pages" below) |
| `release` | The version shown at the very bottom of the page. Built in; do not set it (a `config.json` copied from release 0.1.0-alpha.1 has it: delete that entry, or the old version keeps showing) |
| `font` | The UI font ("Changing the font" below). Without it, the bundled UDEV Gothic |

Other keys and full details are in the ks-kuzuha-ui README, "Instance config". Keys starting with `$` (`$comment`) are notes and are ignored.

- Viewers can change the colours and the "inputs and selection" setting (theme colours) to their liking on the "Settings" (設定) page. The values in `config.json` are the defaults for viewers who have not changed them.
- If a mistake makes the file unreadable as JSON, the whole `config.json` is ignored and the board shows with the default settings (it keeps working). A value of the wrong type (e.g. text where a list belongs) drops just that setting. Either way the **settings page (設定) shows a notice** saying which file and what is wrong (for broken JSON, the line and column where the browser tells it).
- If a change does not show, reload the page. On some hosts caching delays it by a few minutes.

### Language

`locale` (`ja` by default) is the fallback. A viewer whose browser prefers English gets English (`"localeAuto": false` turns that off), and a link with `?lang=en` or `?lang=ja` picks the language and keeps it as the viewer's choice. Details: ks-kuzuha-ui README, "Language".

### Changing the font

The default font is the bundled UDEV Gothic (`bbs/fonts/`: the HSJPDOC variant of [UDEV Gothic](https://github.com/yuru7/udev-gothic) v2.2.0, unmodified apart from shorter file names; SIL Open Font License 1.1). To use another font, add `font` to `bbs/config.json`.

Example using font files uploaded to `bbs/fonts/` by FTP:

```json
{
  "font": {
    "family": "\"My Font\", \"UDEV Gothic\", monospace",
    "faces": [
      { "family": "My Font", "src": "fonts/MyFont-Regular.woff2", "format": "woff2", "weight": 400 },
      { "family": "My Font", "src": "fonts/MyFont-Bold.woff2", "format": "woff2", "weight": 700 }
    ]
  }
}
```

Example using a font installed on the viewer's computer:

```json
{ "font": { "family": "\"BIZ UDGothic\", monospace" } }
```

| Key | Meaning |
|---|---|
| `font.family` | Font for the whole page (written as a CSS `font-family`; includes the post text) |
| `font.mono` | Font only for the places shown monospaced, such as post text (defaults to `family`) |
| `font.faces` | Font files to load, one `{family, src, format?, weight?, style?}` each. `src` is a path relative to `bbs/`, or a URL |
| `font.stylesheets` | URLs of CSS to load (e.g. a web-font service's CSS) |

- The tree view's box-drawing lines (`　│├└`) and text art (AA) in posts line up only with a font in which a full-width character is exactly two half-width characters wide. Choose such a font for post text.
- Fonts are loaded only when used. If `family` does not include UDEV Gothic, the bundled font is not loaded.
- Check the licence of any font you upload. Leave the bundled UDEV Gothic files and `LICENSE-UDEVGothic.txt` unchanged (under the OFL, a modified font may not call itself "UDEV Gothic").
- More in the ks-kuzuha-ui README, "Fonts".

## About page and custom pages

The board ships a default About page, `bbs/about.html`. It is a plain static HTML page, not part of the board's JavaScript app.

It says in one line what this is (a kuzuha-style board) and shows what is running, each linked to its source:

- the release (name and version, built into the zip; linked to this repository),
- the UI version (linked to ks-kuzuha-ui),
- the API: `impl impl_version` from its `/v1/meta`, linked to `impl_url` (ks-sw-api), then `protocol`, `version`, `profile`, `impl`, `impl_version` and `features`.

The About page is optional: nothing the board needs is on it (notices for the operator are on the settings page).

A small script on the page reads the `config.json` next to it and the API location (`apiBaseUrl`) and fills in these values. Without JavaScript the text still reads.

The page follows the board's language, in this order: `?lang=` in the URL, the viewer's saved choice, the browser language (unless `localeAuto` is `false`), then `locale`, then English. It also uses the board's colours (`theme.hue`, or the viewer's saved colours) and font.

### The link row under the post form

By default, the row of links under the post form shows "About" (広報室 in the Japanese UI), linking to `about.html`. This row is `links.related` in `bbs/config.json`.

Each entry is `{"label": ..., "href": ..., "newTab"?: true}`:

- `label` is either a string or a map by language, e.g. `{"en": "About", "ja": "広報室"}`. The viewer's language is used, else `en`, else the first value.
- `href` is the link target, e.g. a page next to `index.html`.
- `newTab: true` opens the link in a new tab.

Setting `links.related` **replaces** the default list, so keep the About entry when you add your own. `"related": []` removes the row.

### Adding your own page

1. Write a page, e.g. `rules.html`.
2. Upload it to `bbs/`, next to `index.html`.
3. Add it to `bbs/config.json` (copied from `config.example.json` if you have none yet):

	```json
	{
	  "links": {
	    "related": [
	      { "label": { "en": "About", "ja": "広報室" }, "href": "about.html" },
	      { "label": { "en": "Rules", "ja": "ルール" }, "href": "rules.html" }
	    ]
	  }
	}
	```

**Upgrades overwrite `about.html`** (it is part of the bundle). Put your own text in a page with another name rather than editing `about.html`, or keep a copy of your edited version.

The settings page (設定) shows only the viewer's settings (and the notices above); it has no link row and no link to the About page.

## Permissions

| Target | Setting |
|---|---|
| Files | 644 (your FTP program's default) |
| Folders | 755 (same) |
| `bbs/api/data/` (where the database lives) | Must be writable by PHP. See below |

PHP creates `bbs/api/data/` by itself. On hosts where it cannot (posting fails with an error), create the `data` folder by FTP and change its permissions:

- Hosts where PHP runs as your FTP user (suEXEC, PHP-FPM; most modern shared hosts): 700 or 705
- Hosts where PHP runs as the web server's user (mod_php): 707 or 777

PHP files (`.php`) do not need execute permission (755).

## Database location, and moving it out of the public folder

All data is one SQLite file. Its default location is `bbs/api/data/kssw.sqlite3`. `.htaccess` blocks direct access to `data/` and `*.sqlite3`, but **if you can, put it outside your public folder (`public_html` or similar)**. Then the data cannot be fetched from outside even if `.htaccess` stops working.

1. Copy `bbs/api/config.example.php` to a file named `config.php` (in the same folder).
2. Change `db_path`. `__DIR__` is the `api/` folder. Example for `public_html/bbs/api/`:

	```php
	// in kssw/ under your home directory (one level above public_html)
	'db_path' => dirname(__DIR__, 3) . '/kssw/kssw.sqlite3',
	```

	`dirname(__DIR__, 3)` is three levels up from `api/` (`api` → `bbs` → `public_html` → home). Adjust the number to how deep you placed it. An absolute path (`'/home/you/kssw/kssw.sqlite3'`) is fine too.
3. The folder (e.g. `kssw/`) must be writable by PHP (same as the permissions above). PHP creates it if it does not exist.
4. If the board already has posts, move `kssw.sqlite3` to the new location by FTP before switching. If there are files ending in `-journal`, `-wal` or `-shm`, move them too.

In `config.php` you can also change the time zone (default `Asia/Tokyo`), the minimum interval between posts (default 5 seconds), and more. Each setting is explained in `config.example.php`. `.htaccess` keeps `config.php` from being read from outside.

### Backup

The admin command `kssw-admin backup kssw.sqlite3` makes a complete copy that stays consistent even while posts are being written ("Administration" below). Without the admin command, just download `kssw.sqlite3` by FTP (at a quiet time, when few posts are coming in).

## Upgrade

1. Extract the new zip.
2. Upload the contents of `bbs/`, **overwriting** the old files. Nothing needs to be deleted first.
3. Your settings stay: the zip ships only the examples (`config.example.json`, `api/config.example.php`), never `config.json` or `api/config.php`, and not `api/data/` (the database), so overwriting does not touch them.
	- When a release adds new keys, the release notes say so. If needed, compare the new `config.example.json` with your `config.json` and add them to yours.
	- Upgrading from 0.1.0-alpha.1, whose zip shipped a `config.json`: delete the `"release"` entry from your `config.json` (the version now comes with the build).
	- **Do not use your FTP program's "synchronise" or "mirror" (features that delete files that exist only on the server).** They delete your settings and your database.
4. `about.html` is replaced by the new version ("About page and custom pages" above).
5. Old files such as `index-xxxxxxxx.js` stay in `assets/`. They are no longer used and do no harm; delete them if you like.

Releases that change the database format will include instructions in the release notes.

## Administration (deleting posts, maintenance, backup)

Two ways:

| | You need | You can |
|---|---|---|
| **Minimal administration without Python**: the admin page `bbs/api/admin.php` in a browser | a browser, and the board on `https://` | log in with a password, see recent posts, delete / restore them |
| **Full administration with the admin command (Python 3.8+)**: `tools/kssw-admin` on your own computer | Python 3.8 or later on your computer | everything: search, bulk delete / restore, maintenance mode, backup, the admin log; it can be handed to an AI agent |

Python is usually already there on Linux, but **on Windows and macOS it usually has to be installed first** (python.org; on Windows also the Microsoft Store). If that is a hurdle, start with the admin page ("Minimal administration without Python" below).

### Full administration with the admin command (Python 3.8+)

Administration is done **from your own computer** with the zip's `tools/kssw-admin` (the admin command). Do not upload it to the server (that is why it sits outside `bbs/`). It runs with Python 3.8 or later without installing anything, and all its output is JSON, so the main way to use it is to **let an AI agent such as Claude operate it directly**.

#### Setup (once)

1. Create a secret token. It is not sent anywhere.

	```sh
	python3 tools/kssw-admin token new
	```

	```json
	{
	  "token": "<43 random characters: your token>",
	  "sha256": "<64 hex characters>",
	  "config_line": "'admin_token_sha256' => '<64 hex characters>',",
	  "note": "…"
	}
	```

	Keep `token` on your own computer (treat it like a password; do not show it to anyone).
2. Add the `config_line` line inside `return [ … ];` in `bbs/api/config.php` on the server, and upload it by FTP. If there is no `config.php`, make one by copying `config.example.php`.

	```php
	<?php
	return [
	    'admin_token_sha256' => '<64 hex characters>',
	];
	```

	Only the token's hash (SHA-256) goes on the server. To replace the token, create a new one and change the line. Removing the line turns the admin API off (it returns 404).
3. Use the board **over `https://`**. The admin API does not work over `http://` (403 `https_required`), and the admin command will not send the token to an `http://` address either.
4. Check it. Setup is complete when `features` in `https://your-domain/bbs/api/v1/meta` includes `"admin"` and the following answers:

	```sh
	export KSSW_URL=https://your-domain/bbs/api
	export KSSW_ADMIN_TOKEN=(the token from step 1)
	python3 tools/kssw-admin capabilities
	```

On Windows, use `py` instead of `python3`, and `set` instead of `export` (in PowerShell, `$env:KSSW_URL = "…"`).

After 10 wrong tokens from the same IP within 15 minutes, that IP cannot use the admin API for a while (429).

#### Usage

| Task | Command |
|---|---|
| Find posts | `kssw-admin posts list --q spam` (post text), `--author name` (exact poster name), `--tag chat`, `--since 2026-10-01`, `--status deleted` |
| Only see what deleting would do | `kssw-admin posts delete --dry-run <id> <id> …` |
| Delete | `kssw-admin posts delete <id> …` (shown as deleted; undo with `posts restore <id>`) |
| Delete everything a search found | `kssw-admin posts list --author troll \| kssw-admin posts delete --stdin` |
| Backup | `kssw-admin backup kssw.sqlite3` (a complete copy of the database) |
| Maintenance mode | `kssw-admin maintenance on` / `off` / `get` (while on, posting stops; reading still works) |
| Admin log | `kssw-admin log` (when, what, and from where; actions on the admin page are included) |
| Description of every command | `kssw-admin commands` (JSON), and `--help` on each command |

`kssw-admin` is short for `python3 tools/kssw-admin`. On https servers that only offer old ciphers (such as XREA's shared SSL), connecting fails. In that case add `--tls-compat` (or set the environment variable `KSSW_TLS_COMPAT=1`): it also allows the old ciphers while still verifying the certificate. The result is one JSON value (for people, use `--format table`). On failure, `{"error": {"code": …, "message": …, "status": …}}` goes to standard error, and the exit code is 1 (usage error), 2 (authentication: wrong token, or not https), 3 (not found), 4 (state conflict, e.g. in maintenance) or 5 (server or network error).

#### Handing it to an AI agent

Give the agent (Claude Code or similar) an environment where it can run `tools/kssw-admin`, set `KSSW_URL` and `KSSW_ADMIN_TOKEN` as environment variables, and write something like this in its instructions:

```
The board is managed with kssw-admin (tools/kssw-admin). KSSW_URL and
KSSW_ADMIN_TOKEN are already set as environment variables. Never print
or record the token, and never put it on a command line.
- First run `kssw-admin commands` to learn the commands, arguments and output.
- Output is one JSON value on standard output. On failure, {"error": …}
  on standard error. Exit codes: 0 success, 1 usage, 2 authentication,
  3 not found, 4 conflict / maintenance, 5 server / network.
- Find posts with `kssw-admin posts list` (--q, --author, --tag, --status,
  --since, --until, --root, --all).
- Before any change, always run it with --dry-run and check "results",
  then run it without --dry-run. Deletions can be undone with `posts restore`.
- Before changing many posts at once, take `kssw-admin backup <file>`.
- Do not switch maintenance mode unless asked.
- `kssw-admin log` shows what was done.
```

Full details of the commands (with sample output for each) are in the ks-sw-api README, "Administration (for AI agents)".

### Minimal administration without Python (admin page)

`https://your-domain/bbs/api/admin.php`. A page where you log in with a password, see posts 50 at a time, newest first, and delete or restore them; nothing else (search, maintenance, backup and the log are done with the admin command).

Setting the password (once, in the browser):

1. Open `https://your-domain/bbs/api/admin.php`. While no password is set up it shows a setup form. (It works only over `https://`.)
2. Type a password (at least 12 characters) twice and press the button. The page shows one line, like `'admin_password_hash' => '$2y$10$…',`, and the steps below. Nothing is saved on the server yet: the page only computes the line (the password itself is not in it, only its hash).
3. With your FTP program, open `bbs/api/`. If it has no `config.php`, download `config.example.php` and keep the copy under the name `config.php`.
4. Open `config.php` in a text editor, find the line `'admin_password_hash' => '',` and replace that whole line with the line from step 2. Save it as UTF-8 and upload it to `bbs/api/`.
5. Reload `admin.php`: the login form appears. Log in with the password from step 2.

To change the password later, set the value back to `''` in `config.php` and start again from step 1. Five wrong passwords in a row lock the login for 15 minutes; the setup form takes at most 10 tries per 15 minutes.

On a computer with PHP you can make the line yourself instead: `php -r 'echo password_hash("your password", PASSWORD_DEFAULT), "\n";'` gives the `$2y$10$…` part (wrap it in single quotes `'`, as it contains `$`).

## Hosts with mandatory ads (XREA Free and similar)

The board also works on hosts like XREA Free, which insert ads automatically in exchange for free hosting.

- The ads are inserted into the HTML (`index.html`) automatically and appear above the board. The board does not cover or remove them.
- **Do not hide the ads.** XREA's terms of service forbid, on the Free plan, hiding the ads or otherwise preventing them from having effect (Article 14, paragraph 1, item 23). Do not modify the board to remove them with CSS or a browser extension either.
- The API (under `api/`) returns JSON. It is not a page, so it is not subject to the ads. If ads ever get into the API's responses, the board stops working; please report it in Issues.
- XREA requires **an index page at the top of the domain** (running without a top page is forbidden by the terms, same article, item 24). If you put the board in a folder such as `bbs/`, also put an `index.html` at the domain root. If you put the board itself at the domain root, it is the top page.
- **Change the PHP version.** XREA's web PHP defaults to 7.0, and the board does not run on it ("Requirements" above). Set it to 7.4 or later (8.x recommended) under "Site settings" (サイト設定) in the control panel.
- **About https.** Free SSL is available only when you set up your own domain as a "sub" domain. It cannot be set up on the initial domain (`account.server.xrea.com`).
	- Without your own domain, you can use shared SSL (`https://ss1.xrea.com/account.server.xrea.com/…`) for https. No setup is needed. The board works under a folder, so it works there as is.
	- But with shared SSL, **every XREA user shares the same address (`ss1.xrea.com`)**. Browsers do not tell their pages apart from other people's, so other people's pages may be able to read board data stored in the viewer's browser (such as the ID used to delete one's own posts). It is fine for trying things out, but for real use, use your own domain with free SSL. On shared SSL, do not use the admin page (`admin.php`); administer with the command (`kssw-admin --tls-compat`).
	- `http://` also works.

On other hosts, check the terms yourself. Whoever installs a board is normally responsible for what is posted on it.

## What this release cannot do

- No banned-word filter or access blocking (no banning of IPs or posters). The administrator can delete and restore posts, use maintenance mode, and make backups ("Administration" above)
- It does not display in browsers without JavaScript
- No import or export of old kuzuha past logs
- The board name, colours and so on can be changed in `config.json` (above). To change the UI itself, build ks-kuzuha-ui yourself (below)

## Source and build

| Component | Repository | Version in this release (0.2.0-alpha.1) |
|---|---|---|
| UI | [kimari-s/ks-kuzuha-ui](https://github.com/kimari-s/ks-kuzuha-ui) | 0.6.0-alpha.1 |
| API | [kimari-s/ks-sw-api](https://github.com/kimari-s/ks-sw-api) | 0.2.0-alpha.1 |
| Specification (kssw) | [kimari-s/ks-sw-spec](https://github.com/kimari-s/ks-sw-spec) | 0.1.0-alpha.1 (kssw 1, Draft) |
| Bundle (this repository) | [kimari-s/ks-kuzuha-alternative](https://github.com/kimari-s/ks-kuzuha-alternative) | 0.2.0-alpha.1 |

The version (commit) of each component is pinned in [`dist/php-min.toml`](dist/php-min.toml). Build the zip with the following (Python 3.11+, git, Node.js 22+, npm):

```sh
make dist      # build/ks-kuzuha-alternative-<version>.zip and .sha256
make smoke     # extracts the zip into docker php:7.4-apache and checks: /v1/meta is kssw 1;
               # /.well-known/kssw with well-known/ placed at /.well-known/;
               # in a browser (Playwright), display, posting and listing;
               # the About page (link row, about.html with /v1/meta, Japanese and English);
               # the zip has config.example.json and no config.json; no config.json, a copied,
               # an edited, a mistyped and a broken one (settings page notice); the settings page's
               # security warning with api/.htaccess's deny rules removed, none with them;
               # the admin.php password setup form; display over http (a name other than localhost).
               # Then runs tools/kssw-admin: capabilities and posts delete --dry-run (token put in config.php)
make smoke-full  # the above, plus reply, delete, search, tags, the settings page,
                 # language, the header (View menu, current item) and Back links
```

The same inputs always produce the same zip (same SHA-256). There are two kinds of configuration (keys: ks-kuzuha-ui README, "Instance config"):

| File | When it applies | Contents |
|---|---|---|
| [`config/bundle.json`](config/bundle.json) | When the UI is built | Things that are the same for every installation (API location `./api`, storage key prefix, etc.). Every zip uses the same build |
| [`config/site.json`](config/site.json) | Built in (merged over bundle.json, with `release`: name, version and URL from `dist/php-min.toml`), and shipped as `bbs/config.example.json` | The default board name, colours, tags, etc. The operator copies the example to `config.json` to change them |
| [`config/demo.json`](config/demo.json) | On every page load, for the demo site only (`make demo` / `make deploy-demo`: shipped as `bbs/config.json` in the demo zip) | Same as site.json, except the name |

The release name shown in the UI footer is the bare product name with its version, e.g. `ks-kuzuha-alternative v0.2.0-alpha.1`, linking to this repository (`[bundle.release]` in `dist/php-min.toml`).

The plain zip has no `bbs/config.json`, so uploading a release over an installation never replaces the operator's. To build a zip that also ships your own `config.json` (as the demo does):

```sh
python3 dist/build.py --site-config my.json --suffix mine
```

`make deploy-demo` is an example of sending the `bbs/` built by `make demo` to your own server. The destination goes in `make.local` (gitignored; `DEPLOY_HOST` / `DEPLOY_PATH`; see the top of the `Makefile`). It never sends the server's `api/config.php` and `api/data/`, and sends `config.json` only when the server has none.

## Reporting vulnerabilities

See [SECURITY.md](SECURITY.md).

## Licenses

| Component | License |
|---|---|
| ks-kuzuha-alternative (this repository) | MIT ([LICENSE](LICENSE)) |
| ks-kuzuha-ui | MIT |
| ks-sw-api | MIT |
| UDEV Gothic (`bbs/fonts/*.ttf`, © Yuko OTAWARA) | SIL Open Font License 1.1 |
| Icon: "auto_awesome" from Material Symbols (`bbs/favicon.svg` etc., © Google) | Apache License 2.0 |

The full texts are in the zip's `LICENSES/`. The font licence is also at `bbs/fonts/LICENSE-UDEVGothic.txt`, the icon's at `bbs/LICENSE-MaterialSymbols.txt`. The bundled UDEV Gothic is the unmodified original. To use another font, see "Changing the font".

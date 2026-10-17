ks-kuzuha-alternative - kuzuha-style message board (PHP + SQLite edition)
====================================================================

A message board in the style of KuzuhaScript. This is not the official
KuzuhaScript. The screens are JavaScript that runs in the browser
(ks-kuzuha-ui); the data is stored in SQLite by a PHP API (ks-sw-api).
The agreement (protocol) between the screens and the API is kssw
(https://github.com/kimari-s/ks-sw-spec).

== REQUIREMENTS

  - PHP 7.4 or later (with PDO and pdo_sqlite enabled)
  - Apache (.htaccess and mod_rewrite must be available)
  - HTTPS recommended (http:// works, but traffic is not encrypted)

  Check the PHP version used on the web, not only on the command line.
  Some hosts run an older PHP on the web by default (XREA: 7.0).

== INSTALL

  1. Upload the bbs/ folder, with everything in it, to your server by FTP.
     Any folder name is fine (e.g. public_html/bbs/).
     Do not forget .htaccess (files starting with a dot).
  2. Open https://your-domain/bbs/api/v1/meta in a browser. If you see
     something like {"protocol":"kssw","version":"1","profile":"min", ...}
     the API is working.
  3. Open https://your-domain/bbs/. If you can post, the board works.
  4. Open the settings page (設定 / Settings at the top). If a red
     security warning appears, api/.htaccess is missing (FTP programs
     often hide files starting with a dot) and your database may be
     downloadable: upload it, then reload the page.

  If posting fails with an error, create a folder named data inside
  bbs/api/ and set its permissions to 707 (or 777). On suEXEC servers,
  700 or 705 works. The database is bbs/api/data/kssw.sqlite3.

== DISCOVERY FILE (optional; the board works without it)

  If you can write to the top of your public folder (the domain root),
  you can upload kssw and .htaccess from the well-known/ folder to a
  .well-known/ folder at the domain root (e.g. public_html/.well-known/kssw).
  It lets kssw screens and tools find the API from the domain name alone.
  - If .well-known/ already has an .htaccess, do not overwrite it; append
    the contents of ours to it.
  - If bbs/ is not at the domain root, change "base": "/bbs/api" in kssw
    to the path of the API folder (e.g. "/kuzuha/api").
  Open https://your-domain/.well-known/kssw. If its contents show, you
  are done.

== BOARD NAME AND COLOURS

  Copy bbs/config.example.json to bbs/config.json, edit it and upload it
  by FTP; the change shows the next time the board is opened (save as
  UTF-8). Example: "network": "My board"
  If a mistake makes the file unreadable, the board keeps working with
  the default settings, and the settings page says what is wrong. The
  keys are explained in the README under "More information" below.

== ABOUT PAGE

  bbs/about.html is a plain About page, linked as "About" under the post
  form. Upgrades overwrite it: put your own text in a page with another
  name (e.g. rules.html) and add a link to it in bbs/config.json
  (links.related; see the README). The About page is optional.

== SETTINGS (optional)

  Copy bbs/api/config.example.php to a file named config.php and edit it
  to change the database location (outside the public folder is
  recommended), the minimum interval between posts (default 5 seconds),
  and more.

== ADMINISTRATION (deleting posts, maintenance, backup)

  Minimal administration without Python: open
  https://your-domain/bbs/api/admin.php (https only). The first time it
  asks for a password (twice) and shows one line to put into
  bbs/api/config.php (copy config.example.php to config.php if there is
  none; replace the line 'admin_password_hash' => '', with it; upload;
  reload). Then log in to delete or restore recent posts.

  Full administration with Python 3.8+: kssw-admin (the admin command)
  in tools/, on your own computer (Windows and macOS usually need Python
  installed first). Do not upload it to the server. You can also let an
  AI agent run it. See tools/README.txt.

== UPGRADE

  Upload the new bbs/ over the old one; nothing to delete first. The zip
  has no config.json, api/config.php or api/data/ (only the examples),
  so your settings and posts stay. From 0.1.0-alpha.1: delete the
  "release" entry from your config.json. For tools/, replace the copy on your own computer.
  Do not use your FTP program's "synchronise" (delete files that exist
  only on the server).

== MORE INFORMATION AND SOURCE

  https://github.com/kimari-s/ks-kuzuha-alternative

== LICENSES

  See LICENSES/.
  - ks-kuzuha-ui, ks-sw-api, ks-kuzuha-alternative: MIT License
  - UDEV Gothic font (bbs/fonts/): SIL Open Font License 1.1
  - Icon (bbs/favicon.svg etc.), "auto_awesome" from Material Symbols:
    Apache License 2.0

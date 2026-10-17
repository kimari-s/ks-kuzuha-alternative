kssw-admin - admin command for the board (made for AI agents)
====================================================================

kssw-admin in this folder is a command for running the board's
administration (deleting and restoring posts, maintenance mode, backups,
the admin log) from your own computer. Do not upload it to the server
(that is why it sits outside bbs/).

With Python 3.8 or later it runs as is; nothing to install. All output is
JSON, so an AI agent such as Claude can operate it directly.

== SETUP (once)

  1. Create a secret token. It is not sent anywhere.

       python3 kssw-admin token new

     Keep the "token" it prints on your own computer (treat it like a
     password).
  2. Add the "config_line" it prints ('admin_token_sha256' => '...',) as
     one line inside return [ ... ]; in bbs/api/config.php on the server,
     and upload the file by FTP. If there is no config.php, make one by
     copying config.example.php. Only the token's hash goes on the server,
     never the token itself.
  3. Use the board over https://. The admin API does not work over http://.

== USAGE

  Put the board's API location and the token in environment variables.

    export KSSW_URL=https://your-domain/bbs/api
    export KSSW_ADMIN_TOKEN=(the token from token new)

    python3 kssw-admin capabilities                  check that it works
    python3 kssw-admin posts list --q spam           search post text (also --author, --tag)
    python3 kssw-admin posts delete --dry-run <id>   only show what deleting would do
    python3 kssw-admin posts delete <id>             delete (undo with posts restore <id>)
    python3 kssw-admin backup kssw.sqlite3           back up the database
    python3 kssw-admin maintenance on / off          maintenance mode (posting stopped)
    python3 kssw-admin log                           admin log
    python3 kssw-admin commands                      description of every command (JSON)

  On Windows, type py instead of python3.

== HANDING IT TO AN AI AGENT

  Write something like this in the agent's instructions:

    The board is managed with kssw-admin (tools/kssw-admin). KSSW_URL and
    KSSW_ADMIN_TOKEN are already set as environment variables. Never print
    or record the token. First run `kssw-admin commands` to learn the usage.
    Before any change, always check the result with --dry-run, then run it.
    Take a backup before deleting in bulk.

  Exit codes: 0 success, 1 usage error, 2 authentication (wrong token, or
  not https), 3 not found, 4 state conflict (e.g. in maintenance),
  5 server or network error.

== DELETING FROM A BROWSER ONLY

  bbs/api/admin.php is a simple admin page that needs no Python: log in
  with a password, then delete or restore recent posts; nothing else.
  The first time, it asks for a password and shows the line to put into
  bbs/api/config.php (README.md, "Minimal administration without
  Python").

More information: https://github.com/kimari-s/ks-sw-api (README, "Administration")

# Security policy

ks-kuzuha-alternative is a distribution: it bundles ks-kuzuha-ui and
ks-sw-api into one zip for shared hosting. Report here problems of the
bundle itself, for example:

- a file in the zip that exposes something when uploaded as documented
  (a missing `.htaccess` rule, a config or database file served over HTTP);
- install or upgrade instructions that leave a server open;
- a zip that does not match its published SHA-256.

Vulnerabilities in the components belong to their repositories (you may
also report them here; we forward them):
[ks-sw-api](https://github.com/kimari-s/ks-sw-api) (the API, admin API and
CLI), [ks-kuzuha-ui](https://github.com/kimari-s/ks-kuzuha-ui) (the board
UI), and [ks-sw-spec](https://github.com/kimari-s/ks-sw-spec) for the kssw
protocol.

## How to report

1. **Preferred:** GitHub private vulnerability reporting — the
   repository's **Security** tab → **Report a vulnerability**.
2. **Fallback:** email **security@6umi.net** (the RFC 2142 `security@`
   mailbox).

Please do not open a public issue for an undisclosed vulnerability. We aim
to acknowledge a report within a week. There is no bug bounty.

## Supported versions

The latest release. This is alpha software: fixes land in the next
release, not in old ones.

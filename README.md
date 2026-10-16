# ks-kuzuha-alternative

くずは風（あやしいわーるど系）の掲示板を、**普通のレンタルサーバに FTP で置くだけ**で動かすための配布物です。

- 画面：[ks-kuzuha-ui](https://github.com/kimari-s/ks-kuzuha-ui)（ブラウザで動く JavaScript。新しい順の一覧・ツリー表示・過去ログ検索・匿名投稿）
- API：[ks-sw-api](https://github.com/kimari-s/ks-sw-api)（PHP + SQLite。データベースサーバ・常駐プロセス不要）。[6umi.net](https://6umi.net) の API から生まれた、**kssw** の PHP の参照実装

画面と API の間の取り決め（プロトコル）が **kssw** です。仕様は [ks-sw-spec](https://github.com/kimari-s/ks-sw-spec) にあります。kssw を話す画面と API なら、組み合わせを替えられます。

この 2 つを 1 つのフォルダにまとめた zip を、リリースごとに配っています。

デモ：<https://demo.newsupers.net/kuzuha-alternative/>

> **公式の KuzuhaScript ではありません。** くずはスクリプトの見た目と使い勝手を参考にした、別の実装です。
> 旧くずはの設定ファイル・過去ログ・CGI との互換はありません。

## 必要なもの

| 項目 | 条件 |
|---|---|
| PHP | 7.4 以上（8.x 可）。PDO と **pdo_sqlite** が有効なこと（多くのレンタルサーバで既定で有効） |
| Web サーバ | Apache。**`.htaccess` が使え、mod_rewrite が有効**なこと |
| HTTPS | **推奨**。`http://` でも動きますが、書き込みの内容が暗号化されずに送られます。無料 SSL が使えるサーバでは `https://` にしてください |
| その他 | MySQL などのデータベースは不要。Composer・SSH も不要（FTP だけで設置できます） |

PHP で `pdo_sqlite` が使えるかは、サーバの管理画面か `phpinfo()` で確かめてください。

**Web で動く PHP の版に注意**してください。管理画面の表示や SSH の `php -v` が 7.4 以上でも、Web の既定が古い版のサーバがあります（XREA は既定が 7.0）。PHP が古いと、`api/v1/meta` を開いたときに `"code":"php_version"` と版を示すエラーが返ります。そのときは管理画面で PHP のバージョンを 7.4 以上（8.x 推奨）に変えてください。

## 中身

```
ks-kuzuha-alternative-0.1.0-alpha.1/
├── README-ja.txt          簡単な説明
├── LICENSES/              各部品のライセンス
├── tools/                 管理コマンド（自分のパソコンで使う。サーバには置かない）
│   ├── kssw-admin
│   └── README-ja.txt
├── well-known/            任意：ドメイン直下の /.well-known/ に置く案内（下の「発見用のファイル」）
│   ├── kssw
│   └── .htaccess
└── bbs/                   ← これをサーバに置く（フォルダ名は自由）
    ├── index.html         掲示板の画面
    ├── assets/            画面の JavaScript・CSS
    ├── fonts/             UDEV Gothic（罫線のツリー表示を揃えるための等幅フォント）
    ├── favicon.png
    ├── config.json        掲示板の名前・色などの設定（FTP で書き換えられます）
    └── api/               PHP の API
        ├── index.php
        ├── admin.php      最小限の管理画面（予備）
        ├── .htaccess      URL の書き換えと、設定・DB へのアクセス禁止
        ├── config.example.php
        └── lib/
```

画面は同じフォルダの `api/` を呼びます（同じドメインなので CORS の設定は不要）。

## 設置（FTP）

1. [Releases](https://github.com/kimari-s/ks-kuzuha-alternative/releases) から `ks-kuzuha-alternative-<版>.zip` を取り、展開します。
	- 改ざんの確認：同じ所にある `.sha256` の値と、`sha256sum`（Windows は `certutil -hashfile <zip> SHA256`）の結果が一致すること。
2. `bbs/` フォルダを、中身ごと FTP でアップロードします。例：`public_html/bbs/`。
	- フォルダ名は自由です（`kuzuha/` でも、ドメイン直下でも可）。
	- **`api/.htaccess` を必ず送ってください。** ドットで始まるファイルは FTP ソフトの設定で隠れていることがあります。`.htaccess` が無いと API が動かず、設定ファイルが外から見える状態になります。
	- 転送モードは「自動」か「バイナリ」で構いません（フォントはバイナリで送る必要があります）。
3. ブラウザで `https://あなたのドメイン/bbs/api/v1/meta` を開き、次のように出れば API は動いています（`impl_version` などの項目も並びます）。

	```
	{"protocol":"kssw","version":"1","profile":"min","impl":"php", ...}
	```

4. `https://あなたのドメイン/bbs/` を開いて、書き込めれば完了です。

最初の書き込み（正確には最初のアクセス）で、データベースのファイルとテーブルが自動で作られます。

### 発見用のファイル（任意）

kssw の画面やツールは、`https://あなたのドメイン/.well-known/kssw` を読んで、そのドメインの API の場所を知ることができます（kssw の仕様 §6）。**置かなくても掲示板は動きます。** ドメイン直下（公開フォルダの一番上）に書き込めるときだけ、次のようにします。

1. zip の `well-known/` の中の `kssw` と `.htaccess` を、公開フォルダ直下の `.well-known/` フォルダへアップロードします（例：`public_html/.well-known/kssw`）。
	- `.well-known/` が既にあり（SSL 証明書用など）、`.htaccess` もあるときは、上書きせず、こちらの `.htaccess` の中身を末尾に書き足します。
2. `bbs/` をドメイン直下以外に置いたときは、`kssw` の `"base": "/bbs/api"` を、API のフォルダの URL のパス（例：`/kuzuha/api`）に書き換えます。
3. `https://あなたのドメイン/.well-known/kssw` を開き、書いた内容が出れば完了です。

ドメイン直下に `.htaccess` を置けるなら、ファイルを置く代わりに書き換え（rewrite）で API に答えさせることもできます。書き方は ks-sw-api の `php/well-known/README.md` にあります。

## 掲示板の名前・色を変える

`bbs/config.json` を書き換えて FTP で送り直すだけです。次に掲示板を開いたときから反映されます（build し直す必要はありません）。テキストエディタで開き、**UTF-8** のまま保存してください。

```json
{
  "network": "あやしいわーるど",
  "defaultTags": ["うちの掲示板"],
  "mainTags": ["うちの掲示板"],
  "theme": { "hue": 30, "accentHue": 200, "accentStrength": 0.6 }
}
```

この例では、タイトルが「あやしいわーるど＠うちの掲示板」になり、背景が茶色寄りになります。書かなかった項目は既定値のままです。

タイトルの `＠` の後は、掲示板のタグ（`mainTags`）です。書き込みにはこのタグが付き（`defaultTags`）、一覧にはこのタグの付いた書き込みが出ます。`mainTags` が空なら、タイトルは `network` だけで、全部の書き込みが出ます。

- 名前（タグ）を後から変えると、それまでの書き込みは古いタグのままなので、一覧に出なくなります。続けて出すには、しばらく古いタグも並べます（例：`"mainTags": ["新しい名前", "古い名前"]`。タイトルは「新しい名前+古い名前」）
- `＠` を別の文字にするには `"messages": { "network.at": "{network} / {tags}" }` のように書きます

| 項目 | 意味 |
|---|---|
| `network` | タイトルの `＠` の前。`""` ならタイトルは `＠<タグ>` |
| `theme.hue` | 背景の色相（0〜360。195 が既定の青緑の黒板色） |
| `theme.accentHue` / `theme.accentStrength` | ボタンなどを押したときの色の色相（0〜360）と強さ（0〜1。0 で白） |
| `theme.controls` | 入力欄と選択範囲の色。`standard`（既定。ブラウザ標準の白い入力欄）か `custom`（テーマの色。入力欄は背景の色相に合わせた暗い色、選択した文字はアクセントの色） |
| `locale` | 画面の言語（`ja` か `en`） |
| `defaultTags` / `mainTags` / `excludeTags` | 書き込みに付けるタグ／一覧に出すタグ（タイトルの `＠` の後）／一覧から隠すタグ（例：`["雑談"]`） |
| `tagsMode` / `showTags` | タグの表示（`full`・`nofilter`・`minimal`）／「タグを表示する」の初期値 |
| `links` | 見出しと投稿欄の下に出すリンク（例：`"related": [{"label": "トップ", "href": "/"}]`） |
| `release` | 画面の一番下に出る版の表示。zip を作るときに入ります。消しても動きます |
| `font` | 画面のフォント（下の「フォントを変える」）。書かなければ同梱の UDEV Gothic |

ほかの項目と詳しい説明は ks-kuzuha-ui の README の "Instance config" にあります。`$` で始まる項目（`$comment`）は説明書きで、無視されます。

- 色と「入力欄・選択範囲」（テーマの色で表示する）は、見る人が「設定」画面で自分好みに変えられます。`config.json` の値は、見る人が変えていないときの既定値です。
- 書き間違えて JSON として読めなくなると、`config.json` 全体が無視され、zip を作ったときの設定で表示されます（掲示板は止まりません）。ブラウザの開発者ツールのコンソールに警告が出ます。
- 反映されないときは、ブラウザを再読み込みしてください。サーバによってはキャッシュで数分遅れることがあります。

### フォントを変える

既定のフォントは同梱の UDEV Gothic（`bbs/fonts/`。[UDEV Gothic](https://github.com/yuru7/udev-gothic) v2.2.0 の HSJPDOC 版を、ファイル名だけ短くして改変せずに入れています。SIL Open Font License 1.1）です。別のフォントにするには、`bbs/config.json` に `font` を書きます。

フォントのファイルを `bbs/fonts/` に FTP で置いて使う例：

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

見る人のパソコンに入っているフォントを使う例：

```json
{ "font": { "family": "\"BIZ UDGothic\", monospace" } }
```

| 項目 | 意味 |
|---|---|
| `font.family` | 画面全体のフォント（CSS の `font-family` の書き方。書き込みの本文も含む） |
| `font.mono` | 書き込みの本文など、等幅で出す所だけのフォント（書かなければ `family` と同じ） |
| `font.faces` | 読み込むフォントのファイル。1 つずつ `{family, src, format?, weight?, style?}`。`src` は `bbs/` からの相対パスか URL |
| `font.stylesheets` | 読み込む CSS の URL（Web フォントのサービスの CSS など） |

- ツリー表示の罫線（`　│├└`）と書き込みの AA は、全角がちょうど半角 2 文字分の幅のフォントで揃います。本文には、そういうフォントを選んでください。
- フォントは使われるときだけ読み込まれます。`family` に UDEV Gothic を含めなければ、同梱のフォントは読み込まれません。
- 置くフォントのライセンスを確かめてください。同梱の UDEV Gothic のファイルと `LICENSE-UDEVGothic.txt` は変えずに置いておいてください（OFL では、改変したフォントは「UDEV Gothic」を名乗れません）。
- 詳しくは ks-kuzuha-ui の README の "Fonts" にあります。

## パーミッション

| 対象 | 設定 |
|---|---|
| ファイル | 644（FTP ソフトの既定のまま） |
| フォルダ | 755（同上） |
| `bbs/api/data/`（DB の置き場） | PHP が書き込めること。下記 |

`bbs/api/data/` は PHP が自分で作ります。作れない（書き込むとエラーになる）サーバでは、FTP で `data` フォルダを作ってパーミッションを変えてください。

- PHP が FTP と同じユーザで動くサーバ（suEXEC・PHP-FPM。最近のレンタルサーバの多く）：700 か 705
- PHP が Web サーバのユーザで動くサーバ（mod_php）：707 か 777

PHP のファイル（`.php`）に実行権限（755）は要りません。

## データベースの場所と、公開フォルダの外への移動

データは SQLite のファイル 1 つです。既定の場所は `bbs/api/data/kssw.sqlite3` です。`.htaccess` が `data/` と `*.sqlite3` への直接のアクセスを禁じていますが、**できれば公開フォルダ（`public_html` など）の外に置いてください**。`.htaccess` が効かなくなった場合でも、データが外から取られません。

1. `bbs/api/config.example.php` を `config.php` という名前でコピーします（同じフォルダ）。
2. `db_path` を書き換えます。`__DIR__` は `api/` フォルダのことです。例：`public_html/bbs/api/` に置いた場合

	```php
	// ホームの下の kssw/ に置く（public_html の 1 つ上）
	'db_path' => dirname(__DIR__, 3) . '/kssw/kssw.sqlite3',
	```

	`dirname(__DIR__, 3)` は `api/` から 3 つ上（`api` → `bbs` → `public_html` → ホーム）です。置いた深さに合わせて数を変えてください。絶対パス（`'/home/あなた/kssw/kssw.sqlite3'`）でも構いません。
3. 置き場のフォルダ（例：`kssw/`）は PHP が書き込める必要があります（上のパーミッションと同じ）。無ければ PHP が作ります。
4. すでに書き込みがある場合は、移す前に `kssw.sqlite3` を新しい場所へ FTP で移してください。`-journal` `-wal` `-shm` で終わるファイルがあれば一緒に移します。

`config.php` ではほかに、時刻のタイムゾーン（既定 `Asia/Tokyo`）、連続投稿の間隔（既定 30 秒）などを変えられます。各項目の説明は `config.example.php` の中にあります。`config.php` は `.htaccess` で外から読めないようにしてあります。

### バックアップ

管理コマンドの `kssw-admin backup kssw.sqlite3` で、書き込み中でも壊れない完全なコピーが取れます（下の「管理」）。管理コマンドを使わない場合は、`kssw.sqlite3` を FTP で取ってくるだけです（書き込みの少ない時間帯に取ってください）。

## 更新

1. 新しい版の zip を展開し、**展開した `bbs/config.json` を消します**（サーバにある自分の `config.json` を上書きしないため）。
	- `config.json` を書き換えていない場合は、消さずに上書きしても構いません。
	- 新しい版で項目が増えたときは、リリースノートに書きます。必要なら新しい `config.json` を見比べて、自分の方に書き足してください。
2. `bbs/` の中身を**上書き**でアップロードします。
3. `api/config.php` と `api/data/`（データベース）は zip に入っていないので、上書きしても消えません。
	- **FTP ソフトの「同期」「ミラー」（サーバ側にしか無いファイルを削除する機能）は使わないでください。** 設定とデータベースが消えます。
4. `assets/` には古い版の `index-xxxxxxxx.js` などが残りますが、使われないだけで害はありません。気になれば消してください。

データベースの形式が変わる版では、リリースノートに手順を書きます。

## 管理（投稿の削除・メンテナンス・バックアップ）

管理は、zip の `tools/kssw-admin`（管理コマンド）で、**自分のパソコンから**行います。サーバには上げません（`bbs/` の外に置いてあるのはそのためです）。Python 3.8 以上があればインストール不要で動き、出力はすべて JSON なので、Claude などの **AI エージェントにそのまま操作させる**のが主な使い方です。

ブラウザだけで投稿を消したい人のために、`bbs/api/admin.php` に最小限の管理画面（パスワードでログインし、最近の投稿を削除・復元するだけ）もあります。下の「管理画面（予備）」を見てください。

### 準備（最初の 1 回）

1. 合言葉（トークン）を作ります。どこにも送信されません。

	```sh
	python3 tools/kssw-admin token new
	```

	```json
	{
	  "token": "3iSmaIsekLlx73TkCofCNMVl55RywNuFKZp1Hmj_Ppo",
	  "sha256": "c3ddb18a…",
	  "config_line": "'admin_token_sha256' => 'c3ddb18a…',",
	  "note": "…"
	}
	```

	`token` は自分のパソコンに保管します（パスワードと同じ扱い。人に見せない）。
2. `config_line` の 1 行を、サーバの `bbs/api/config.php` の `return [ … ];` の中に足して、FTP で送ります。`config.php` が無ければ `config.example.php` をコピーして作ります。

	```php
	<?php
	return [
	    'admin_token_sha256' => 'c3ddb18a…',
	];
	```

	サーバに置くのはトークンのハッシュ（SHA-256）だけです。トークンを取り替えるときは、新しく作って行を書き換えます。行を消せば管理 API は止まります（404 になります）。
3. 掲示板を **`https://` で**使ってください。管理 API は `http://` では動きません（403 `https_required`）。管理コマンドも、`http://` の相手にはトークンを送りません。
4. 確かめます。`https://あなたのドメイン/bbs/api/v1/meta` の `features` に `"admin"` が出て、次が答えれば準備完了です。

	```sh
	export KSSW_URL=https://あなたのドメイン/bbs/api
	export KSSW_ADMIN_TOKEN=（1 で作ったトークン）
	python3 tools/kssw-admin capabilities
	```

Windows では `python3` の代わりに `py`、`export` の代わりに `set`（PowerShell では `$env:KSSW_URL = "…"`）を使います。

同じ IP から 15 分に 10 回トークンを間違えると、その IP からはしばらく管理 API が使えなくなります（429）。

### 使い方

| やること | コマンド |
|---|---|
| 投稿を探す | `kssw-admin posts list --q 宣伝`（本文）、`--author 名前`（投稿者名が一致）、`--tag 雑談`、`--since 2026-10-01`、`--status deleted` |
| 消したらどうなるか見るだけ | `kssw-admin posts delete --dry-run <id> <id> …` |
| 削除する | `kssw-admin posts delete <id> …`（削除済みの表示になります。`posts restore <id>` で戻せます） |
| 探したものをまとめて削除 | `kssw-admin posts list --author 荒らし \| kssw-admin posts delete --stdin` |
| バックアップ | `kssw-admin backup kssw.sqlite3`（データベースの完全なコピー） |
| メンテナンスモード | `kssw-admin maintenance on` / `off` / `get`（on の間は書き込みが止まり、閲覧はできます） |
| 管理ログ | `kssw-admin log`（いつ、何を、どこから。管理画面での操作も載ります） |
| 全コマンドの説明 | `kssw-admin commands`（JSON）、各コマンドに `--help` |

`kssw-admin` は `python3 tools/kssw-admin` の略です。古い暗号方式しか使えない https のサーバ（XREA の共有 SSL など）では接続に失敗します。そのときは `--tls-compat`（または環境変数 `KSSW_TLS_COMPAT=1`）を付けてください。証明書の確認は続けたまま、古い方式も使えるようにします。結果は 1 つの JSON で出ます（人が見るなら `--format table`）。失敗すると、標準エラーに `{"error": {"code": …, "message": …, "status": …}}` が出て、終了コードは 1（使い方の誤り）、2（認証：トークン違い・https でない）、3（見つからない）、4（状態の衝突：メンテナンス中など）、5（サーバ・通信のエラー）です。

### AI エージェントに任せる

エージェント（Claude Code など）に `tools/kssw-admin` を使える環境を用意し、`KSSW_URL` と `KSSW_ADMIN_TOKEN` を環境変数に設定してから、指示に次のように書きます。

```
掲示板は kssw-admin（tools/kssw-admin）で管理する。KSSW_URL と
KSSW_ADMIN_TOKEN は環境変数に設定済み。トークンは表示・記録せず、
コマンドラインにも書かない。
- 最初に `kssw-admin commands` で、コマンド・引数・出力を確かめる。
- 出力は標準出力に JSON 1 つ。失敗時は標準エラーに {"error": …}。
  終了コード 0 成功、1 使い方、2 認証、3 見つからない、4 衝突・メンテナンス、
  5 サーバ・通信。
- 投稿は `kssw-admin posts list`（--q, --author, --tag, --status, --since,
  --until, --root, --all）で探す。
- 変更の前に必ず --dry-run で "results" を確かめ、それから --dry-run なしで
  実行する。削除は `posts restore` で戻せる。
- まとめて変更する前に `kssw-admin backup <ファイル>` を取る。
- 頼まれない限りメンテナンスモードを切り替えない。
- 何をしたかは `kssw-admin log` で確かめられる。
```

コマンドの詳しい説明（全コマンドの出力例）は ks-sw-api の README の "Administration (for AI agents)" にあります。

### 管理画面（予備）

`https://あなたのドメイン/bbs/api/admin.php`。パスワードでログインし、新しい順に 50 件ずつ投稿を見て、削除・復元するだけの画面です（検索・メンテナンス・バックアップ・ログは管理コマンドで）。

使うには、パスワードのハッシュを `config.php` に書きます。PHP のあるパソコンで

```sh
php -r 'echo password_hash("あなたのパスワード", PASSWORD_DEFAULT), "\n";'
```

を実行し、出てきた `$2y$10$…` を `'admin_password_hash' => '$2y$10$…',` として `config.php` に足します（`$` を含むので必ずシングルクォート `'` で囲みます）。ハッシュが無い間、管理画面は 403 で閉じています。5 回続けて間違えると 15 分ロックされます。`https://` で使ってください。

## 広告が必須のサーバ（XREA Free など）

XREA Free のように、無料の代わりに広告が自動で入るサーバでも動きます。

- 広告は HTML（`index.html`）に自動で挿入され、掲示板の画面の上に表示されます。掲示板の画面は広告を覆ったり消したりしません。
- **広告を非表示にしないでください。** XREA の利用規約では、Free プランで広告を非表示にするなど広告の効果が出ないようにする行為は禁止です（第 14 条 1 項 23 号）。CSS やブラウザの拡張で消す改造もしないでください。
- API（`api/` の下）は JSON を返します。画面ではないので、広告の対象になりません。万一 API の応答に広告が入ると掲示板が動かなくなります。その場合は Issues で知らせてください。
- XREA では、ドメインの**トップに index のページが必要**です（トップページを置かない運用は規約で禁止、同 24 号）。掲示板を `bbs/` などのフォルダに置く場合は、ドメイン直下にも `index.html` を置いてください。掲示板そのものをドメイン直下に置けば、それがトップになります。
- **PHP のバージョンを変えてください。** XREA の Web の PHP は既定が 7.0 で、そのままでは動きません（上の「必要なもの」）。管理画面の「サイト設定」から 7.4 以上（8.x 推奨）にします。
- **https について。** 無料 SSL を使えるのは、独自ドメインを「サブ」として設定したときです。初期ドメイン（`アカウント名.サーバー名.xrea.com`）には設定できません。
	- 独自ドメインが無ければ、共有 SSL（`https://ss1.xrea.com/アカウント名.サーバー名.xrea.com/…`）で https にできます。設定は要りません。掲示板はフォルダの下でも動くので、そのまま使えます。
	- ただし共有 SSL は、**XREA の全利用者が同じアドレス（`ss1.xrea.com`）を共有**します。ブラウザは他の人のページと区別しないため、他の人のページから、閲覧者のブラウザに保存された掲示板の情報（投稿の削除に使う ID など）が読める可能性があります。お試しには使えますが、本格的に使うなら独自ドメインで無料 SSL にしてください。共有 SSL では管理画面（`admin.php`）を使わず、管理はコマンド（`kssw-admin --tls-compat`）で行ってください。
	- `http://` でも動きます。

ほかのサーバでも、規約は各自で確かめてください。掲示板に書かれた内容の責任は、設置した人が負うのが普通です。

## できないこと（この版）

- NG ワード・アクセス拒否（IP・投稿者の禁止）はありません。管理者ができるのは、投稿の削除・復元、メンテナンスモード、バックアップです（上の「管理」）
- JavaScript が動かないブラウザでは表示されません
- 旧くずはの過去ログの読み込み・書き出しはありません
- 掲示板の名前・色などは `config.json` で変えられます（上記）。画面そのものを変えるには ks-kuzuha-ui を自分で build します（下記）

## ソースと build

| 部品 | リポジトリ | この版（0.1.0-alpha.1）に入っているもの |
|---|---|---|
| 画面 | [kimari-s/ks-kuzuha-ui](https://github.com/kimari-s/ks-kuzuha-ui) | 0.5.0-alpha.1 |
| API | [kimari-s/ks-sw-api](https://github.com/kimari-s/ks-sw-api) | 0.2.0-alpha.1 |
| 仕様（kssw） | [kimari-s/ks-sw-spec](https://github.com/kimari-s/ks-sw-spec) | 0.1.0-alpha.1（kssw 1、Draft） |
| 配布物（このリポジトリ） | [kimari-s/ks-kuzuha-alternative](https://github.com/kimari-s/ks-kuzuha-alternative) | 0.1.0-alpha.1 |

各部品の版（commit）は [`dist/php-min.toml`](dist/php-min.toml) に固定してあります。zip は次で作れます（Python 3.11 以上、git、Node.js 22 以上、npm）。

```sh
make dist      # build/ks-kuzuha-alternative-<版>.zip と .sha256
make smoke     # zip を docker の php:7.4-apache に展開し、/v1/meta が kssw 1 であること、
               # well-known/ を /.well-known/ に置いたときの /.well-known/kssw、
               # ブラウザ（Playwright）で表示・投稿・一覧、
               # config.json の書き換えの反映、http（localhost 以外の名前）での表示を確認。
               # 続けて tools/kssw-admin で capabilities と posts delete --dry-run（トークンは config.php に入れて）
make smoke-full  # 上に加えて返信・削除・検索・タグ・設定画面
```

同じ入力からは同じ zip（同じ SHA-256）ができます。設定は 2 つです（項目は ks-kuzuha-ui の README の "Instance config"）。

| ファイル | いつ効くか | 中身 |
|---|---|---|
| [`config/bundle.json`](config/bundle.json) | 画面の build 時 | どの設置先でも同じもの（API の場所 `./api`、保存キーの接頭辞など）。全部の zip で同じ build を使います |
| [`config/site.json`](config/site.json) | 表示のたび（`bbs/config.json` として zip に入る） | 掲示板の名前・色・タグなど。build 時に `release`（`dist/php-min.toml` の名前・版・URL）を書き足します |
| [`config/demo.json`](config/demo.json) | 同上（デモサイト用。`make demo` / `make deploy-demo`） | site.json と同じで、名前だけ違う |

自分の `config.json` 入りの zip を作るには：

```sh
python3 dist/build.py --site-config my.json --suffix mine
```

`make deploy-demo` は、`make demo` で作った `bbs/` を自分のサーバへ送る例です。送り先は gitignore の `make.local` に書きます（`DEPLOY_HOST` / `DEPLOY_PATH`。書き方は `Makefile` の冒頭）。サーバの `api/config.php` と `api/data/` は送らず、`config.json` もサーバに無いときだけ送ります。

## 脆弱性の報告

[SECURITY.md](SECURITY.md) を見てください。

## ライセンス

| 対象 | ライセンス |
|---|---|
| ks-kuzuha-alternative（このリポジトリ） | MIT（[LICENSE](LICENSE)） |
| ks-kuzuha-ui | MIT |
| ks-sw-api | MIT |
| UDEV Gothic（`bbs/fonts/*.ttf`、© Yuko OTAWARA） | SIL Open Font License 1.1 |

zip の `LICENSES/` に全文があります。フォントのライセンスは `bbs/fonts/LICENSE-UDEVGothic.txt` にも同じものを置いています。同梱の UDEV Gothic は改変していない原本です。別のフォントにするには「フォントを変える」を見てください。

---

## English

ks-kuzuha-alternative bundles [ks-kuzuha-ui](https://github.com/kimari-s/ks-kuzuha-ui) (a static SPA for a kuzuha-style BBS) and [ks-sw-api](https://github.com/kimari-s/ks-sw-api) (PHP 7.4+, SQLite; derived from the [6umi.net](https://6umi.net) API) into one zip that you upload by FTP to ordinary shared hosting. The UI and the API speak **kssw**, specified in [ks-sw-spec](https://github.com/kimari-s/ks-sw-spec); ks-sw-api is its PHP reference implementation. It is not the official KuzuhaScript and is not compatible with its CGI, settings or logs.

Demo: <https://demo.newsupers.net/kuzuha-alternative/?lang=en>

This release (0.1.0-alpha.1) contains ks-kuzuha-ui 0.5.0-alpha.1 and ks-sw-api 0.2.0-alpha.1 (kssw protocol 1, Draft; ks-sw-spec 0.1.0-alpha.1).

- **Requirements**: PHP 7.4+ with pdo_sqlite; Apache with `.htaccess` and mod_rewrite. HTTPS recommended (plain `http://` works, unencrypted).
- **Install**: upload the zip's `bbs/` folder (any name, any depth), including `api/.htaccess`. Check `https://<host>/bbs/api/v1/meta` (`{"protocol":"kssw","version":"1","profile":"min",…}`), then open `https://<host>/bbs/`. The SQLite file is created on first use in `bbs/api/data/`; move it outside the document root with `db_path` in `api/config.php` (copy of `config.example.php`).
- **Administration**: `tools/kssw-admin` (outside `bbs/`; Python 3.8+, stdlib only, JSON output, made for AI agents) drives the admin API of ks-sw-api: posts list / delete / restore (with `--dry-run`), maintenance mode, backup, admin log. Setup: `kssw-admin token new`, put its `config_line` (the token's SHA-256) into `bbs/api/config.php`, serve over HTTPS, set `KSSW_URL` / `KSSW_ADMIN_TOKEN`. `bbs/api/admin.php` is a minimal password-protected fallback page (recent posts, delete / undelete). Details: ks-sw-api README, "Administration (for AI agents)".
- **Discovery (optional)**: kssw clients can find the API from `https://<host>/.well-known/kssw`. If you can write to the document root, upload the zip's `well-known/kssw` and `well-known/.htaccess` to `<document root>/.well-known/` (append to an existing `.htaccess` there) and set `base` to your API's URL path if `bbs/` is not at the root. Or rewrite to the API instead: ks-sw-api `php/well-known/README.md`. The board works without it.
- **Board name, colours, tags**: edit `bbs/config.json` and upload it; read on every page load, no rebuild (keys: ks-kuzuha-ui README "Instance config"). The title is `network＠<mainTags joined with +>` (`network` alone when `mainTags` is empty); the board's name is its tag, so posts carry it (`defaultTags`) and the listing shows the posts tagged with it. Renaming the tag hides older posts unless the old tag stays in `mainTags`. `theme.controls`: `standard` (browser-look inputs, default) or `custom` (inputs and text selection in theme colours); viewers can switch it on the settings page. Broken JSON falls back to the build-time defaults.
- **Language**: `locale` in `bbs/config.json` (`ja` as shipped) is the fallback. A viewer whose browser prefers English gets English (`"localeAuto": false` turns that off), and a link with `?lang=en` or `?lang=ja` picks the language and keeps it as the viewer's choice (ks-kuzuha-ui README "Language").
- **Font**: the default is the bundled, unmodified UDEV Gothic (SIL OFL 1.1). To use another font, add `font` to `bbs/config.json`, e.g. `{"font": {"family": "\"My Font\", monospace", "faces": [{"family": "My Font", "src": "fonts/MyFont.woff2", "format": "woff2"}]}}` with the file uploaded to `bbs/fonts/` (keys: ks-kuzuha-ui README "Fonts"). Pick a font whose full-width glyphs are two half-widths wide, or the tree view's lines will not align.
- **Upgrade**: delete `bbs/config.json` from the new release (to keep yours), then upload the new `bbs/` over the old one. `api/config.php` and `api/data/` are not in the zip; do not use an FTP "mirror/sync with delete".
- **Hosts with mandatory ads** (XREA Free): ads are injected into the HTML and must not be hidden (XREA terms art. 14(1)(23)); the API answers JSON; a top-level index page is required.
- **Build**: `make dist` (Python 3.11+, git, Node 22+) builds the zip from the commits pinned in `dist/php-min.toml` (one neutral UI build, `config/bundle.json`; the runtime `bbs/config.json` from `config/site.json` plus `release`); `make smoke` tests it in `php:7.4-apache` with Playwright, including a `config.json` edit and a plain-http non-localhost origin, then runs the shipped `tools/kssw-admin` against it; it also checks that `/v1/meta` is kssw 1 and that `/.well-known/kssw`, placed from `well-known/`, leads to the API.
- **Security**: see [SECURITY.md](SECURITY.md).
- **Licenses**: MIT (this repo, ks-kuzuha-ui, ks-sw-api); UDEV Gothic fonts (bundled unmodified) under SIL OFL 1.1.

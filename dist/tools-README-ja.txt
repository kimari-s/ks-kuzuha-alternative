kssw-admin — 掲示板の管理コマンド（AI エージェント向け）
====================================================================

このフォルダの kssw-admin は、掲示板の管理（投稿の削除・復元、メンテナンス
モード、バックアップ、管理ログ）を、自分のパソコンから行うためのコマンドです。
サーバーには上げません（bbs/ の外に置いてあるのはそのためです）。

Python 3.8 以上があれば、インストール不要でそのまま動きます。出力はすべて
JSON なので、Claude などの AI エージェントにそのまま操作させられます。

■ 準備（最初の 1 回）

  1. 合言葉（トークン）を作ります。どこにも送信されません。

       python3 kssw-admin token new

     出てきた "token" は自分のパソコンに保管します（パスワードと同じ扱い）。
  2. 出てきた "config_line"（'admin_token_sha256' => '...',）を、サーバーの
     bbs/api/config.php の return [ ... ]; の中に 1 行足して、FTP で送ります。
     config.php が無ければ config.example.php をコピーして作ります。
     サーバーに置くのはトークンのハッシュだけで、トークンそのものは置きません。
  3. 掲示板は https:// で使ってください。http:// では管理 API は動きません。

■ 使い方

  環境変数に掲示板の API の場所とトークンを入れます。

    export KSSW_URL=https://あなたのドメイン/bbs/api
    export KSSW_ADMIN_TOKEN=（token new で作ったトークン）

    python3 kssw-admin capabilities                  動作確認
    python3 kssw-admin posts list --q 宣伝             本文で探す（--author, --tag も可）
    python3 kssw-admin posts delete --dry-run <id>    消したらどうなるかだけ見る
    python3 kssw-admin posts delete <id>              削除（posts restore <id> で戻せます）
    python3 kssw-admin backup kssw.sqlite3            データベースのバックアップ
    python3 kssw-admin maintenance on / off           メンテナンスモード（書き込み停止）
    python3 kssw-admin log                            管理ログ
    python3 kssw-admin commands                       全コマンドの説明（JSON）

  Windows では python3 の代わりに py と打ちます。

■ AI エージェントに任せるとき

  エージェントへの指示に、たとえば次のように書きます。

    掲示板は kssw-admin（tools/kssw-admin）で管理する。KSSW_URL と
    KSSW_ADMIN_TOKEN は環境変数に設定済み。トークンは表示・記録しない。
    最初に `kssw-admin commands` で使い方を確かめる。変更の前には必ず
    --dry-run で結果を確かめてから実行する。まとめて消す前には backup を取る。

  終了コード: 0 成功、1 使い方の誤り、2 認証（トークン違い・https でない）、
  3 見つからない、4 状態の衝突（メンテナンス中など）、5 サーバー・通信のエラー。

■ ブラウザだけで消したいとき

  bbs/api/admin.php に、パスワードでログインして最近の投稿を削除・復元する
  だけの簡単な管理画面があります（設定は README.md の「管理」）。

詳しい説明: https://github.com/kimari-s/ks-sw-api （README の Administration）

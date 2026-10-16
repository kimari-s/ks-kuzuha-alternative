ks-kuzuha-alternative — くずは風 掲示板（PHP + SQLite 版）
====================================================================

くずはスクリプト（KuzuhaScript）風の掲示板です。公式の KuzuhaScript では
ありません。画面はブラウザで動く JavaScript（ks-kuzuha-ui）、データは
PHP の API（ks-sw-api）が SQLite に保存します。画面と API の間の取り決め
（プロトコル）は kssw です（https://github.com/kimari-s/ks-sw-spec）。

■ 必要なもの

  - PHP 7.4 以上（PDO と pdo_sqlite が有効）
  - Apache（.htaccess と mod_rewrite が使えること）
  - HTTPS を推奨（http:// でも動きますが、通信が暗号化されません）

■ 設置

  1. bbs/ フォルダを、中身ごと FTP でサーバーにアップロードします。
     フォルダ名は自由です（例: public_html/bbs/）。
     .htaccess（ドットで始まるファイル）も忘れずに送ってください。
  2. ブラウザで https://あなたのドメイン/bbs/api/v1/meta を開き、
     {"protocol":"kssw","version":"1","profile":"min", ...} のように出れば
     API は動いています。
  3. https://あなたのドメイン/bbs/ を開き、書き込めれば完了です。

  書き込めない（エラーになる）ときは、bbs/api/ の中に data フォルダを作り、
  パーミッションを 707（または 777）にしてください。suEXEC のサーバーでは
  700 か 705 で動きます。データベースは bbs/api/data/kssw.sqlite3 です。

■ 発見用のファイル（任意。置かなくても動きます）

  公開フォルダの一番上（ドメイン直下）に書き込めるなら、well-known/ の
  中の kssw と .htaccess を、ドメイン直下の .well-known/ フォルダへ
  アップロードできます（例: public_html/.well-known/kssw）。kssw に対応した
  画面やツールが、ドメイン名だけで API の場所を知るためのものです。
  - .well-known/ に既に .htaccess があるときは、上書きせず中身を書き足します。
  - bbs/ をドメイン直下以外に置いたときは、kssw の "base": "/bbs/api" を
    API のフォルダの場所（例: "/kuzuha/api"）に書き換えます。
  https://あなたのドメイン/.well-known/kssw を開いて中身が出れば完了です。

■ 掲示板の名前・色

  bbs/config.json を書き換えて FTP で送り直すと、次に開いたときから
  反映されます（UTF-8 で保存）。例: "network": "うちの掲示板"
  書き間違えて読めなくなっても掲示板は止まらず、既定の設定で表示されます。
  項目の説明は下の「詳しい説明」の README にあります。

■ 設定（任意）

  bbs/api/config.example.php を config.php という名前でコピーして編集すると、
  データベースの場所（公開フォルダの外に置くのがおすすめ）、投稿間隔などを
  変えられます。

■ 管理（投稿の削除・メンテナンス・バックアップ）

  tools/ の kssw-admin（管理コマンド）を、自分のパソコンで使います。
  サーバーには上げません。AI エージェントに操作させることもできます。
  準備と使い方は tools/README-ja.txt を見てください。

  ブラウザだけで投稿を消したいときは、bbs/api/admin.php の簡単な管理画面
  （パスワードでログインして削除・復元するだけ）も使えます。設定は
  下の「詳しい説明」の README の「管理画面（予備）」にあります。

■ 更新

  新しい版の bbs/config.json を消してから（自分の config.json を残すため）、
  bbs/ を上書きアップロードします。api/config.php と api/data/ は
  zip に入っていないので、上書きしても消えません。tools/ は
  自分のパソコンの方を新しくします。FTP ソフトの「同期（サーバー
  側の余分なファイルを削除）」は使わないでください。

■ 詳しい説明・ソース

  https://github.com/kimari-s/ks-kuzuha-alternative

■ ライセンス

  LICENSES/ を参照してください。
  - ks-kuzuha-ui, ks-sw-api, ks-kuzuha-alternative: MIT License
  - UDEV Gothic フォント（bbs/fonts/）: SIL Open Font License 1.1

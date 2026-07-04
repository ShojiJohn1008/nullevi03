# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

「ナルエビちゃん三世」は、Claude Code を Telegram Bot 経由で常時稼働させるための極小ラッパー。リポジトリ本体には Bot ロジックは存在せず、`claude` CLI を `claude-plugins-official` の `plugin:telegram` チャンネルに繋いで起動・再起動するだけのシェルスクリプトで構成されている。

## 起動方法

```sh
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... ./boot.sh
```

- `boot.sh` は `claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official -c` を無限ループで実行し、終了したら 5 秒待って再起動する。
- 初回起動と再起動の各イベントを Telegram にプッシュ通知する (`notify_telegram` 関数)。
- `-c` フラグで前回セッションを継続するため、会話状態は Claude Code 側のセッション履歴に依存する。
- 設定値は他のスクリプトと同じく `.env` から読み込む。`TELEGRAM_BOT_TOKEN` は telegram プラグイン (claude の子プロセス) からも参照されるため export している。
- **channels は起動フラグだけでは動かない**。初回に telegram プラグインの導入 (`/plugin install telegram@claude-plugins-official` → `/telegram:configure <トークン>`) と、Telegram 側からのペアリング (`/telegram:access pair <コード>` → `/telegram:access policy allowlist`) が必要。要 Claude Code v2.1.80+ と Bun。手順の詳細は README を参照。トークンは `~/.claude/channels/telegram/.env`、許可リストは `~/.claude/channels/telegram/access.json` に保存される。

## 朝のブリーフィング

```sh
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... [BRIEFING_LOCATION=Tokyo] ./briefing.sh
```

- `briefing.sh` は毎朝定時に実行する想定。`claude -p` (ヘッドレス・単発セッション、`-c` なし) で `prompts/briefing.md` の指示に従いブリーフィング文を生成し、Telegram Bot API で送信する。boot.sh の常駐セッションとは独立して動く。
- 設定値 (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` / `BRIEFING_LOCATION`) は同ディレクトリの `.env` から読み込む (無ければ環境変数)。`.env` は `.gitignore` 済みで、秘密情報をリポジトリや crontab/plist に書かずに済ませるための仕組み。`.env.example` が雛形。
- ブリーフィングの内容 (日付・天気・TODO・ひとこと) は `prompts/briefing.md` で定義する。出力は Telegram 1 メッセージに収まるよう 1500 文字以内・プレーンテキスト縛り。
- `memory/todo.md` は秘書の永続メモリ。ブリーフィングで読み上げるほか、Telegram での会話中に「TODO に追加して」と頼まれたらこのファイルに追記する。セッションの要約・圧縮をまたいで残したい情報はここに書く。

## メール要約

```sh
./mail_summary.sh
```

- 特定の送信者からの新着メール (本文 + PDF/Excel/CSV 添付) を要約して Telegram に送る。朝のブリーフィングの少し後 (例 7:05) に launchd/cron から実行する想定。
- `fetch_mail.py` (Python 標準ライブラリのみ) が Gmail に **IMAP + アプリパスワード**で接続し、対象メールと添付を `mail_work/` に保存する。`imap.select("INBOX", readonly=True)` で開くのでメールを既読にも変更もしない。OAuth (Google Cloud) を避けて設定を最小化するための選択。
- 認証等は `.env` から読む: `GMAIL_ADDRESS` / `GMAIL_APP_PASSWORD` / `MAIL_SENDERS` (カンマ区切り) / `MAIL_LOOKBACK_DAYS` (既定3)。`GMAIL_APP_PASSWORD` は Google が空白区切りで表示するが、`.env` では**空白を詰めて**書く (空白を残すと `.env` の source が壊れる)。`fetch_mail.py` 側でも空白は除去している。
- **複数の受信箱**を横断する場合は `MAIL_ACCOUNT_N_ADDRESS` / `_PASSWORD` / `_HOST` (省略時 `imap.gmail.com`) を番号付きで並べる。1つでもあれば `GMAIL_*` より優先。`get_accounts()` が組み立てる。あるアカウントの接続に失敗しても他は続行し、`index.md` の「接続エラー」欄に記録して要約で知らせる。全滅かつ0件のときだけ非ゼロ終了する。`MAIL_SENDERS` は全アカウント共通の送信者フィルタ。
- `mail_summary.sh` が `fetch_mail.py` → `claude -p` (`prompts/mail_summary.md` の指示で要約) → Telegram 送信、の順で動く。対象メール 0 件なら claude を呼ばずに「新着なし」を送って終了する。
- 処理済みメールは `mail_state.txt` (Message-ID を記録、git 管理外) で重複を防ぐ。`mail_work/` にはメール本文・添付が入るので `.gitignore` 済み。**この2つは絶対にコミットしない**。
- Excel (.xlsx) の読み取りには pandas / openpyxl が必要 (`pip3 install pandas openpyxl`)。PDF は claude が直接読め、CSV はテキストとして読める。

## カレンダー連携・日程調整

```sh
python3 gcal.py list 2026-07-10                       # 予定一覧 (空き確認)
python3 gcal.py hold "打合せ" 2026-07-10T10:00 2026-07-10T11:00   # 仮押さえ
python3 gcal.py create "歯医者" 2026-07-10T15:00 2026-07-10T16:00 # 通常予定
python3 gcal.py delete <イベントID>
```

- `gcal.py` (Python 標準ライブラリのみ) が Google カレンダーを読み書きする。裏側は Apps Script のウェブアプリ (`gas/Calendar.gs`) で、`.env` の `CAL_WEBAPP_URL` に POST する。認証は `.env` の `CAL_SHARED_SECRET` と Apps Script 側スクリプトプロパティ `SHARED_SECRET` の一致で行う。設置手順は `gas/README.md`。
- **Apps Script 方式を選んだ理由**: カレンダー書き込みには OAuth が必須 (アプリパスワード不可)。MCP + OAuth 方式は「テスト公開のままだと refresh token が7日で失効し、朝の自動実行が毎週壊れる」罠がある (本番公開に切り替えれば回避可、個人利用なら審査不要)。Apps Script はトークン管理自体が無く、公開した URL に POST するだけなので保守がほぼゼロ。会話秘書 (boot.sh) からも launchd からも同じように叩ける。
- `CAL_WEBAPP_URL` と `CAL_SHARED_SECRET` は鍵。`.env` (git 管理外) に置き、漏らさない。URL が漏れても合言葉チェックで守られるが、両方とも秘密扱い。
- v1 は自分のカレンダーの読み書きまで。**他人へのゲスト招待は未対応**(通知が飛ぶ操作なので、足すときは送信前確認フローとセットにする)。

### 日程調整のやり方 (会話秘書が従う手順)

Telegram で日程調整メールの文面を渡されたり「この日程どこか空いてる?」と聞かれたら:

1. 相手が挙げた候補日について `python3 gcal.py list <日付>` で既存予定を確認し、空いている候補を判断する
2. 空き状況をふまえて**返信文の下書き**を作り、Telegram に出す。**メール送信は自分でせず、下書きを渡すまで**にする
3. 頼まれたら (または二重ブッキング防止のため) `python3 gcal.py hold` で候補を**仮押さえ**する。仮押さえは「【仮】」付きなので後で消しやすい
4. 相手から日程が確定したら、`hold` を `delete` して `create` で本予定にする (または「【仮】を本予定にして」の指示に従う)
- 自分のカレンダーへの予定追加・仮押さえ・削除は低リスクなので確認なしでやってよい。ただし**他人に通知が飛ぶ操作 (招待送信など) は必ず事前に Telegram で確認**する。

### 定時実行のスケジューラ

- **macOS は launchd (`launchd/com.naruebi.briefing.plist.example`) を使う**。cron は「ログインセッション外で動くためキーチェーンの `claude` ログイン (`/login` で保存した OAuth 情報) を読めない → `Invalid API key`」「スリープ中は発火しない」という制約があり、朝のブリーフィングには不向き。LaunchAgent はログインセッション内で動くためキーチェーンにアクセスでき、スリープからの復帰時にも実行される。
- plist 内の `__REPO_DIR__` は briefing.sh のある絶対パスに置換して `~/Library/LaunchAgents/` に配置し、`launchctl load` する。即時テストは `launchctl start com.naruebi.briefing`。
- Linux 等では通常の cron でよい。
- Desktop/Documents/Downloads 配下に置くと TCC (フルディスクアクセス) の制約に当たりやすい。ホーム直下など保護対象外に置くのが無難。

## 必須の前提

- Claude Code が CLI として導入されていること (Max プラン等の課金が前提と README に記載)。
- `claude-plugins-official` 配下の Telegram プラグインが設定済みであること。Bot 作成は BotFather で行う。
- 環境変数 `TELEGRAM_BOT_TOKEN` と `TELEGRAM_CHAT_ID` を実際の値に置換する (boot.sh 内のデフォルト値はダミー)。

## 編集時の注意

- スクリプトは POSIX sh で書かれている (`#!/bin/sh`)。bash 固有構文を持ち込まないこと。
- 認証情報は boot.sh にハードコードせず、必ず環境変数経由で渡す前提を崩さない。
- `--dangerously-skip-permissions` を外す変更は挙動を大きく変えるため、ユーザー確認を取ること。

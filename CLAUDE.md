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

## 朝のブリーフィング

```sh
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... [BRIEFING_LOCATION=Tokyo] ./briefing.sh
```

- `briefing.sh` は毎朝定時に実行する想定。`claude -p` (ヘッドレス・単発セッション、`-c` なし) で `prompts/briefing.md` の指示に従いブリーフィング文を生成し、Telegram Bot API で送信する。boot.sh の常駐セッションとは独立して動く。
- 設定値 (`TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` / `BRIEFING_LOCATION`) は同ディレクトリの `.env` から読み込む (無ければ環境変数)。`.env` は `.gitignore` 済みで、秘密情報をリポジトリや crontab/plist に書かずに済ませるための仕組み。`.env.example` が雛形。
- ブリーフィングの内容 (日付・天気・TODO・ひとこと) は `prompts/briefing.md` で定義する。出力は Telegram 1 メッセージに収まるよう 1500 文字以内・プレーンテキスト縛り。
- `memory/todo.md` は秘書の永続メモリ。ブリーフィングで読み上げるほか、Telegram での会話中に「TODO に追加して」と頼まれたらこのファイルに追記する。セッションの要約・圧縮をまたいで残したい情報はここに書く。

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

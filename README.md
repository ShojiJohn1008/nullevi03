# ナルエビちゃん三世

AI秘書っす。

## 使い方

- Claude に月200ドルとか課金する

- Telegramを頑張って入れる。Botfatherとか。

- Claude Code Channelsを頑張って設定する。

- boot.sh で起動

- あとは、死ぬほど会話とかする

- 終わり

## 朝のブリーフィング

毎朝、日付・天気・TODO をまとめて Telegram に送ってくれるやつ。

```sh
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... ./briefing.sh
```

### 設定 (.env)

トークン類は `.env` に書く (git 管理外)。crontab や plist に平文で書かずに済む。

```sh
cp .env.example .env
# .env を編集して TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID を実値にする
```

`.env` があれば `briefing.sh` が自動で読み込む。環境変数で直接渡してもよい。

### 毎朝の自動実行

**macOS は launchd を使う** (cron はキーチェーンの claude ログインを読めず、スリープ中も発火しないため)。

```sh
# __REPO_DIR__ を briefing.sh のある絶対パスに置き換えて配置
cp launchd/com.naruebi.briefing.plist.example ~/Library/LaunchAgents/com.naruebi.briefing.plist
sed -i '' "s#__REPO_DIR__#$(pwd)#g" ~/Library/LaunchAgents/com.naruebi.briefing.plist
launchctl load ~/Library/LaunchAgents/com.naruebi.briefing.plist

# 時刻を待たず即テスト
launchctl start com.naruebi.briefing
```

外すときは `launchctl unload ~/Library/LaunchAgents/com.naruebi.briefing.plist`。

**Linux は cron** でよい:

```
0 7 * * * cd /path/to/nullevi03 && ./briefing.sh >> /path/to/nullevi03/briefing.log 2>&1
```

- 天気の地域は `.env` の `BRIEFING_LOCATION` で変えられる (デフォルト Tokyo)
- ブリーフィングの中身は `prompts/briefing.md` を編集して調整する
- TODO は `memory/todo.md` に書いておくと読み上げてくれる。Telegram で「TODO に〇〇追加して」と頼んでもいい

## メール要約

特定の送信者からの新着メール (本文 + PDF/Excel/CSV 添付) を読んで、要点を毎朝 Telegram に送る。読み取り専用でメールは既読にも変更もしない。

```sh
./mail_summary.sh
```

### 準備 (Gmail 側)

1. Google アカウントで **2段階認証を ON** にする
2. [アプリパスワード](https://myaccount.google.com/apppasswords) を1つ発行する
3. `.env` に設定を追記する (`GMAIL_APP_PASSWORD` は**空白を詰めて**書く):

```
GMAIL_ADDRESS=you@gmail.com
GMAIL_APP_PASSWORD=abcdefghijklmnop
MAIL_SENDERS=boss@example.com,info@example.com
MAIL_LOOKBACK_DAYS=3
```

Excel (.xlsx) を読むには一度だけ `pip3 install pandas openpyxl` しておく (PDF/CSV は不要)。

### 自動実行 (macOS / launchd)

朝のブリーフィング (7:00) の少し後、7:05 に動かす例:

```sh
cp launchd/com.naruebi.mailsummary.plist.example ~/Library/LaunchAgents/com.naruebi.mailsummary.plist
sed -i '' "s#__REPO_DIR__#$(pwd)#g" ~/Library/LaunchAgents/com.naruebi.mailsummary.plist
launchctl load ~/Library/LaunchAgents/com.naruebi.mailsummary.plist
launchctl start com.naruebi.mailsummary   # 時刻を待たず即テスト
```

- 対象送信者は `.env` の `MAIL_SENDERS` (カンマ区切りで複数可)
- 要約のしかたは `prompts/mail_summary.md` を編集して調整する
- 一度要約したメールは `mail_state.txt` に記録され、翌朝重複して拾わない

## トラブルシューティング

- AIに聞け！俺には聞くな！！

## ライセンス

ナルエビちゃんライセンスに従うものとする。（まだない）

## 免責事項

家が燃えたとか、なんか起きても全て責任は負わないです。


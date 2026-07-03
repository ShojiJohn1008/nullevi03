#!/bin/sh
# 特定の送信者からの新着メール(本文 + PDF/Excel 添付)を要約して Telegram に送る。
# 毎朝、朝のブリーフィングの少し後に launchd/cron から実行する想定。
#
# 設定値は briefing.sh と同じ .env から読み込む:
#   TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID  (必須) Telegram 送信用
#   GMAIL_ADDRESS / GMAIL_APP_PASSWORD     (必須) Gmail IMAP ログイン用
#   MAIL_SENDERS                           (必須) 対象送信者 (カンマ区切り)
#   MAIL_LOOKBACK_DAYS                     (任意) 何日前まで遡るか (既定 3)
#
# 読み取り専用でメールを開くので、既読状態やメール本体は変更しない。

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

if [ -f .env ]; then
  . ./.env
fi

# python 子プロセスに渡すため export する
export GMAIL_ADDRESS GMAIL_APP_PASSWORD MAIL_SENDERS MAIL_LOOKBACK_DAYS

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
WORKDIR=mail_work

send_telegram() {
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=$1" \
    > /dev/null 2>&1
}

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "TELEGRAM_BOT_TOKEN と TELEGRAM_CHAT_ID を .env に設定してください" >&2
  exit 1
fi

if ! command -v python3 > /dev/null 2>&1; then
  send_telegram "🦐 メール要約に失敗…python3 が見つかりませんでした🙏"
  echo "python3 が見つかりません" >&2
  exit 1
fi

# 前回分を消してから取得
rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

if ! python3 fetch_mail.py "$WORKDIR" 2>"$WORKDIR/fetch_err.txt"; then
  send_telegram "🦐 メール取得でエラーっす🙏
$(cat "$WORKDIR/fetch_err.txt")"
  echo "fetch_mail.py が失敗しました" >&2
  exit 1
fi

count=$(cat "$WORKDIR/.count" 2>/dev/null || echo 0)
if [ "$count" = "0" ]; then
  send_telegram "🦐 今朝は対象の新着メールはありませんでした📭"
  echo "対象メールなし"
  exit 0
fi

prompt="作業ディレクトリ: ./${WORKDIR}

$(cat prompts/mail_summary.md)"

summary=$(claude -p "$prompt" --dangerously-skip-permissions 2>/dev/null)

if [ -z "$summary" ]; then
  send_telegram "🦐 メール要約の生成に失敗したっす…claude の応答が空でした🙏"
  echo "claude -p が空の応答を返しました" >&2
  exit 1
fi

if send_telegram "🦐 今朝のメール要約っす📬

${summary}"; then
  echo "メール要約を送信しました (${count} 件)"
else
  echo "Telegram への送信に失敗しました" >&2
  exit 1
fi

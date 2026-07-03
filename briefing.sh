#!/bin/sh
# 朝のブリーフィングを生成して Telegram に送信する。
# cron から毎朝実行する想定:
#   0 7 * * * cd /path/to/nullevi03 && TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... ./briefing.sh
#
# 環境変数:
#   TELEGRAM_BOT_TOKEN  (必須) BotFather で発行した Bot トークン
#   TELEGRAM_CHAT_ID    (必須) 送信先チャット ID
#   BRIEFING_LOCATION   (任意) 天気を調べる地域。デフォルト Tokyo

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
BRIEFING_LOCATION="${BRIEFING_LOCATION:-Tokyo}"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

send_telegram() {
  text="$1"
  curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    --data-urlencode "text=${text}" \
    > /dev/null 2>&1
}

if [ -z "$TELEGRAM_BOT_TOKEN" ] || [ -z "$TELEGRAM_CHAT_ID" ]; then
  echo "TELEGRAM_BOT_TOKEN と TELEGRAM_CHAT_ID を環境変数で設定してください" >&2
  exit 1
fi

if [ ! -f prompts/briefing.md ]; then
  echo "prompts/briefing.md が見つかりません" >&2
  exit 1
fi

prompt="対象地域: ${BRIEFING_LOCATION}

$(cat prompts/briefing.md)"

# boot.sh の常駐セッションとは別に、ヘッドレスで単発実行する (-c は付けない)
briefing=$(claude -p "$prompt" --dangerously-skip-permissions 2>/dev/null)

if [ -z "$briefing" ]; then
  send_telegram "🦐 朝のブリーフィング生成に失敗したっす…claude の応答が空でした🙏"
  echo "claude -p が空の応答を返しました" >&2
  exit 1
fi

if send_telegram "🦐 おはようございます!今日のブリーフィングっす🌅

${briefing}"; then
  echo "ブリーフィングを送信しました"
else
  echo "Telegram への送信に失敗しました" >&2
  exit 1
fi

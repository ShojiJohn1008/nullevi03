#!/bin/sh
# 朝のブリーフィングを生成して Telegram に送信する。
# macOS では launchd (LaunchAgent) から、Linux では cron から毎朝実行する想定。
#
# 設定値 (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID / BRIEFING_LOCATION) は
# 次のどちらかで渡す:
#   1. 同じディレクトリの .env ファイル (推奨。crontab/plist に秘密を書かずに済む)
#   2. 環境変数 (cron 行に直書きするなど)
#
# 設定値:
#   TELEGRAM_BOT_TOKEN  (必須) BotFather で発行した Bot トークン
#   TELEGRAM_CHAT_ID    (必須) 送信先チャット ID
#   BRIEFING_LOCATION   (任意) 天気を調べる地域。デフォルト Tokyo

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

# .env があれば読み込む。TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID をここに書けば
# crontab や launchd の plist に秘密情報を書かずに済む (.env は git 管理外)。
if [ -f .env ]; then
  . ./.env
fi

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
BRIEFING_LOCATION="${BRIEFING_LOCATION:-Tokyo}"

# claude の子プロセス (gcal.py) がカレンダー/ToDo を読めるよう export しておく。
# 未設定なら briefing.md 側でその項目をスキップする。
export CAL_WEBAPP_URL CAL_SHARED_SECRET CAL_EXTRA_CALENDAR_IDS CAL_WRITE_CALENDAR_ID

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

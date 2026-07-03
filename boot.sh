#!/bin/sh
# ナルエビちゃん三世: Claude Code を Telegram チャンネルに繋いで常駐させる。
#
# 初回はプラグインの設定が必要 (README「会話できる秘書 (boot.sh)」参照):
#   claude を起動して /plugin install telegram@claude-plugins-official
#   → /telegram:configure <Botトークン> → ペアリング
#
# 設定値 (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID) は同ディレクトリの .env
# から読み込む (無ければ環境変数)。起動・再起動の通知に使うほか、
# TELEGRAM_BOT_TOKEN は telegram プラグインからも参照される。

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

if [ -f .env ]; then
  . ./.env
fi

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"

# telegram プラグイン (claude の子プロセス) がトークンを読めるように export
export TELEGRAM_BOT_TOKEN

notify_telegram() {
  text="$1"
  if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
    curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d "chat_id=${TELEGRAM_CHAT_ID}" \
      --data-urlencode "text=${text}" \
      > /dev/null 2>&1 || true
  fi
}

FIRST=1
while true; do
  if [ "$FIRST" = "1" ]; then
    notify_telegram "🦐 boot.sh起動: ナルエビ三世を起動します🌅"
    FIRST=0
  else
    notify_telegram "🦐 ナルエビ三世が終了 → 5秒後に再起動します🔄"
    sleep 5
    notify_telegram "🦐 ナルエビ三世を再起動します🌅"
  fi
  claude --dangerously-skip-permissions --channels plugin:telegram@claude-plugins-official -c
  echo "ナルエビ三世が終了しました。5秒後に再起動します..."
done

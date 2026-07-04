#!/bin/sh
# 受信箱を広く見て「返信が要りそう / 日程調整」のメールを拾い、
# 日程調整なら返信の下書き + 候補の仮押さえまで用意して Telegram に送る。
# 朝のブリーフィング・メール要約の後 (例 7:10) に実行する想定。
#
# 定期通知やメルマガは、Gmail のカテゴリ分け (category:primary) で大半を自動除外する。
# 設定は .env から読む。既読のものは is:unread で自然に外れる (state ファイルは使わない)。
#
#   MAIL_TRIAGE_QUERY  (任意) Gmail 検索。既定 "category:primary is:unread newer_than:3d"

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

if [ -f .env ]; then
  . ./.env
fi

# メール接続とカレンダー操作 (gcal.py) の両方を子プロセスに渡す
export GMAIL_ADDRESS GMAIL_APP_PASSWORD MAIL_SENDERS MAIL_LOOKBACK_DAYS
export MAIL_ACCOUNT_1_ADDRESS MAIL_ACCOUNT_1_PASSWORD MAIL_ACCOUNT_1_HOST
export MAIL_ACCOUNT_2_ADDRESS MAIL_ACCOUNT_2_PASSWORD MAIL_ACCOUNT_2_HOST
export CAL_WEBAPP_URL CAL_SHARED_SECRET CAL_EXTRA_CALENDAR_IDS CAL_WRITE_CALENDAR_ID

TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
QUERY="${MAIL_TRIAGE_QUERY:-category:primary is:unread newer_than:3d}"
WORKDIR=triage_work

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
  echo "python3 が見つかりません" >&2
  exit 1
fi

rm -rf "$WORKDIR"
mkdir -p "$WORKDIR"

# --state "" で重複記録を無効化 (未読フィルタが自然な重複除けになる)
if ! python3 fetch_mail.py "$WORKDIR" --gmail-query "$QUERY" --state "" 2>"$WORKDIR/fetch_err.txt"; then
  send_telegram "🦐 トリアージのメール取得でエラーっす🙏
$(cat "$WORKDIR/fetch_err.txt")"
  echo "fetch_mail.py が失敗しました" >&2
  exit 1
fi

count=$(cat "$WORKDIR/.count" 2>/dev/null || echo 0)
if [ "$count" = "0" ]; then
  echo "トリアージ対象なし (静かに終了)"
  exit 0
fi

prompt="作業ディレクトリ: ./${WORKDIR}

$(cat prompts/triage.md)"

report=$(claude -p "$prompt" --dangerously-skip-permissions 2>/dev/null)

# 対応が必要なメールが無ければ claude は NONE を返す約束。その場合は通知しない。
trimmed=$(printf '%s' "$report" | tr -d '[:space:]')
if [ -z "$trimmed" ] || [ "$trimmed" = "NONE" ]; then
  echo "対応が必要なメールなし (通知せず終了)"
  exit 0
fi

if send_telegram "🦐 返信が要りそうなメールっす📨

${report}"; then
  echo "トリアージ結果を送信しました"
else
  echo "Telegram への送信に失敗しました" >&2
  exit 1
fi

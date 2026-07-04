#!/usr/bin/env python3
"""Google カレンダーを Apps Script 橋渡し (gas/Calendar.gs) 経由で読み書きする CLI。

.env の CAL_WEBAPP_URL (公開したウェブアプリの /exec URL) と
CAL_SHARED_SECRET (Apps Script 側に設定した合言葉) を使う。標準ライブラリのみ。

使い方:
  gcal.py calendars                           # 見えているカレンダー一覧 (共有含む。ID 調べ用)
  gcal.py list   <開始> [終了]                # 期間の予定一覧 (空き確認用)。終了省略時は開始日1日分
  gcal.py hold   <タイトル> <開始> <終了> [説明]  # 仮押さえ (【仮】+ 灰色)
  gcal.py create <タイトル> <開始> <終了> [説明]  # 通常の予定
  gcal.py delete <イベントID>

日時は ISO 形式 (例 "2026-07-10T10:00" や "2026-07-10T10:00:00+09:00")。
list の日付だけ指定 (例 "2026-07-10") はその日の 00:00〜翌 00:00 として扱う。

共有カレンダーも一緒に見たいとき:
  1. `gcal.py calendars` でカレンダーの ID を調べる
  2. .env の CAL_EXTRA_CALENDAR_IDS に、そのIDをカンマ区切りで書く
  list はメイン + それらを合算して返す。
書き込み先を共有カレンダーにしたいときは .env の CAL_WRITE_CALENDAR_ID にID を入れる。
"""

import json
import os
import sys
import urllib.request


def call(payload):
    url = os.environ.get("CAL_WEBAPP_URL", "").strip()
    secret = os.environ.get("CAL_SHARED_SECRET", "").strip()
    if not url or not secret:
        sys.stderr.write(
            "CAL_WEBAPP_URL と CAL_SHARED_SECRET を .env に設定してください\n")
        sys.exit(1)
    payload["secret"] = secret
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"})
    # Apps Script は POST に 302 を返し googleusercontent.com へ誘導する。
    # urllib は既定でこのリダイレクトを追って本文を取得する。
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def day_bounds(s):
    """"2026-07-10" のような日付だけの指定を 1 日分の範囲に広げる。"""
    if len(s) == 10 and s.count("-") == 2:
        return s + "T00:00:00", s + "T23:59:59"
    return s, None


def main():
    if len(sys.argv) < 2:
        sys.stderr.write(__doc__)
        sys.exit(1)
    action = sys.argv[1]
    args = sys.argv[2:]

    if action == "calendars":
        result = call({"action": "calendars"})
    elif action == "list":
        if not args:
            sys.stderr.write("開始日を指定してください\n")
            sys.exit(1)
        start, auto_end = day_bounds(args[0])
        end = args[1] if len(args) > 1 else (auto_end or start)
        extra = [c.strip() for c in
                 os.environ.get("CAL_EXTRA_CALENDAR_IDS", "").split(",") if c.strip()]
        payload = {"action": "list", "start": start, "end": end}
        if extra:
            payload["calendarIds"] = extra
        result = call(payload)
    elif action in ("hold", "create"):
        if len(args) < 3:
            sys.stderr.write("タイトル・開始・終了を指定してください\n")
            sys.exit(1)
        payload = {
            "action": action,
            "title": args[0],
            "start": args[1],
            "end": args[2],
            "description": args[3] if len(args) > 3 else "",
        }
        write_cal = os.environ.get("CAL_WRITE_CALENDAR_ID", "").strip()
        if write_cal:
            payload["calendarId"] = write_cal
        result = call(payload)
    elif action == "delete":
        if not args:
            sys.stderr.write("イベントIDを指定してください\n")
            sys.exit(1)
        result = call({"action": "delete", "id": args[0]})
    else:
        sys.stderr.write("不明なコマンド: %s\n" % action)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()

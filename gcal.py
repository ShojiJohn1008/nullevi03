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
  gcal.py tasks                               # Google ToDo (未完了) の一覧
  gcal.py addtask <タイトル> [期限] [メモ]      # Google ToDo に追加 (期限は 2026-07-10 形式)
  gcal.py donetask <タスクID>                  # ToDo を完了にする

日時は ISO 形式 (例 "2026-07-10T10:00" や "2026-07-10T10:00:00+09:00")。
list の日付だけ指定 (例 "2026-07-10") はその日の 00:00〜翌 00:00 として扱う。

共有カレンダーも一緒に見たいとき:
  1. `gcal.py calendars` でカレンダーの ID を調べる
  2. .env の CAL_EXTRA_CALENDAR_IDS に、そのIDをカンマ区切りで書く
  list はメイン + それらを合算して返す。

予定ごとに書き込み先を選ぶ (hold / create / delete):
  --cal <名前 or ID> を付けると、その回だけ書き込み先を変えられる。
  例) gcal.py create "定例MTG" 2026-07-10T10:00 2026-07-10T11:00 --cal チーム
      gcal.py hold   "打合せ"  2026-07-10T14:00 2026-07-10T15:00           # 個人 (既定)
  名前は `gcal.py calendars` の名前と照合する。ID (@ を含む) はそのまま使う。
  --cal 省略時は .env の CAL_WRITE_CALENDAR_ID があればそこ、無ければ個人カレンダー。
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


def pop_cal_flag(args):
    """args から --cal <値> / --cal=<値> を取り出し、(残りの args, 値) を返す。"""
    cal = None
    rest = []
    i = 0
    while i < len(args):
        if args[i] == "--cal" and i + 1 < len(args):
            cal = args[i + 1]
            i += 2
            continue
        if args[i].startswith("--cal="):
            cal = args[i][len("--cal="):]
            i += 1
            continue
        rest.append(args[i])
        i += 1
    return rest, cal


def resolve_calendar(value):
    """--cal の値をカレンダーIDに解決する。@ を含めばID、なければ名前で照合。"""
    if not value:
        return None
    if "@" in value:
        return value
    result = call({"action": "calendars"})
    cals = result.get("calendars", [])
    for c in cals:                       # 完全一致を優先
        if c.get("name") == value:
            return c["id"]
    for c in cals:                       # 次に部分一致
        if value in c.get("name", ""):
            return c["id"]
    names = ", ".join(c.get("name", "") for c in cals)
    sys.stderr.write(
        "カレンダー '%s' が見つかりません。候補: %s\n" % (value, names))
    sys.exit(1)


def target_calendar(cal_flag):
    """--cal 指定を優先し、無ければ .env の CAL_WRITE_CALENDAR_ID を使う。"""
    if cal_flag:
        return resolve_calendar(cal_flag)
    return os.environ.get("CAL_WRITE_CALENDAR_ID", "").strip() or None


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
    args, cal_flag = pop_cal_flag(sys.argv[2:])

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
        write_cal = target_calendar(cal_flag)
        if write_cal:
            payload["calendarId"] = write_cal
        result = call(payload)
    elif action == "delete":
        if not args:
            sys.stderr.write("イベントIDを指定してください\n")
            sys.exit(1)
        payload = {"action": "delete", "id": args[0]}
        del_cal = target_calendar(cal_flag)
        if del_cal:
            payload["calendarId"] = del_cal
        result = call(payload)
    elif action == "tasks":
        result = call({"action": "tasks"})
    elif action == "addtask":
        if not args:
            sys.stderr.write("タスクのタイトルを指定してください\n")
            sys.exit(1)
        payload = {"action": "addtask", "title": args[0]}
        if len(args) > 1:
            payload["due"] = args[1]
        if len(args) > 2:
            payload["notes"] = args[2]
        result = call(payload)
    elif action == "donetask":
        if not args:
            sys.stderr.write("タスクIDを指定してください\n")
            sys.exit(1)
        result = call({"action": "donetask", "id": args[0]})
    else:
        sys.stderr.write("不明なコマンド: %s\n" % action)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()

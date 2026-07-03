#!/usr/bin/env python3
"""特定の送信者からの新着メールと添付ファイルを取得して作業ディレクトリに保存する。

Gmail に IMAP + アプリパスワードで接続する (標準ライブラリのみ、pip 不要)。
メールは読み取り専用で開くので、既読状態やメール自体を変更しない。

環境変数 (briefing と同じ .env から渡す想定):
  GMAIL_ADDRESS         Gmail アドレス (例 you@gmail.com)          [必須]
  GMAIL_APP_PASSWORD    アプリパスワード (16桁。空白は自動で除去)   [必須]
  MAIL_SENDERS          対象送信者。カンマ区切りで複数可           [必須]
  MAIL_LOOKBACK_DAYS    何日前まで遡るか (既定 3)                   [任意]

使い方:
  python3 fetch_mail.py [作業ディレクトリ]   # 既定は ./mail_work

一度要約したメールを翌朝また拾わないよう、処理済みの Message-ID を
mail_state.txt に記録して重複を防ぐ。
"""

import email
import email.header
import imaplib
import os
import re
import sys
from datetime import datetime, timedelta

IMAP_HOST = "imap.gmail.com"
STATE_FILE = "mail_state.txt"
MAX_BODY_CHARS = 6000
ATTACH_EXTS = (".pdf", ".csv", ".xls", ".xlsx", ".txt", ".tsv")
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def die(msg):
    sys.stderr.write(msg + "\n")
    sys.exit(1)


def decode_mime(value):
    """MIME エンコードされたヘッダ/ファイル名を可読文字列にする。"""
    if not value:
        return ""
    parts = []
    for text, enc in email.header.decode_header(value):
        if isinstance(text, bytes):
            try:
                parts.append(text.decode(enc or "utf-8", "replace"))
            except (LookupError, TypeError):
                parts.append(text.decode("utf-8", "replace"))
        else:
            parts.append(text)
    return "".join(parts)


def safe_name(name):
    """ファイル名からパス区切りや危険な文字を除いて安全にする。"""
    name = os.path.basename(name.replace("\\", "/"))
    name = re.sub(r"[^\w.\- ぁ-んァ-ン一-龥]", "_", name)
    return name.strip() or "attachment"


def extract_body(msg):
    """text/plain を優先して本文を取り出す。無ければ簡易に HTML を除去。"""
    plain, html = "", ""
    for part in msg.walk():
        if part.is_multipart():
            continue
        ctype = part.get_content_type()
        disp = str(part.get("Content-Disposition") or "")
        if "attachment" in disp.lower():
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        charset = part.get_content_charset() or "utf-8"
        try:
            text = payload.decode(charset, "replace")
        except LookupError:
            text = payload.decode("utf-8", "replace")
        if ctype == "text/plain":
            plain += text
        elif ctype == "text/html":
            html += text
    body = plain if plain.strip() else re.sub(r"<[^>]+>", " ", html)
    body = re.sub(r"[ \t]+\n", "\n", body).strip()
    return body[:MAX_BODY_CHARS]


def load_seen():
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}


def append_seen(ids):
    if not ids:
        return
    with open(STATE_FILE, "a", encoding="utf-8") as f:
        for mid in ids:
            f.write(mid + "\n")


def main():
    workdir = sys.argv[1] if len(sys.argv) > 1 else "mail_work"

    address = os.environ.get("GMAIL_ADDRESS", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    senders_raw = os.environ.get("MAIL_SENDERS", "")
    senders = [s.strip() for s in senders_raw.split(",") if s.strip()]
    try:
        lookback = int(os.environ.get("MAIL_LOOKBACK_DAYS", "3"))
    except ValueError:
        lookback = 3

    if not address or not password:
        die("GMAIL_ADDRESS と GMAIL_APP_PASSWORD を設定してください")
    if not senders:
        die("MAIL_SENDERS に対象の送信者アドレスを設定してください")

    since = datetime.now() - timedelta(days=lookback)
    since_str = "%02d-%s-%d" % (since.day, MONTHS[since.month - 1], since.year)

    seen = load_seen()
    new_ids = []
    saved = 0
    index_lines = []

    try:
        imap = imaplib.IMAP4_SSL(IMAP_HOST)
        imap.login(address, password)
    except imaplib.IMAP4.error as e:
        die("Gmail への IMAP ログインに失敗しました: %s\n"
            "2段階認証を有効にし、アプリパスワードを使っているか確認してください。" % e)

    # readonly=True で開くので既読フラグを変更しない
    imap.select("INBOX", readonly=True)

    for sender in senders:
        typ, data = imap.search(None, '(FROM "%s" SINCE %s)' % (sender, since_str))
        if typ != "OK" or not data or not data[0]:
            continue
        for num in data[0].split():
            typ, msgdata = imap.fetch(num, "(RFC822)")
            if typ != "OK" or not msgdata or not msgdata[0]:
                continue
            msg = email.message_from_bytes(msgdata[0][1])

            mid = (msg.get("Message-ID") or "").strip()
            if mid and mid in seen:
                continue
            if mid:
                new_ids.append(mid)

            saved += 1
            folder = os.path.join(workdir, "%03d" % saved)
            attach_dir = os.path.join(folder, "attachments")
            os.makedirs(attach_dir, exist_ok=True)

            subject = decode_mime(msg.get("Subject")) or "(件名なし)"
            frm = decode_mime(msg.get("From"))
            date = msg.get("Date", "")

            with open(os.path.join(folder, "meta.txt"), "w", encoding="utf-8") as f:
                f.write("From: %s\nSubject: %s\nDate: %s\n" % (frm, subject, date))
            with open(os.path.join(folder, "body.txt"), "w", encoding="utf-8") as f:
                f.write(extract_body(msg))

            attaches = []
            for part in msg.walk():
                fname = part.get_filename()
                if not fname:
                    continue
                fname = safe_name(decode_mime(fname))
                if not fname.lower().endswith(ATTACH_EXTS):
                    continue
                payload = part.get_payload(decode=True)
                if payload is None:
                    continue
                with open(os.path.join(attach_dir, fname), "wb") as f:
                    f.write(payload)
                attaches.append(fname)

            index_lines.append(
                "- %03d/ | From: %s | 件名: %s | 添付: %s"
                % (saved, frm, subject, ", ".join(attaches) if attaches else "なし")
            )

    imap.logout()

    os.makedirs(workdir, exist_ok=True)
    with open(os.path.join(workdir, "index.md"), "w", encoding="utf-8") as f:
        f.write("# 取得したメール一覧\n\n")
        f.write("\n".join(index_lines) if index_lines else "(対象メールなし)")
        f.write("\n")
    with open(os.path.join(workdir, ".count"), "w", encoding="utf-8") as f:
        f.write(str(saved))

    append_seen(new_ids)
    sys.stderr.write("取得: %d 件\n" % saved)


if __name__ == "__main__":
    main()

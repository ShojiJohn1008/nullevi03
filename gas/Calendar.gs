/**
 * ナルエビちゃん三世 — Google カレンダー橋渡し (Apps Script ウェブアプリ)
 *
 * 自分の Google アカウント上でこのスクリプトを「ウェブアプリ」として公開し、
 * ローカルの gcal.py から HTTPS POST で叩いてカレンダーを読み書きする。
 * Google Cloud の OAuth 設定は不要 (Apps Script が自分の権限で動く)。
 *
 * 導入手順は gas/README.md を参照。合言葉はコードに書かず、
 * プロジェクト設定 > スクリプトプロパティ の SHARED_SECRET に入れる。
 *
 * 対応アクション (POST の JSON body の "action"):
 *   list   … 指定期間の予定一覧 (空き確認用)   {start, end}
 *   hold   … 仮押さえを作成 (【仮】+ 灰色)      {title, start, end, description?}
 *   create … 通常の予定を作成                    {title, start, end, description?}
 *   delete … 予定を ID で削除                    {id}
 * start / end は ISO 文字列 (例 "2026-07-10T10:00:00+09:00" や "2026-07-10T10:00")。
 */

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var secret = PropertiesService.getScriptProperties().getProperty('SHARED_SECRET');
    if (!secret || body.secret !== secret) {
      return json({ ok: false, error: 'unauthorized' });
    }

    var cal = CalendarApp.getDefaultCalendar();
    switch (body.action) {
      case 'list':   return json(listEvents(cal, body));
      case 'hold':   return json(createEvent(cal, body, true));
      case 'create': return json(createEvent(cal, body, false));
      case 'delete': return json(deleteEvent(cal, body));
      default:       return json({ ok: false, error: 'unknown action: ' + body.action });
    }
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

// ブラウザで /exec を開いたときの生存確認用
function doGet() {
  return json({ ok: true, msg: 'naruebi calendar bridge alive' });
}

function listEvents(cal, body) {
  var events = cal.getEvents(new Date(body.start), new Date(body.end));
  var items = events.map(function (ev) {
    return {
      id: ev.getId(),
      title: ev.getTitle(),
      start: ev.getStartTime().toISOString(),
      end: ev.getEndTime().toISOString(),
      allDay: ev.isAllDayEvent()
    };
  });
  return { ok: true, count: items.length, events: items };
}

function createEvent(cal, body, tentative) {
  if (!body.start || !body.end) {
    return { ok: false, error: 'start と end が必要です' };
  }
  var title = body.title || '(無題)';
  if (tentative) { title = '【仮】' + title; }

  var ev = cal.createEvent(
    title,
    new Date(body.start),
    new Date(body.end),
    { description: body.description || '' }
  );
  if (tentative) {
    ev.setColor(CalendarApp.EventColor.GRAY);   // 仮押さえは灰色で一目で分かるように
    ev.setMyStatus(CalendarApp.GuestStatus.MAYBE);
  }
  return {
    ok: true,
    id: ev.getId(),
    title: ev.getTitle(),
    start: ev.getStartTime().toISOString(),
    end: ev.getEndTime().toISOString()
  };
}

function deleteEvent(cal, body) {
  var ev = cal.getEventById(body.id);
  if (!ev) { return { ok: false, error: 'event not found: ' + body.id }; }
  var title = ev.getTitle();
  ev.deleteEvent();
  return { ok: true, deleted: title };
}

function json(obj) {
  return ContentService
    .createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

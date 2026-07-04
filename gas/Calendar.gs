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
 *   calendars … 見えているカレンダーの一覧 (ID を調べる用)
 *   list      … 指定期間の予定一覧 (空き確認用)
 *               {start, end, calendarIds?}  calendarIds は共有カレンダー等の追加ID配列
 *   hold      … 仮押さえを作成 (【仮】+ 灰色)  {title, start, end, description?, calendarId?}
 *   create    … 通常の予定を作成              {title, start, end, description?, calendarId?}
 *   delete    … 予定を ID で削除              {id, calendarId?}
 * start / end は ISO 文字列 (例 "2026-07-10T10:00:00+09:00" や "2026-07-10T10:00")。
 */

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    var secret = PropertiesService.getScriptProperties().getProperty('SHARED_SECRET');
    if (!secret || body.secret !== secret) {
      return json({ ok: false, error: 'unauthorized' });
    }

    switch (body.action) {
      case 'calendars': return json(listCalendars());
      case 'list':      return json(listEvents(body));
      case 'hold':      return json(createEvent(body, true));
      case 'create':    return json(createEvent(body, false));
      case 'delete':    return json(deleteEvent(body));
      default:          return json({ ok: false, error: 'unknown action: ' + body.action });
    }
  } catch (err) {
    return json({ ok: false, error: String(err) });
  }
}

// ブラウザで /exec を開いたときの生存確認用
function doGet() {
  return json({ ok: true, msg: 'naruebi calendar bridge alive' });
}

// アクセスできる全カレンダーの一覧 (共有・購読を含む)。ID を調べるのに使う。
function listCalendars() {
  var items = CalendarApp.getAllCalendars().map(function (c) {
    return { id: c.getId(), name: c.getName(), owned: c.isOwnedByMe() };
  });
  return { ok: true, count: items.length, calendars: items };
}

// メインカレンダー + calendarIds で指定した追加カレンダーの予定を合算して返す
function listEvents(body) {
  var cals = [CalendarApp.getDefaultCalendar()];
  var missing = [];
  (body.calendarIds || []).forEach(function (id) {
    var c = CalendarApp.getCalendarById(id);
    if (c) { cals.push(c); } else { missing.push(id); }
  });

  var start = new Date(body.start);
  var end = new Date(body.end);
  var seen = {};
  var items = [];
  cals.forEach(function (c) {
    c.getEvents(start, end).forEach(function (ev) {
      var id = ev.getId();
      if (seen[id]) { return; }   // 複数カレンダーに同じ予定があっても1回だけ
      seen[id] = true;
      items.push({
        id: id,
        calendar: c.getName(),
        title: ev.getTitle(),
        start: ev.getStartTime().toISOString(),
        end: ev.getEndTime().toISOString(),
        allDay: ev.isAllDayEvent()
      });
    });
  });
  items.sort(function (a, b) { return a.start < b.start ? -1 : (a.start > b.start ? 1 : 0); });

  var result = { ok: true, count: items.length, events: items };
  if (missing.length) { result.missing = missing; }   // 見つからなかった指定ID
  return result;
}

function createEvent(body, tentative) {
  if (!body.start || !body.end) {
    return { ok: false, error: 'start と end が必要です' };
  }
  var cal = body.calendarId
    ? CalendarApp.getCalendarById(body.calendarId)
    : CalendarApp.getDefaultCalendar();
  if (!cal) { return { ok: false, error: 'calendar not found: ' + body.calendarId }; }

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
    calendar: cal.getName(),
    title: ev.getTitle(),
    start: ev.getStartTime().toISOString(),
    end: ev.getEndTime().toISOString()
  };
}

function deleteEvent(body) {
  var cal = body.calendarId
    ? CalendarApp.getCalendarById(body.calendarId)
    : CalendarApp.getDefaultCalendar();
  if (!cal) { return { ok: false, error: 'calendar not found: ' + body.calendarId }; }
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

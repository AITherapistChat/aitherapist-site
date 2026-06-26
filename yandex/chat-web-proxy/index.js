// =====================================================================
// chat-web-proxy — Yandex Cloud Function: прокси для ВЕБ-версии AI Therapist.
//
// Зачем: в РФ прямой доступ браузера к *.functions.supabase.co нестабилен.
// Эта функция (на functions.yandexcloud.net, доступном в РФ) форвардит
// запросы фронта на наши веб-эндпоинты Supabase.
//
// Отличия от прокси приложения (chat-tuned-proxy):
//  • CORS + обработка preflight OPTIONS (нужно браузеру);
//  • отдаёт наружу X-Remaining / X-Plan-Until (для плашки статуса);
//  • whitelist: только chat-web / vk-auth / pay-web (никакого chat-tuned);
//  • анон-ключ не нужен (веб-функции verify_jwt=false);
//  • для /chat-web принудительно stream:false (прокси буферизует ответ —
//    SSE через него не идёт; фронт «фейк-печатает» по символам).
//
// Вызов из фронта:
//   https://functions.yandexcloud.net/<ID>?t=<encodeURIComponent(targetUrl)>
//   где targetUrl = https://efniwpfjdfktfczgdpxm.functions.supabase.co/chat-web
// =====================================================================
var https = require('https');

var ALLOW_ORIGIN   = 'https://aitherapist.ru';
var ALLOWED_HOST   = 'efniwpfjdfktfczgdpxm.functions.supabase.co';
var ALLOWED_PATHS  = ['/chat-web', '/vk-auth', '/pay-web'];

function corsHeaders() {
  return {
    'Access-Control-Allow-Origin': ALLOW_ORIGIN,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'content-type',
    'Access-Control-Expose-Headers': 'X-Remaining, X-Plan-Until',
    'Vary': 'Origin'
  };
}
function json(statusCode, obj) {
  var h = corsHeaders();
  h['Content-Type'] = 'application/json; charset=utf-8';
  return { statusCode: statusCode, headers: h, body: JSON.stringify(obj) };
}

function proxyRequest(hostname, path, method, headers, body) {
  return new Promise(function (resolve) {
    var opts = { hostname: hostname, path: path, method: method, headers: headers };
    if (body) opts.headers['Content-Length'] = String(Buffer.byteLength(body));
    var req = https.request(opts, function (res) {
      var chunks = [];
      res.on('data', function (c) { chunks.push(c); });
      res.on('end', function () {
        var data = Buffer.concat(chunks).toString('utf-8');
        var h = corsHeaders();
        if (res.headers['content-type']) h['Content-Type'] = res.headers['content-type'];
        if (res.headers['x-remaining'])   h['X-Remaining']  = res.headers['x-remaining'];
        if (res.headers['x-plan-until'])  h['X-Plan-Until'] = res.headers['x-plan-until'];
        resolve({ statusCode: res.statusCode, headers: h, body: data });
      });
    });
    req.on('error', function (e) {
      resolve(json(502, { error: 'proxy_error', reason: e.message }));
    });
    if (body) req.write(body);
    req.end();
  });
}

module.exports.handler = function (event) {
  var method = (event.httpMethod || 'POST').toUpperCase();

  // CORS preflight
  if (method === 'OPTIONS') {
    return Promise.resolve({ statusCode: 204, headers: corsHeaders(), body: '' });
  }

  // тело
  var rawBody = event.body || '';
  if (event.isBase64Encoded && rawBody) {
    rawBody = Buffer.from(rawBody, 'base64').toString('utf-8');
  }

  // целевой URL из ?t=
  var queryParams = event.queryStringParameters || {};
  var targetUrl = queryParams.t || null;
  if (!targetUrl) return Promise.resolve(json(400, { error: 'missing_target', hint: 'pass ?t=<url>' }));

  var parsed;
  try { parsed = new URL(decodeURIComponent(targetUrl)); }
  catch (e) { return Promise.resolve(json(400, { error: 'invalid_url' })); }

  // whitelist: только наши веб-эндпоинты
  if (parsed.hostname !== ALLOWED_HOST || ALLOWED_PATHS.indexOf(parsed.pathname) === -1) {
    return Promise.resolve(json(403, { error: 'target_not_allowed' }));
  }

  var body = (method !== 'GET' && rawBody) ? rawBody : null;

  // /chat-web: принудительно non-streaming (прокси не отдаёт SSE)
  if (body && parsed.pathname === '/chat-web') {
    try { var o = JSON.parse(body); o.stream = false; body = JSON.stringify(o); } catch (_) {}
  }

  var headers = { 'Content-Type': 'application/json', 'Accept-Encoding': 'identity' };
  // пробрасываем Origin (на всякий случай — для серверной логики апстрима)
  var inHeaders = event.headers || {};
  var origin = inHeaders['origin'] || inHeaders['Origin'];
  if (origin) headers['Origin'] = origin;

  return proxyRequest(parsed.hostname, parsed.pathname + parsed.search, method, headers, body);
};

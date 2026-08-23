# -*- coding: utf-8 -*-
"""Публикует в телеграм-канал посты, у которых наступило время.

Запускается по расписанию из .github/workflows/telegram.yml, но так же работает
и локально. Что уже опубликовано — помнит `posted.json`, поэтому повторный
запуск ничего не задваивает, а пропущенный запуск ничего не теряет.

Ключи:
  переменные окружения TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID (так в GitHub Actions),
  либо локальный файл — токен первой строкой, @канал второй:
  C:\\Users\\XE\\Desktop\\gpt\\сайт\\вк доступ группа\\телеграм бот.txt

⚠️ Адрес картинки — raw.githubusercontent.com, а не aitherapist.ru. Это не описка:
серверы Телеграма не могут скачать с нашего домена ничего — ни картинку, ни страницу
(проверено 23.08.2026: википедия превью получает, любой адрес на aitherapist.ru — нет,
а sendPhoto по такому URL отвечает 400). Похоже на фильтрацию между Телеграмом
и Yandex CDN. Именно из-за этого пост stress-rabota 23.08.2026 вышел без картинки,
а пост про прокрастинацию 22.08.2026 — с картинкой главной страницы: og.png у Телеграма
давно лежала в кэше, а свежие файлы он взять не смог.

⚠️ Перед отправкой адрес картинки проверяется. Нет файла — пост не уходит вовсе
и ждёт следующего запуска крона, а в лог уходит ошибка. Тихо подставленная
чужая картинка хуже, чем пост на несколько часов позже.
"""
import os, re, sys, json, datetime, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEDULE = os.path.join(HERE, 'schedule.json')
POSTED = os.path.join(HERE, 'posted.json')
LOCAL_KEYS = r'C:\Users\XE\Desktop\gpt\сайт\TG бот\токен.txt'
MSK = datetime.timedelta(hours=3)

# тем же юзер-агентом за картинкой пойдёт и сам Телеграм
UA = 'TelegramBot (like TwitterBot)'


def keys():
    tok = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    if tok and chat:
        return tok.strip(), chat.strip()
    with open(LOCAL_KEYS, encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    # во второй строке лежит ссылка на канал — Телеграму нужен из неё @username
    chat = lines[1]
    m = re.search(r'(?:t\.me/|^@?)([A-Za-z0-9_]{4,})/?$', chat)
    if m:
        chat = '@' + m.group(1)
    return lines[0], chat


def api(token, method, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        'https://api.telegram.org/bot%s/%s' % (token, method),
        data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode('utf-8'))


def image_ok(url):
    """Лежит ли картинка на месте. Иначе Телеграм покажет чужую."""
    try:
        req = urllib.request.Request(url, method='HEAD', headers={'User-Agent': UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200 and r.headers.get('Content-Type', '').startswith('image/')
    except Exception as e:
        print('   картинка недоступна:', e)
        return False


def load(path, default):
    if not os.path.exists(path):
        return default
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    dry = '--dry-run' in sys.argv
    token, chat = ('', '') if dry else keys()
    schedule = load(SCHEDULE, [])
    posted = load(POSTED, [])
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None) + MSK

    due = []
    for item in schedule:
        if item['id'] in posted:
            continue
        when = datetime.datetime.strptime(item['when'], '%Y-%m-%d %H:%M')
        if when <= now:
            due.append(item)

    print('сейчас (МСК):', now.strftime('%Y-%m-%d %H:%M'),
          '| в плане:', len(schedule), '| опубликовано ранее:', len(posted),
          '| к публикации:', len(due))

    failed = []
    for item in due:
        # без картинки не публикуем вовсе — пост подождёт следующего запуска
        if not image_ok(item['image']):
            print('  ПРОПУСК, картинки нет на сайте:', item['id'], item['image'])
            failed.append(item['id'])
            continue
        if dry:
            print('  [dry-run]', item['id'])
            continue
        r = api(token, 'sendMessage', {
            'chat_id': chat,
            'text': item['html'],
            'parse_mode': 'HTML',
            'link_preview_options': {
                'url': item['image'],
                'prefer_large_media': True,
                'show_above_text': True,
            },
        })
        if r.get('ok'):
            posted.append(item['id'])
            print('  опубликовано:', item['id'])
        else:
            print('  ОШИБКА:', item['id'], json.dumps(r, ensure_ascii=False)[:200])

    if not dry and due:
        with open(POSTED, 'w', encoding='utf-8') as f:
            json.dump(posted, f, ensure_ascii=False, indent=1)

    # падаем только после того, как записано опубликованное, иначе отметка потеряется
    # и следующий запуск задвоит то, что уже ушло
    if failed:
        print('::error::телеграм: не опубликовано %d — %s' % (len(failed), ', '.join(failed)))
        sys.exit(1)


if __name__ == '__main__':
    main()

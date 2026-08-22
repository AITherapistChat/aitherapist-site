# -*- coding: utf-8 -*-
"""Публикует в телеграм-канал посты, у которых наступило время.

Запускается по расписанию из .github/workflows/telegram.yml, но так же работает
и локально. Что уже опубликовано — помнит `posted.json`, поэтому повторный
запуск ничего не задваивает, а пропущенный запуск ничего не теряет.

Ключи:
  переменные окружения TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID (так в GitHub Actions),
  либо локальный файл — токен первой строкой, @канал второй:
  C:\\Users\\XE\\Desktop\\gpt\\сайт\\вк доступ группа\\телеграм бот.txt
"""
import os, sys, json, datetime, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEDULE = os.path.join(HERE, 'schedule.json')
POSTED = os.path.join(HERE, 'posted.json')
LOCAL_KEYS = r'C:\Users\XE\Desktop\gpt\сайт\TG бот\токен.txt'
MSK = datetime.timedelta(hours=3)


def keys():
    tok = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat = os.environ.get('TELEGRAM_CHAT_ID')
    if tok and chat:
        return tok.strip(), chat.strip()
    with open(LOCAL_KEYS, encoding='utf-8') as f:
        lines = [l.strip() for l in f if l.strip()]
    return lines[0], lines[1]


def api(token, method, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        'https://api.telegram.org/bot%s/%s' % (token, method),
        data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode('utf-8'))


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

    for item in due:
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


if __name__ == '__main__':
    main()

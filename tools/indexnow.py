# -*- coding: utf-8 -*-
"""Сообщает Яндексу через IndexNow, что страницы сайта появились или изменились.

Обходной путь, пока в Вебмастере не работает переобход (после сбоя Яндекса
в октябре 2026), и заодно без его дневного лимита. IndexNow только зовёт
робота: на ранжирование не влияет и в индекс в обход проверок не пускает.

Ключ лежит в корне сайта файлом <ключ>.txt — Яндекс скачивает его и так
убеждается, что запрос шлёт владелец. Ключ публичный по замыслу, это не пароль.
Не удалять файл и не менять ключ без нужды: старые запросы перестанут проверяться.

Запуск — ПОСЛЕ пуша, когда страницы уже отдаются с прода:
  python tools/indexnow.py blog/emotsionalnyy-intellekt.html index.html
  python tools/indexnow.py https://aitherapist.ru/blog/
Слать только новое и изменённое: одни и те же адреса по сто раз в день
Яндекс сочтёт спамом и начнёт игнорировать.

Google IndexNow не поддерживает — там только sitemap и «Запросить индексирование»
в Search Console.
"""
import os, sys, glob, json, urllib.request, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOST = 'aitherapist.ru'
ENDPOINT = 'https://yandex.com/indexnow'


def find_key():
    for p in glob.glob(os.path.join(ROOT, '*.txt')):
        name = os.path.basename(p)[:-4]
        if len(name) == 32 and all(c in '0123456789abcdef' for c in name):
            with open(p, encoding='utf-8') as f:
                if f.read().strip() == name:
                    return name
    sys.exit('Не найден файл ключа <32 hex>.txt в корне сайта')


def to_url(arg):
    if arg.startswith('http'):
        return arg
    path = arg.replace('\\', '/').lstrip('/')
    if path in ('', 'index.html'):
        return 'https://%s/' % HOST
    if path.endswith('/index.html'):
        path = path[:-len('index.html')]
    return 'https://%s/%s' % (HOST, path)


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    key = find_key()
    urls = [to_url(a) for a in args]
    body = json.dumps({
        'host': HOST,
        'key': key,
        'keyLocation': 'https://%s/%s.txt' % (HOST, key),
        'urlList': urls,
    }).encode('utf-8')
    req = urllib.request.Request(ENDPOINT, data=body,
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            code, text = r.status, r.read().decode('utf-8', 'replace')
    except urllib.error.HTTPError as e:
        code, text = e.code, e.read().decode('utf-8', 'replace')
    for u in urls:
        print('  ' + u)
    # 200 и 202 — приняли; 403 — ключ не совпал с файлом на сайте; 422 — адрес не с нашего хоста
    print('IndexNow: HTTP %s %s' % (code, text.strip()[:300]))
    sys.exit(0 if code in (200, 202) else 1)


if __name__ == '__main__':
    main()

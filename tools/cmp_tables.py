# -*- coding: utf-8 -*-
"""Готовит таблицы .cmp к показу на телефоне.

На узком экране таблица в 3–4 колонки не помещается: раньше она листалась вбок,
но это ничем не было видно — читатель видел обрезанный текст (13.09.2026, скриншот
пользователя на статье о послеродовой депрессии). Теперь ниже 700px каждая строка
показывается карточкой: первая ячейка — заголовок, остальные — с подписью колонки.

Подпись CSS берёт из data-label, поэтому её надо проставить в разметке. Этот модуль:
  * находит строку заголовков (первая <tr> с <th>) и помечает её class="cmp-head";
  * каждой ячейке данных ставит data-label="<текст заголовка колонки>" (если заголовок
    колонки пустой — а у первой колонки он обычно пустой — подписи нет);
  * добавляет таблице класс stack — CSS-карточки включаются только на таких таблицах,
    а таблица без подписей по-прежнему листается вбок и не ломается.
Операция идемпотентна: повторный прогон ничего не меняет.

Запуск по всему сайту: python tools/cmp_tables.py
Генераторы тестов и подходов вызывают label_tables() сами перед записью страницы.
check_site.py падает, если на странице осталась .cmp без класса stack.
"""
import re, io, os, sys, html

TABLE_RE = re.compile(r'<table class="cmp[^"]*">.*?</table>', re.S)
ROW_RE = re.compile(r'(<tr)([^>]*)(>)(.*?)(</tr>)', re.S)
CELL_RE = re.compile(r'<t([hd])([^>]*)>(.*?)</t\1>', re.S)


def _text(s):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', s))).strip()


def _one(m):
    t = m.group(0)
    rows = list(ROW_RE.finditer(t))
    head = next((r for r in rows if '<th' in r.group(4)), None)
    if head is None:
        return t
    labels = [_text(c.group(3)) for c in CELL_RE.finditer(head.group(4))]
    out, pos = [], 0
    for r in rows:
        out.append(t[pos:r.start()])
        pos = r.end()
        attrs, body = r.group(2), r.group(4)
        if r is head:
            if 'cmp-head' not in attrs:
                attrs = attrs + ' class="cmp-head"'
            out.append(r.group(1) + attrs + r.group(3) + body + r.group(5))
            continue
        cells, i = [], 0

        def cell(c):
            nonlocal i
            tag, cattrs, inner = c.group(1), c.group(2), c.group(3)
            if i < len(labels) and labels[i] and 'data-label=' not in cattrs:
                cattrs = cattrs + ' data-label="%s"' % html.escape(labels[i], quote=True)
            i += 1
            return '<t%s%s>%s</t%s>' % (tag, cattrs, inner, tag)

        body = CELL_RE.sub(cell, body)
        out.append(r.group(1) + attrs + r.group(3) + body + r.group(5))
    out.append(t[pos:])
    t = ''.join(out)
    t = re.sub(r'<table class="cmp([^"]*)">', lambda mm: mm.group(0) if 'stack' in mm.group(1).split()
               else '<table class="cmp%s stack">' % mm.group(1), t, count=1)
    return t


def label_tables(page):
    return TABLE_RE.sub(_one, page)


def main():
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    changed = 0
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'supabase', 'yandex', 'tools')]
        for f in files:
            if not f.endswith('.html'):
                continue
            p = os.path.join(dirpath, f)
            s = io.open(p, encoding='utf-8').read()
            if '<table class="cmp' not in s:
                continue
            n = label_tables(s)
            if n != s:
                io.open(p, 'w', encoding='utf-8', newline='').write(n)
                changed += 1
                print('подписи проставлены:', os.path.relpath(p, root))
    print('изменено страниц:', changed)


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()

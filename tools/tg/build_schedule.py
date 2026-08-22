# -*- coding: utf-8 -*-
"""Собирает tools/tg/schedule.json из общего плана постов (tools/vk/month.py).

Телеграм, в отличие от ВК, умеет разметку — поэтому текст переверстывается:
первая строка и подзаголовки становятся жирными, голые адреса сайта
превращаются в ссылки словом, хэштеги убираются (в канале они бесполезны).

Картинка не прикладывается файлом: она уходит превью-ссылкой на aitherapist.ru,
иначе Телеграм ограничил бы подпись 1024 символами вместо 4096.
"""
import os, sys, json, re, html, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'vk'))
from month import PLAN  # noqa: E402
from posts_tg import POSTS as TG  # noqa: E402

IMG_BASE = 'https://aitherapist.ru/assets/social/'
OUT = os.path.join(HERE, 'schedule.json')

# осмысленный текст ссылки вместо голого адреса
ANCHORS = {
    'blog/prokrastinatsiya.html':        'Разбор целиком — почему откладывание не про лень',
    'blog/navyazchivye-mysli.html':      'Разбор целиком — про навязчивые мысли',
    'blog/toksichnye-otnosheniya.html':  'Разбор целиком — про токсичные отношения',
    'blog/kak-spravitsya-s-odinochestvom.html': 'Разбор целиком — про одиночество',
    'blog/osennyaya-depressiya.html':    'Разбор целиком — про осеннюю хандру',
    'podhody/kpt.html':                  'Подробно про КПТ',
    'podhody/cft.html':                  'Подробно про подход, сфокусированный на сострадании',
    'podhody/act.html':                  'Подробно про ACT',
    'podhody/mindfulness.html':          'Подробно про практики осознанности',
    'testy/depressiya-phq-9.html':       'Пройти PHQ-9 — бесплатно, без регистрации',
    'testy/stress-pss-10.html':          'Пройти PSS-10 — бесплатно, без регистрации',
    'testy/samootsenka-rozenberga.html': 'Пройти шкалу Розенберга — бесплатно, без регистрации',
    'testy/depressiya-trevoga-stress-dass-21.html': 'Пройти DASS-21 — бесплатно, без регистрации',
}

URL_RE = re.compile(r'(?:^|\s)aitherapist\.ru/(\S+?)(?=[\s]|$)')


def is_heading(line, nxt):
    """Короткая строка без завершающей точки, за которой идёт текст, — подзаголовок."""
    t = line.strip()
    if not t or len(t) > 62:
        return False
    if t[-1] in '.!?…':
        return False
    if t.startswith(('•', '▸', '─', '1.', '2.', '3.', '4.')):
        return False
    if re.match(r'^[\W\d]+$', t):
        return False
    return bool(nxt.strip())


def to_html(text):
    lines = text.split('\n')
    out = []
    for i, line in enumerate(lines):
        nxt = ' '.join(lines[i + 1:i + 3])
        stripped = line.strip()

        if stripped.startswith('#'):            # хэштеги в канал не несём
            continue

        m = URL_RE.search(line)
        if m:
            path = m.group(1).rstrip('.,')
            anchor = ANCHORS.get(path, 'Читать на сайте')
            out.append('<a href="https://aitherapist.ru/%s">%s</a>' % (path, html.escape(anchor)))
            continue

        esc = html.escape(line)
        # у пунктов-маркеров жирним первую фразу — это то, на что надо смотреть
        m3 = re.match(r'^([^\w\s]+\s+)([^.]{3,58})\.(\s.+)$', esc)
        if m3 and not is_heading(line, nxt):
            out.append(m3.group(1) + '<b>' + m3.group(2) + '.</b>' + m3.group(3))
            continue
        if i == 0 or is_heading(line, nxt):
            # эмодзи в начале строки оставляем снаружи жирного — так аккуратнее
            m2 = re.match(r'^([^\w\s]+\s+)(.*)$', esc)
            if m2:
                esc = m2.group(1) + '<b>' + m2.group(2) + '</b>'
            else:
                esc = '<b>' + esc + '</b>'
        out.append(esc)

    res = '\n'.join(out)
    res = re.sub(r'\n{3,}', '\n\n', res).strip()
    return res


def build():
    items = []
    for date, hhmm, key, text in PLAN:
        # телеграмный текст, если он написан; иначе — автоперевод вэкашного
        body = TG.get(key) or to_html(text)
        items.append({
            'id': '%s-%s' % (date, key),
            'when': '%s %s' % (date, hhmm),
            'image': IMG_BASE + key + '.jpg',
            'html': body,
        })
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=1)
    return items


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    items = build()
    print('постов:', len(items), '->', OUT)
    long = [i['id'] for i in items if len(i['html']) > 4000]
    print('слишком длинных (>4000):', long or 'нет')
    if '--show' in sys.argv:
        print('\n' + '=' * 60)
        print(items[1]['html'])

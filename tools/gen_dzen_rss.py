# -*- coding: utf-8 -*-
"""Собирает dzen.xml — RSS-ленту статей блога для трансляции в Дзен.

Дзен проверяет ленту несколько раз в час и публикует новое сам, так что после
подключения ничего делать не надо: добавили статью → прогнали этот скрипт → пуш.

Что важно в разметке (справка Дзена, export-content и rss-modify):
  * в content:encoded нужен ПОЛНЫЙ текст — одним анонсом со ссылкой не отделаться;
  * <category>noindex</category> запрещает индексацию копии в поиске, поэтому
    статья в Дзене не конкурирует с нашей же страницей в Яндексе. Не убирать;
  * обложка в enclosure — JPEG/PNG, не WebP, минимум 480×320.

Картинки: у нас всё в WebP, Дзен его не принимает, поэтому скрипт кладёт
JPEG-копии в assets/dzen/ и ссылается на них.
"""
import os, re, io, sys, json, html, datetime, email.utils

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLOG = os.path.join(ROOT, 'blog')
OUT = os.path.join(ROOT, 'dzen.xml')
JPEG_DIR = os.path.join(ROOT, 'assets', 'dzen')
STATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dzen_sent.json')
SITE = 'https://aitherapist.ru/'
MAX_IMG_W = 1200

# Статьи, написанные ДО подключения ленты, приезжают в Дзен черновиками:
# иначе при первом чтении ленты он опубликовал бы весь архив разом.
# Всё, что появится позже этой даты, публикуется автоматически.
DRAFT_BEFORE = '2026-08-23'

# ⚠️ Дзен забирает из ленты только СВЕЖИЕ материалы («за последние два-три дня»,
# справка rss-modify) и молча пропускает всё, что старше. 26.08.2026 на этом
# и погорели: из 19 статей архива в черновики приехали только 8 — те, что были
# датированы 19 и 21 августа, а одиннадцать с датами июня-августа он проигнорировал.
#
# Поэтому статье старше FRESH_DAYS в ЛЕНТУ (не на сайте!) проставляется сегодняшняя
# дата — это дата публикации копии в Дзене, настоящие datePublished/dateModified
# страницы не трогаются. Проставленная дата один раз записывается в dzen_sent.json
# и дальше не меняется: повторно отправленный материал Дзен всё равно не берёт,
# а плавающая дата выглядела бы как правка.
#
# На флаг черновика это не влияет — он считается по НАСТОЯЩЕЙ дате статьи,
# иначе весь передатированный архив ушёл бы в публикацию пачкой.
FRESH_DAYS = 3

# Единственный работающий канал из Дзена на сайт — переходы живых людей:
# ссылки там nofollow, а копия ещё и noindex. Поэтому в конце каждой статьи
# ставим короткий блок со ссылками. Тесты впереди статей осознанно:
# «пройти тест» кликают охотнее, чем «читать ещё».
TAIL = (
    '<p><b>Что ещё есть на сайте</b></p>'
    '<p><a href="%(s)stesty/">Бесплатные психологические тесты</a> — GAD-7, PHQ-9, DASS-21 '
    'и другие, без регистрации.</p>'
    '<p><a href="%(s)sbesplatnaya-psihologicheskaya-pomoshch.html">Куда обратиться '
    'за бесплатной помощью</a> — телефоны, что даёт ОМС и правда ли, что «поставят на учёт».</p>'
) % {'s': SITE}

# блоки, которые в Дзене не нужны: навигация по странице и наша служебка
DROP_CLASSES = ('crumbs', 'date', 'toc', 'eeat')


def read(path):
    return io.open(path, encoding='utf-8').read()


def webp_to_jpeg(rel_src):
    """assets/blog/x.webp → assets/dzen/x.jpg (создаёт файл при необходимости)."""
    from PIL import Image
    rel = rel_src.replace('../', '').split('?')[0]
    src = os.path.join(ROOT, rel.replace('/', os.sep))
    if not os.path.exists(src):
        return None
    name = os.path.splitext(os.path.basename(rel))[0] + '.jpg'
    dst = os.path.join(JPEG_DIR, name)
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        os.makedirs(JPEG_DIR, exist_ok=True)
        im = Image.open(src).convert('RGB')
        if im.size[0] > MAX_IMG_W:
            k = MAX_IMG_W / im.size[0]
            im = im.resize((MAX_IMG_W, int(im.size[1] * k)), Image.LANCZOS)
        im.save(dst, quality=82, optimize=True)
    return 'assets/dzen/' + name


def body_html(page):
    """Вырезает текст статьи и приводит его к разметке, которую понимает Дзен."""
    m = re.search(r'<main class="legal">(.*?)</main>', page, re.S)
    if not m:
        return None
    b = m.group(1)

    b = re.sub(r'<script.*?</script>', '', b, flags=re.S)
    b = re.sub(r'<h1[^>]*>.*?</h1>', '', b, flags=re.S)
    for cls in DROP_CLASSES:
        b = re.sub(r'<(p|div|nav|aside)[^>]*class="[^"]*\b%s\b[^"]*"[^>]*>.*?</\1>' % cls,
                   '', b, flags=re.S)
    # врезки — в цитаты, это Дзен показывает нормально
    b = re.sub(r'<div[^>]*class="[^"]*\b(note|tip|tldr|sos|example|reassure|cta-box)\b[^"]*"[^>]*>(.*?)</div>',
               r'<blockquote>\2</blockquote>', b, flags=re.S)
    # подпись под картинкой: без обёртки её текст сливается с соседним абзацем
    b = re.sub(r'<figcaption[^>]*>(.*?)</figcaption>', r'<p><i>\1</i></p>', b, flags=re.S)
    # подпись под цитатой: <footer> внутри <p> — недопустимая вложенность, курсив надёжнее
    b = re.sub(r'</?footer[^>]*>', lambda m: '</i>' if m.group(0).startswith('</') else '<i>', b)
    # карточки гида: <a><b>заголовок</b><span>описание</span><em>Начать отсюда</em></a>.
    # «Начать отсюда →» — экранный жест, в тексте статьи он бессмыслен.
    b = re.sub(r'<a href="([^"]+)"[^>]*>\s*<b>(.*?)</b>\s*<span>(.*?)</span>'
               r'\s*(?:<em>.*?</em>)?\s*</a>',
               r'<p><a href="\1"><b>\2</b></a> — \3</p>', b, flags=re.S)
    b = re.sub(r'</?(figure|figcaption|section|div|span)[^>]*>', '', b)
    b = re.sub(r'\sid="[^"]*"', '', b)
    b = re.sub(r'\sclass="[^"]*"', '', b)

    # картинки: webp → jpeg, пути абсолютные
    def fix_img(mm):
        src = re.search(r'src="([^"]+)"', mm.group(0))
        alt = re.search(r'alt="([^"]*)"', mm.group(0))
        if not src:
            return ''
        rel = webp_to_jpeg(src.group(1))
        if not rel:
            return ''
        return '<img src="%s%s" alt="%s">' % (SITE, rel, alt.group(1) if alt else '')
    b = re.sub(r'<img[^>]*>', fix_img, b)

    # относительные ссылки → абсолютные
    b = re.sub(r'href="\.\./([^"]*)"', 'href="%s\\1"' % SITE, b)
    b = re.sub(r'href="\./([^"]*)"', 'href="%sblog/\\1"' % SITE, b)
    b = re.sub(r'href="#[^"]*"', 'href="%s"' % SITE, b)
    # соседние статьи лежат в blog/ и пишутся без префикса
    b = re.sub(r'href="(?!https?:|mailto:|#)([^"]+)"', r'href="%sblog/\1"' % SITE, b)

    b = tables_to_lists(b)
    b = wrap_loose(b)

    b = re.sub(r'\n{2,}', '\n', b)
    return b.strip()


# Блочные теги: внутри них текст стоит сам по себе и склеиться не может.
BLOCK = {'p', 'h2', 'h3', 'h4', 'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr',
         'td', 'th', 'blockquote', 'img', 'hr'}
# Контейнеры, где текст может оказаться голым: корень статьи и наши врезки.
LOOSE_IN = {None, 'blockquote'}


def wrap_loose(b):
    """Заворачивает в <p> текст, лежащий в контейнере без блочной обёртки.

    ⚠️ Ради этого всё и затевалось: Дзен не расставляет переносы сам, и голая
    ссылка-кнопка из .cta-box слипалась со следующим абзацем — получалось
    «Начать разговор бесплатноЕсли самое трудное…». То же с текстом врезок,
    который в статьях написан прямо внутри <div>, и с подписями к картинкам.
    Правило общее, а не заплатка на кнопку: любая новая разметка в статье
    приедет в Дзен разделённой.
    """
    out, stack, p_open = [], [], False
    for tok in re.split(r'(<[^>]+>)', b):
        if not tok:
            continue
        if tok.startswith('<'):
            name = re.match(r'</?\s*(\w+)', tok)
            name = name.group(1).lower() if name else ''
            closing = tok.startswith('</')
            ctx = stack[-1] if stack else None
            if name in BLOCK:
                if p_open:                      # блок прерывает абзац
                    out.append('</p>'); p_open = False
                if closing:
                    if stack and stack[-1] == name:
                        stack.pop()
                elif name not in ('img', 'hr') and not tok.endswith('/>'):
                    stack.append(name)
                out.append(tok)
                continue
            if closing and p_open and ctx in LOOSE_IN:
                out.append(tok); continue
            if not closing and ctx in LOOSE_IN and not p_open:
                out.append('<p>'); p_open = True
            out.append(tok)
            continue
        ctx = stack[-1] if stack else None
        if tok.strip() and ctx in LOOSE_IN and not p_open:
            out.append('<p>'); p_open = True
        out.append(tok)
    if p_open:
        out.append('</p>')
    return ''.join(out)


def tables_to_lists(b):
    """Таблицы Дзен показывает ненадёжно — разворачиваем их в списки."""
    def one(m):
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', m.group(0), re.S)
        out = []
        for i, row in enumerate(rows):
            cells = [re.sub(r'<[^>]+>', '', c).strip()
                     for c in re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', row, re.S)]
            cells = [c for c in cells if c]
            if not cells:
                continue
            if i == 0 and '<th' in row:
                out.append('<p><b>%s</b></p>' % ' · '.join(cells))
            else:
                head, rest = cells[0], cells[1:]
                out.append('<li><b>%s</b>%s</li>' % (head, (' — ' + ' · '.join(rest)) if rest else ''))
        lis = [x for x in out if x.startswith('<li')]
        ps = [x for x in out if x.startswith('<p')]
        return ''.join(ps) + ('<ul>%s</ul>' % ''.join(lis) if lis else '')
    return re.sub(r'<table[^>]*>.*?</table>', one, b, flags=re.S)


def meta(page):
    def tag(pat, default=''):
        m = re.search(pat, page, re.S)
        return html.unescape(m.group(1)).strip() if m else default
    return {
        'title': tag(r'<h1[^>]*>(.*?)</h1>'),
        'descr': tag(r'<meta name="description" content="([^"]*)"'),
        'cover': tag(r'<meta property="og:image" content="([^"]*)"'),
        'date':  tag(r'"datePublished"\s*:\s*"([^"]+)"'),
        'mod':   tag(r'"dateModified"\s*:\s*"([^"]+)"'),
    }


def load_state():
    if os.path.exists(STATE):
        return json.load(io.open(STATE, encoding='utf-8'))
    return {}


def save_state(state):
    io.open(STATE, 'w', encoding='utf-8').write(
        json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True) + chr(10))


def feed_date(slug, real_iso, state):
    """Дата для ленты: своя у статей, которые Дзен иначе сочтёт несвежими.

    Возвращает (RFC822-дата, передатирована ли)."""
    if slug in state:
        return state[slug], state[slug][5:16] != rfc822(real_iso)[5:16]
    now = datetime.datetime.now(datetime.timezone.utc)
    try:
        age = (now - datetime.datetime.strptime(real_iso[:10], '%Y-%m-%d')
               .replace(tzinfo=datetime.timezone.utc)).days
    except ValueError:
        age = 0
    stamped = age > FRESH_DAYS
    state[slug] = email.utils.format_datetime(now) if stamped else rfc822(real_iso)
    return state[slug], stamped


def rfc822(iso):
    for f in ('%Y-%m-%d', '%Y-%m-%dT%H:%M:%S'):
        try:
            return email.utils.format_datetime(datetime.datetime.strptime(iso[:19], f))
        except ValueError:
            continue
    return email.utils.format_datetime(datetime.datetime.now())


def build():
    state = load_state()
    items = []
    for name in sorted(os.listdir(BLOG)):
        if not name.endswith('.html') or name == 'index.html':
            continue
        page = read(os.path.join(BLOG, name))
        m = meta(page)
        body = body_html(page)
        if not body or not m['title']:
            print('  пропущено (не разобралось):', name)
            continue
        cover = webp_to_jpeg(m['cover'].replace(SITE, '')) if m['cover'] else None
        url = SITE + 'blog/' + name
        real = m['mod'] or m['date'] or ''
        date, stamped = feed_date(name[:-5], real, state)
        items.append({
            'url': url, 'title': m['title'], 'descr': m['descr'],
            'date': date, 'stamped': stamped, 'cover': cover, 'body': body + TAIL,
            'draft': real[:10] < DRAFT_BEFORE,
        })

    save_state(state)

    esc = lambda s: html.escape(s, quote=True)
    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<rss xmlns:content="http://purl.org/rss/1.0/modules/content/" version="2.0">',
             '<channel>',
             '<title>AI Therapist — о тревоге, выгорании и самопомощи</title>',
             '<link>%s</link>' % SITE,
             '<description>Статьи о тревоге, выгорании, сне и самооценке: что происходит '
             'и что с этим делать. Материалы команды AI Therapist.</description>',
             '<language>ru</language>']
    for it in items:
        parts += ['<item>',
                  '<title>%s</title>' % esc(it['title']),
                  '<link>%s</link>' % it['url'],
                  '<guid isPermaLink="true">%s</guid>' % it['url'],
                  '<pubDate>%s</pubDate>' % it['date'],
                  '<description>%s</description>' % esc(it['descr']),
                  '<category>format-article</category>',
                  '<category>noindex</category>',
                  '<category>comment-all</category>']
        if it['draft']:
            parts.append('<category>native-draft</category>')
        if it['cover']:
            parts.append('<enclosure url="%s%s" type="image/jpeg" length="0"/>' % (SITE, it['cover']))
        parts += ['<content:encoded><![CDATA[%s]]></content:encoded>' % it['body'],
                  '</item>']
    parts += ['</channel>', '</rss>']

    io.open(OUT, 'w', encoding='utf-8').write('\n'.join(parts))
    return items


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    items = build()
    size = os.path.getsize(OUT) / 1024
    print('статей в ленте: %d (минимум для подключения — 10)' % len(items))
    print('dzen.xml: %.0f КБ (лимит 10 МБ)' % size)
    jpegs = os.listdir(JPEG_DIR) if os.path.exists(JPEG_DIR) else []
    total = sum(os.path.getsize(os.path.join(JPEG_DIR, f)) for f in jpegs) / 1024 / 1024
    print('картинок сконвертировано: %d (%.1f МБ)' % (len(jpegs), total))
    print('черновиками: %d, сразу в публикацию: %d'
          % (sum(1 for i in items if i['draft']), sum(1 for i in items if not i['draft'])))
    fresh = [i['url'].split('/')[-1] for i in items if i['stamped']]
    if fresh:
        print('передатировано сегодняшним числом (иначе Дзен сочтёт несвежим): %d' % len(fresh))
        for f in fresh:
            print('   ', f)
    short = [i['title'] for i in items if len(i['body']) < 2000]
    print('подозрительно короткие:', short or 'нет')

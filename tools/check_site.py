# -*- coding: utf-8 -*-
"""
Проверка всего сайта. Запуск: python tools/check_site.py [--strict]

Каждая проверка здесь появилась после реальной ошибки, а не «на всякий случай»:

  JSON-LD       — правка разметки руками ломает JSON молча, страница при этом
                  выглядит нормально.
  FAQ дословно  — видимый ответ обязан совпадать с FAQPage слово-в-слово, иначе
                  сниппет не покажется. 19.08 нашлось расхождение в одну пару
                  кавычек, которое жило в проде месяцами.
  Ссылки        — при переносе страниц легко получить битую относительную ссылку.
  Вложенность   — незакрытый тег ломает вёрстку ниже по странице.
  title/desc    — 21.08 было 12 title длиннее 65 и 15 description длиннее 175:
                  хвост с ключом обрезался в выдаче.
  og:image      — Google Discover и крупная карточка требуют ширину от 1200 px.
                  21.08 у 17 из 20 статей обложка была меньше.
  width/height  — если не совпадают с реальным файлом, вёрстку дёргает при загрузке.
  Индекс риска  — «слов × входящих». Ниже ~4000 страницы у нас уже выпадали
                  как «малоценные», см. память seo-maloc-page-incident.
  Sitemap       — страница без записи в карте не индексируется.

Выход 1, если есть ошибки (в --strict — и если есть предупреждения).
"""
import glob
import html as htmllib
import io
import json
import os
import re
import sys
from collections import Counter
from html.parser import HTMLParser

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
SITE = 'https://aitherapist.ru'

TITLE_MAX = 65
DESC_MIN, DESC_MAX = 120, 175
OG_MIN_WIDTH = 1200
RISK_MIN = 4000
HUB_MIN_WORDS = 800          # у хабов priority 0.9 — тонкий хаб не ранжируется

errors, warns = [], []


def err(where, msg):
    errors.append('%s: %s' % (where, msg))


def warn(where, msg):
    warns.append('%s: %s' % (where, msg))


def pages():
    out = []
    for p in glob.glob('**/*.html', recursive=True):
        p = p.replace('\\', '/')
        if '.git' in p or p.startswith('assets/') or p.startswith('tools/'):
            continue
        out.append(p)
    return sorted(out)


def _tidy(s):
    """Убираем пробел перед знаками препинания и после открывающих кавычек/скобок.

    Тег при вырезании заменяется пробелом — иначе слипаются соседние слова.
    Но в видимом тексте ссылку часто закрывают вплотную к точке
    («…в <a href="privacy.html">политике конфиденциальности</a>.»), и без этой
    нормализации сравнение FAQ давало ложные расхождения.
    """
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s+([.,;:!?…»)])', r'\1', s)
    return re.sub(r'([«(])\s+', r'\1', s)


def strip_tags(s):
    s = re.sub(r'(?is)<script.*?</script>|<style.*?</style>', ' ', s)
    return _tidy(htmllib.unescape(re.sub(r'(?s)<[^>]+>', ' ', s)))


def ld_blocks(s):
    for m in re.finditer(r'(?s)<script type="application/ld\+json">(.*?)</script>', s):
        yield m.group(1)


# ─────────────────────────── вложенность тегов ───────────────────────────
VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
        'link', 'meta', 'param', 'source', 'track', 'wbr'}
OPTIONAL = {'p', 'li', 'tr', 'td', 'th', 'thead', 'tbody', 'option'}


class Nest(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.st, self.bad = [], []

    def handle_starttag(self, t, a):
        if t not in VOID:
            self.st.append(t)

    def handle_endtag(self, t):
        if t in VOID:
            return
        while self.st and self.st[-1] in OPTIONAL and self.st[-1] != t:
            self.st.pop()
        if not self.st:
            self.bad.append('лишний </%s>' % t)
            return
        if self.st[-1] != t:
            self.bad.append('ожидался </%s>, пришёл </%s>' % (self.st[-1], t))
            for i in range(len(self.st) - 1, -1, -1):
                if self.st[i] == t:
                    del self.st[i:]
                    return
            return
        self.st.pop()


def main():
    files = pages()
    src = {f: io.open(f, encoding='utf-8').read() for f in files}
    sitemap = io.open('sitemap.xml', encoding='utf-8').read() if os.path.exists('sitemap.xml') else ''
    inlinks = Counter()
    words = {}
    titles, descs = {}, {}

    try:
        from PIL import Image
        have_pil = True
    except ImportError:
        have_pil = False
        warn('окружение', 'Pillow не установлен — размеры картинок не проверены')

    for f, s in src.items():
        base = os.path.dirname(f)
        is_404 = f == '404.html'

        # --- JSON-LD ---
        for blk in ld_blocks(s):
            try:
                json.loads(blk)
            except Exception as e:
                err(f, 'JSON-LD не парсится — %s' % e)

        # --- вложенность ---
        n = Nest()
        n.feed(s)
        left = [t for t in n.st if t not in OPTIONAL]
        if n.bad or left:
            err(f, 'вложенность тегов: %s%s' % ('; '.join(n.bad[:2]),
                                                (' | не закрыты: %s' % left[:4]) if left else ''))

        # --- title / description ---
        mt = re.search(r'<title>(.*?)</title>', s, re.S)
        md = re.search(r'name="description"\s+content="(.*?)"', s, re.S)
        t = mt.group(1).strip() if mt else ''
        d = md.group(1).strip() if md else ''
        if not t:
            err(f, 'нет <title>')
        if not d and not is_404:
            err(f, 'нет meta description')
        titles.setdefault(t, []).append(f)
        descs.setdefault(d, []).append(f)
        if len(t) > TITLE_MAX:
            warn(f, 'title %d символов (>%d) — хвост обрежется в выдаче' % (len(t), TITLE_MAX))
        if d and not (DESC_MIN <= len(d) <= DESC_MAX):
            warn(f, 'description %d символов (норма %d–%d)' % (len(d), DESC_MIN, DESC_MAX))

        # --- обязательная обвязка ---
        if not is_404:
            if 'rel="canonical"' not in s:
                err(f, 'нет canonical')
            if '110180781' not in s:
                err(f, 'нет счётчика Метрики')
            if 'og:image' not in s:
                err(f, 'нет og:image')
        if 'lang="ru"' not in s:
            err(f, 'нет lang="ru"')
        if len(re.findall(r'<h1[\s>]', s)) != 1:
            err(f, 'h1 должен быть ровно один, найдено %d' % len(re.findall(r'<h1[\s>]', s)))

        # --- og:image: ширина и наличие файла ---
        mo = re.search(r'property="og:image"\s+content="([^"]+)"', s)
        if mo and have_pil:
            rel = mo.group(1).replace(SITE + '/', '')
            if not os.path.exists(rel):
                err(f, 'og:image не найден: %s' % rel)
            else:
                try:
                    w, h = Image.open(rel).size
                    if w < OG_MIN_WIDTH:
                        warn(f, 'og:image %dx%d — уже %d px, не годится для Discover '
                                'и крупной карточки' % (w, h, OG_MIN_WIDTH))
                except Exception as e:
                    warn(f, 'og:image не прочитался: %s' % e)

        # --- картинки: alt, размеры, соответствие файлу ---
        for tag in re.findall(r'<img[^>]*>', s):
            if 'mc.yandex.ru' in tag:
                continue
            if 'alt=' not in tag:
                err(f, 'img без alt: %s' % tag[:70])
            msrc = re.search(r'src="([^"]+)"', tag)
            mw = re.search(r'width="(\d+)"', tag)
            mh = re.search(r'height="(\d+)"', tag)
            if not (mw and mh):
                warn(f, 'img без width/height (дёргает вёрстку): %s' % tag[:70])
                continue
            if msrc and have_pil and not msrc.group(1).startswith('http'):
                _s = msrc.group(1)
                # путь может быть от корня сайта (404.html), а не относительным
                p = _s[1:] if _s.startswith('/') else os.path.join(base, _s)
                p = os.path.normpath(p).replace('\\', '/')
                if not os.path.exists(p):
                    err(f, 'картинка не найдена: %s' % msrc.group(1))
                else:
                    try:
                        rw, rh = Image.open(p).size
                        dw, dh = int(mw.group(1)), int(mh.group(1))
                        # Файл КРУПНЕЕ отображаемого размера — так и задумано:
                        # миниатюры 240×240 показываются в 96px, иконки 192×192
                        # в 34px, чтобы не мылились на 2x/3x-экранах.
                        # Ругаемся только на две настоящие беды:
                        #   апскейл (файл мельче разметки — мыло)
                        #   и расхождение пропорций (картинку плющит).
                        if rw < dw or rh < dh:
                            warn(f, '%s: апскейл — в разметке %dx%d, файл всего %dx%d'
                                 % (os.path.basename(p), dw, dh, rw, rh))
                        elif abs((rw / rh) - (dw / dh)) > 0.01:
                            warn(f, '%s: пропорции не совпадают — в разметке %dx%d (%.3f), '
                                    'в файле %dx%d (%.3f), картинку сплющит'
                                 % (os.path.basename(p), dw, dh, dw / dh, rw, rh, rw / rh))
                    except Exception:
                        pass

        # --- ссылки ---
        for href in set(re.findall(r'href="([^"]+)"', s)):
            if href.startswith(('http', 'mailto:', 'tel:', '#', '${')):
                continue
            path = href.split('#')[0].split('?')[0]
            if not path:
                continue
            tgt = path[1:] if path.startswith('/') else os.path.join(base, path)
            tgt = os.path.normpath(tgt).replace('\\', '/')
            if tgt.endswith('/'):
                tgt += 'index.html'
            if os.path.isdir(tgt):
                tgt += '/index.html'
            if not os.path.exists(tgt):
                err(f, 'битая ссылка: %s' % href)
            elif tgt.endswith('.html') and tgt != f:
                inlinks[tgt] += 1

        # --- объём ---
        body = re.sub(r'(?is)<head.*?</head>', '', s)
        words[f] = len(re.findall(r'[А-Яа-яЁёA-Za-z]{2,}', strip_tags(body)))

        # --- FAQ дословно ---
        answers = []
        for blk in ld_blocks(s):
            try:
                data = json.loads(blk)
            except Exception:
                continue
            for node in (data.get('@graph') or [data]):
                if node.get('@type') == 'FAQPage':
                    for q in node.get('mainEntity', []):
                        answers.append((q.get('name', ''), q['acceptedAnswer']['text']))
        if answers:
            visible = strip_tags(s)
            for q, a in answers:
                if _tidy(htmllib.unescape(a)) not in visible:
                    err(f, 'FAQ не совпадает дословно с разметкой: «%s…»' % q[:55])

        # --- sitemap ---
        if not is_404 and sitemap:
            url = SITE + '/' + f
            if f == 'index.html':
                url = SITE + '/'
            elif f.endswith('/index.html'):
                url = SITE + '/' + f[:-len('index.html')]
            if '<loc>%s</loc>' % url not in sitemap:
                err(f, 'нет в sitemap.xml')

    # --- дубли title / description ---
    for label, d in (('title', titles), ('description', descs)):
        for v, fs in d.items():
            if v and len(fs) > 1:
                err('дубль', '%s повторяется на %s' % (label, ', '.join(fs)))

    # --- индекс риска и тонкие хабы ---
    print('\n%-50s %6s %8s %9s' % ('страница', 'слов', 'входящих', 'риск'))
    print('-' * 78)
    for f in sorted(files, key=lambda x: words[x] * max(inlinks[x], 1)):
        if f in ('404.html',) or f in ('privacy.html', 'terms.html', 'oferta.html'):
            continue
        risk = words[f] * max(inlinks[f], 1)
        flag = ''
        if risk < RISK_MIN:
            flag = '  ← ниже порога, выпадала как «малоценная»'
            warn(f, 'индекс риска %d (<%d): %d слов × %d входящих'
                 % (risk, RISK_MIN, words[f], inlinks[f]))
        if f.endswith('/index.html') and words[f] < HUB_MIN_WORDS:
            warn(f, 'хаб тоньше %d слов (%d) при высоком priority' % (HUB_MIN_WORDS, words[f]))
        print('%-50s %6d %8d %9d%s' % (f, words[f], inlinks[f], risk, flag))

    # --- итог ---
    print()
    if warns:
        print('ПРЕДУПРЕЖДЕНИЯ (%d):' % len(warns))
        for w in warns:
            print('  ·', w)
    if errors:
        print('\nОШИБКИ (%d):' % len(errors))
        for e in errors:
            print('  !', e)
        return 1
    print('\nОшибок нет.' + (' Предупреждения выше — на ваше усмотрение.' if warns else ''))
    return 1 if ('--strict' in sys.argv and warns) else 0


if __name__ == '__main__':
    sys.exit(main())

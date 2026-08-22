# -*- coding: utf-8 -*-
"""Готовит картинки для постов ВК.

Если у картинки есть исходник в «для блога» (1536×1024 / 1730×909) — берём его:
он в 1.4–1.6 раза крупнее того, что лежит в assets. Иначе берём assets как есть.
Всё, что шире 2:1, кладём на подложку 1.91:1 — иначе ВК обрежет.
"""
import os
from PIL import Image
import numpy as np

SRC = r'C:\Users\XE\Desktop\gpt\сайт\для блога'
SITE = r'C:\Users\XE\Desktop\ai_therapist_site\assets'
OUT = r'C:\Users\XE\AppData\Local\Temp\vkimg3'
os.makedirs(OUT, exist_ok=True)

# ключ -> (файл в assets, исходник в «для блога» или None)
PLAN = {
    'prokrastinaciya':   ('blog/prokrastinaciya-cover.webp',      '29.png'),
    'malenkiy-shag':     ('blog/malenkiy-shag.webp',              None),
    'test-phq9':         ('testy/depressiya-cover.webp',          None),
    'stress-rabota':     ('blog/stress-cover.webp',               '17.png'),
    'navyazchivye':      ('blog/navyazchivye-mysli-cover.webp',   '11.png'),
    'kpt':               ('podhody/kpt-cover.webp',              '87.png'),
    'test-pss10':        ('testy/stress-cover.webp',              None),

    'toksichnye':        ('blog/toksichnye-cover.webp',           '47.png'),
    'samosostradanie':   ('blog/samosostradanie.webp',            None),
    'test-rozenberg':    ('testy/samootsenka-cover.webp',         None),
    'odinochestvo':      ('blog/odinochestvo-cover.webp',         '38.png'),
    'mindfulness':       ('podhody/mindfulness-cover.webp',      '88.png'),
    'test-dass':         ('testy/dass-cover.webp',                '93.png'),
    'osennyaya':         ('blog/osennyaya-depressiya-cover.webp', '59.png'),
    'cft':               ('podhody/cft-cover.webp',               '89.png'),
    'act':               ('podhody/act-cover.webp',               '85.png'),
}

MAXW = 1500


def trim(im, thr=246):
    a = np.array(im.convert('L'))
    m = a < thr
    if not m.any():
        return im
    ys, xs = np.where(m)
    return im.crop((xs.min(), ys.min(), xs.max() + 1, ys.max() + 1))


def prepare(key):
    asset, src = PLAN[key]
    if src:
        im = trim(Image.open(os.path.join(SRC, src)).convert('RGB'))
    else:
        im = Image.open(os.path.join(SITE, asset.replace('/', os.sep))).convert('RGB')
    if im.size[0] > MAXW:
        k = MAXW / im.size[0]
        im = im.resize((MAXW, int(im.size[1] * k)), Image.LANCZOS)
    ratio = im.size[0] / im.size[1]
    if ratio > 2.0:                       # ВК режет — подкладываем поля
        bg = im.getpixel((2, 2))
        H = int(im.size[0] / 1.91)
        c = Image.new('RGB', (im.size[0], max(H, im.size[1])), bg)
        c.paste(im, (0, (c.size[1] - im.size[1]) // 2))
        im = c
    p = os.path.join(OUT, key + '.jpg')
    im.save(p, quality=95)
    return p, im.size, ('исходник ' + src if src else 'assets')


if __name__ == '__main__':
    import sys
    sys.stdout.reconfigure(encoding='utf-8')
    for k in PLAN:
        p, size, how = prepare(k)
        print('%-18s %-12s %s' % (k, '%dx%d' % size, how))

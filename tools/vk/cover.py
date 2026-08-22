# -*- coding: utf-8 -*-
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 768          # ВК режет обложку в 2.5:1 — рисуем сразу в этом формате
PAPER  = (246, 242, 234)
PAPER2 = (237, 231, 218)
WHITE  = (253, 251, 246)
INK    = (27, 32, 26)
INK_S  = (82, 90, 78)
INK_F  = (139, 146, 133)
SAND   = (166, 110, 56)
RULE   = (201, 195, 180)

SP  = "fonts/Spectral-SemiBold.ttf"
SPI = "fonts/Spectral-MediumItalic.ttf"
MAN = "fonts/Manrope.ttf"

def manrope(size, weight=400):
    f = ImageFont.truetype(MAN, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f

img = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(img)
d.line([(0, 0), (W, 0)], fill=RULE, width=4)
d.line([(0, H - 4), (W, H - 4)], fill=RULE, width=4)

X = 330

def tracked(draw, xy, text, font, fill, track=0):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + track

f_label = manrope(25, 600)
tracked(d, (X, 168), "ПСИХОЛОГИЧЕСКАЯ САМОПОМОЩЬ", f_label, INK_F, track=4.0)

f_h1 = ImageFont.truetype(SP, 118)
d.text((X - 6, 214), "AI Therapist", font=f_h1, fill=INK)

d.line([(X, 378), (X + 640, 378)], fill=RULE, width=2)

f_sub = manrope(40, 600)
d.text((X, 412), "Тревога · выгорание · самооценка", font=f_sub, fill=INK_S)

f_it = ImageFont.truetype(SPI, 36)
d.text((X, 480), "разборы, практики и бесплатные тесты", font=f_it, fill=SAND)

f_url = manrope(30, 600)
url = "aitherapist.ru"
uw = d.textlength(url, font=f_url)
d.text((X, 566), url, font=f_url, fill=INK_S)
d.line([(X, 608), (X + uw, 608)], fill=SAND, width=2)

f_msg = manrope(26, 500)

def bubble(x, y, w, text, fill, border=None, pad=22, lh=36):
    lines, cur = [], ""
    for word in text.split():
        t = (cur + " " + word).strip()
        if d.textlength(t, font=f_msg) <= w - 2 * pad:
            cur = t
        else:
            lines.append(cur); cur = word
    lines.append(cur)
    h = pad * 2 + lh * len(lines) - 8
    d.rounded_rectangle([x, y, x + w, y + h], radius=17, fill=fill,
                        outline=border, width=2 if border else 0)
    ty = y + pad - 3
    for ln in lines:
        d.text((x + pad, ty), ln, font=f_msg, fill=INK_S)
        ty += lh
    return y + h

RX, RW = 1230, 370
y = bubble(RX + 56, 250, RW - 56, "Не могу перестать об этом думать", PAPER2)
y = bubble(RX, y + 22, RW - 36, "Давай разложим — по одному шагу", WHITE, border=RULE)

img.convert("RGB").save("vk_cover.jpg", quality=95)
print("ok", img.size)

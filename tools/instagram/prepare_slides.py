"""Готовит слайды карусели к публикации: 2:3 из ChatGPT → 1080×1350 (4:5) JPEG.

    python tools/instagram/prepare_slides.py <папка_с_исходниками> <папка_вывода>

Исходники — PNG/JPG, порядок по имени (01.png, 02.png …). Рисунок НЕ режется:
обрезка по высоте съедает заголовки сверху и «листай →» снизу. Вместо этого
рисунок обрезается по содержимому (bbox + 36 px), центрируется на холсте 4:5
цвета фона (берётся из углов) и ужимается до 1080×1350. Поля по бокам
незаметны, только если фон ровный белый и рисунок-виньетка не касается краёв —
поэтому это и требуем в промптах.

Печатает, сколько пикселей осталось до каждого края: меньше ~10 — рисунок
упирается в край, при подкладке будет виден шов.
Плюс собирает лист-превью _sheet.jpg (служебные файлы с «_» скрипт публикации
пропускает).
"""
import sys
from pathlib import Path

from PIL import Image, ImageChops

MARGIN = 36


def prepare(src):
    im = Image.open(src).convert("RGB")
    w, h = im.size
    corners = [im.getpixel(p) for p in [(3, 3), (w - 4, 3), (3, h - 4), (w - 4, h - 4)]]
    bg = tuple(sorted(c[i] for c in corners)[1] for i in range(3))
    mask = ImageChops.difference(im, Image.new("RGB", im.size, bg)).convert("L")
    l, t, r, b = mask.point(lambda v: 255 if v > 22 else 0).getbbox()
    print(f"{src.name}: до краёв L{l} T{t} R{w - r} B{h - b}, фон {bg}")
    t2, b2 = max(0, t - MARGIN), min(h, b + MARGIN)
    l2, r2 = max(0, l - MARGIN), min(w, r + MARGIN)
    cw, ch = r2 - l2, b2 - t2
    W = max(cw, round(ch * 0.8))
    H = round(W * 1.25)
    if H < ch:
        H, W = ch, round(ch * 0.8)
    canvas = Image.new("RGB", (W, H), bg)
    canvas.paste(im.crop((l2, t2, r2, b2)), ((W - cw) // 2, (H - ch) // 2))
    return canvas.resize((1080, 1350), Image.LANCZOS)


def main():
    src_dir, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in src_dir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg"))
    slides = []
    for i, f in enumerate(files, 1):
        im = prepare(f)
        im.save(out_dir / f"{i:02d}.jpg", quality=92)
        slides.append(im)
    cols = 6
    rows = (len(slides) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 360, rows * 450), "white")
    for i, im in enumerate(slides):
        sheet.paste(im.resize((360, 450)), ((i % cols) * 360, (i // cols) * 450))
    sheet.save(out_dir / "_sheet.jpg", quality=85)
    print(f"готово: {len(slides)} слайдов → {out_dir}")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Генерирует blog/articles.json — машиночитаемый фид статей блога.
Его читает Android-приложение (вкладка «Статьи» в Дневнике), поэтому
ЗАПУСКАТЬ ПОСЛЕ КАЖДОЙ новой статьи (см. чек-лист в CLAUDE.md, п.9):

    python tools/gen_articles_json.py

Данные берутся из самих статей (og:title, meta description, og:image,
canonical, datePublished из JSON-LD) — отдельно ничего заполнять не нужно.
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BLOG = ROOT / "blog"
OUT = BLOG / "articles.json"
SITE_PREFIX = "https://aitherapist.ru/"


def image_size(url: str) -> tuple[int, int] | None:
    """Размеры обложки из локального файла (приложение сохраняет пропорции)."""
    if not url.startswith(SITE_PREFIX):
        return None
    path = ROOT / url[len(SITE_PREFIX):]
    try:
        with Image.open(path) as im:
            return im.size
    except Exception:
        return None


def extract(html: str) -> dict | None:
    def meta(pattern):
        m = re.search(pattern, html, re.IGNORECASE)
        return m.group(1).strip() if m else None

    title = meta(r'<meta property="og:title" content="([^"]+)"')
    desc = meta(r'<meta name="description" content="([^"]+)"')
    image = meta(r'<meta property="og:image" content="([^"]+)"')
    url = meta(r'<link rel="canonical" href="([^"]+)"')
    date = meta(r'"datePublished"\s*:\s*"([^"]+)"')
    if not (title and url):
        return None
    # Оценка времени чтения: слова видимого текста / 180 слов-в-минуту
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", html, flags=re.S)
    words = len(re.findall(r"[А-Яа-яЁёA-Za-z]{3,}", re.sub(r"<[^>]+>", " ", text)))
    item = {
        "title": title,
        "description": desc or "",
        "image": image or "",
        "url": url,
        "date": date or "",
        "minutes": max(2, round(words / 180)),
    }
    if image:
        size = image_size(image)
        if size:
            item["w"], item["h"] = size
    return item


def main() -> int:
    items = []
    for f in sorted(BLOG.glob("*.html")):
        if f.name == "index.html":
            continue
        data = extract(f.read_text(encoding="utf-8"))
        if data:
            items.append(data)
        else:
            print(f"SKIP (нет og:title/canonical): {f.name}")
    items.sort(key=lambda a: a["date"], reverse=True)
    OUT.write_text(
        json.dumps({"articles": items}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"OK: {len(items)} статей -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

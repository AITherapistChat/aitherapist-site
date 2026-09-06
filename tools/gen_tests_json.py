# -*- coding: utf-8 -*-
"""
Генерирует testy/tests.json — машиночитаемый фид тестов /testy/.
Его читает Android-приложение (вкладка «Тесты» в Дневнике), поэтому
ЗАПУСКАТЬ ПОСЛЕ КАЖДОГО нового теста — иначе в приложении он не появится:

    python tools/gen_tests_json.py

Данные берутся из самих страниц тестов (h1, og:description, og:image,
canonical, datePublished и строки «Шкала … · N вопросов» / «… на прохождение»),
отдельно ничего заполнять не нужно. Близнец tools/gen_articles_json.py —
формат записи такой же, добавлены поля questions/minutes_text/scale.

Заголовок в фид идёт из <h1>, а не из og:title: og:title заточен под выдачу
(«… онлайн (PHQ-9) — бесплатно, без регистрации»), в карточке приложения нужен
короткий человеческий заголовок.
"""
import json
import re
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
TESTY = ROOT / "testy"
OUT = TESTY / "tests.json"
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
        m = re.search(pattern, html, re.IGNORECASE | re.S)
        return m.group(1).strip() if m else None

    title = meta(r"<h1[^>]*>(.*?)</h1>")
    desc = meta(r'<meta property="og:description" content="([^"]+)"')
    if not desc:
        desc = meta(r'<meta name="description" content="([^"]+)"')
    image = meta(r'<meta property="og:image" content="([^"]+)"')
    url = meta(r'<link rel="canonical" href="([^"]+)"')
    date = meta(r'"datePublished"\s*:\s*"([^"]+)"')
    lead = meta(r'<p class="lead">(.*?)</p>')
    if not (title and url and lead):
        return None
    title = re.sub(r"<[^>]+>", "", title).strip()
    lead = re.sub(r"<[^>]+>", "", lead).strip()
    # «Шкала PHQ-9 · 9 вопросов» → scale + questions
    nq = re.search(r"(\d+)\s+вопрос", lead)
    scale = lead.split("·")[0].strip() if "·" in lead else ""
    # «Обновлено: 09.08.2026 · 2 минуты на прохождение» → «2 минуты»
    mins = meta(r'<p class="date">.*?·\s*([^<·]*?)\s*на прохождение')
    item = {
        "title": title,
        "description": desc or "",
        "image": image or "",
        "url": url,
        "date": date or "",
        "scale": scale,
        "questions": int(nq.group(1)) if nq else 0,
        "minutes_text": mins or "",
    }
    if image:
        size = image_size(image)
        if size:
            item["w"], item["h"] = size
    return item


def main() -> int:
    items = []
    for f in sorted(TESTY.glob("*.html")):
        if f.name == "index.html":
            continue
        data = extract(f.read_text(encoding="utf-8"))
        if data:
            items.append(data)
        else:
            print(f"SKIP (нет h1/canonical/lead): {f.name}")
    items.sort(key=lambda a: a["date"], reverse=True)
    OUT.write_text(
        json.dumps({"tests": items}, ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"OK: {len(items)} тестов -> {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

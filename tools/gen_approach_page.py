# -*- coding: utf-8 -*-
"""
Сборка страниц-лендингов о подходах для /podhody/.

Зачем раздел: на главной мы заявляем КПТ, ACT, схематерапию, Mindfulness
и CFT, но отдельных страниц под эти запросы нет — а у конкурента это
целый кластер лендингов (см. память seo-competitor-aura).

Видимый FAQ и разметка FAQPage собираются из одного списка, поэтому
разойтись не могут (см. CLAUDE.md — это требование к каждой странице).

⚠️ Формулировки о продукте: ИИ-психолог **опирается на принципы** подхода,
но терапию не проводит и специалиста не заменяет. Не менять на
«проводит КПТ» и подобное — это и неправда, и лишний юридический риск.

Запуск:  python tools/gen_approach_page.py
"""
import io, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_test_page import METRIKA, strip_tags, SITE, ASSET_V  # noqa: E402

OUT = "podhody"

FOOTER_LINKS = [
    ("../", "Главная"), ("../blog/", "Блог"), ("../testy/", "Тесты"),
    ("../privacy.html", "Конфиденциальность"), ("../about.html", "О проекте"),
    ("https://t.me/AI_Therapist_APP", "Telegram"),
    ("https://max.ru/u/f9LHodD0cOLipAu8wObtKCFFNq0tcwTb1FXJH4-p1ZsA73YJgBBY1-SNVxM", "MAX"),
]

DISCLAIMER = ('AI Therapist — приложение для самопомощи и эмоциональной поддержки. Оно опирается '
              'на принципы доказательных подходов, но не проводит психотерапию и не заменяет '
              'работу со специалистом. Если вы в кризисной ситуации, обратитесь за помощью: '
              '<strong>112</strong> — при угрозе жизни; <strong>+7 (495) 989-50-50</strong> — '
              'круглосуточная линия ЦЭПП МЧС России. Куда ещё можно обратиться бесплатно — '
              '<a href="../besplatnaya-psihologicheskaya-pomoshch.html">в справочнике помощи</a>.')


def build(a):
    url = "%s/%s/%s" % (SITE, OUT, a["slug"])
    # обложка 1200x630 = og:image и одновременно картинка на странице (один файл на оба применения)
    cover = a["slug"].replace(".html", "")
    faq_html = "\n".join('  <h3>%s</h3>\n  <p>%s</p>\n' % (q, ans) for q, ans in a["faq"])
    faq_ld = [{"@type": "Question", "name": q,
               "acceptedAnswer": {"@type": "Answer", "text": strip_tags(ans)}}
              for q, ans in a["faq"]]

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "Article", "headline": a["title"], "description": a["desc"],
         "inLanguage": "ru-RU", "datePublished": a["published"], "dateModified": a["modified"],
         "mainEntityOfPage": {"@type": "WebPage", "@id": url},
         "image": "%s/assets/%s/%s-cover.webp" % (SITE, OUT, cover),
         "author": {"@id": SITE + "/#organization"},
         "publisher": {"@id": SITE + "/#organization"},
         "about": {"@type": "Thing", "name": a["about"]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Главная", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Подходы", "item": SITE + "/" + OUT + "/"},
            {"@type": "ListItem", "position": 3, "name": a["crumb"]}]},
        {"@type": "FAQPage", "mainEntity": faq_ld}]}

    flinks = "\n".join('      <a href="%s"%s>%s</a>' %
                       (h, ' target="_blank" rel="noopener"' if h.startswith("http") else "", n)
                       for h, n in FOOTER_LINKS)

    return """<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="theme-color" content="#F6F2EA">
<title>{title}</title>
<meta name="description" content="{desc}">
<meta name="robots" content="index, follow, max-image-preview:large, max-snippet:-1">
<link rel="canonical" href="{url}">
<meta property="og:type" content="article">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="AI Therapist">
<meta property="og:locale" content="ru_RU">
<meta property="og:image" content="{SITE}/assets/podhody/{cover}-cover.webp">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" as="image" fetchpriority="high" href="../assets/podhody/{cover}-cover.webp">
<link rel="preload" as="font" type="font/woff2" crossorigin href="../assets/fonts/manrope-400-800-cyrillic.woff2">
<link rel="preload" as="font" type="font/woff2" crossorigin href="../assets/fonts/spectral-600-cyrillic.woff2">
<link rel="icon" type="image/webp" href="../assets/apps/aitherapist.webp">
<link rel="stylesheet" href="../assets/legal.css?v={ASSET_V}">
<script type="application/ld+json">
{ld}
</script>
</head>
<body>

<header class="lhead">
  <div class="row">
    <a class="logo" href="../"><img class="appmark" src="../assets/apps/aitherapist.webp" alt="" width="30" height="30"> AI Therapist</a>
    <a class="back" href="./"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg> Все подходы</a>
  </div>
</header>

<main class="legal">
  <p class="crumbs"><a href="../">Главная</a> → <a href="./">Подходы</a> → {crumb}</p>
  <h1>{h1}</h1>
  <p class="date">Обновлено: {mod_ru} · {mins} чтения</p>

  <div class="intro">
    <p>{intro}</p>
  </div>

  <figure>
    <img src="../assets/podhody/{cover}-cover.webp" alt="{cover_alt}" width="1200" height="630" fetchpriority="high">
  </figure>

  <div class="toc">
    <b>Содержание</b>
    <ol>
{toc}
    </ol>
  </div>

{body}

  <div class="cta-box">
    <p>{cta}</p>
    <a class="btn" href="../#chat">Попробовать бесплатно</a>
  </div>

  <h2 id="faq">Частые вопросы</h2>

{faq_html}
  <div class="note">{disclaimer}</div>

  <div class="eeat">
    <p>{eeat}</p>
    <p>Источники: {sources}.</p>
    <p>Кто отвечает за содержание сайта и по каким правилам мы готовим материалы — на странице <a href="../about.html">о проекте</a>.</p>
  </div>

  <p style="margin-top:26px"><a href="./">← Все подходы</a></p>
</main>

<footer>
  <div class="row">
    <div>© 2026 AI Therapist</div>
    <div class="flinks">
{flinks}
    </div>
  </div>
</footer>

{metrika}

</body>
</html>
""".format(title=a["title"], desc=a["desc"], url=url, SITE=SITE, ASSET_V=ASSET_V,
           ld=json.dumps(ld, ensure_ascii=False, indent=2),
           crumb=a["crumb"], h1=a["h1"], mod_ru=a["mod_ru"], mins=a["mins"],
           intro=a["intro"], toc=a["toc"], body=a["body"], cta=a["cta"],
           cover=cover, cover_alt=a["cover_alt"],
           faq_html=faq_html, disclaimer=DISCLAIMER, eeat=a["eeat"],
           sources=a["sources"], flinks=flinks, metrika=METRIKA)


def write(items):
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    for a in items:
        io.open(os.path.join(OUT, a["slug"]), "w", encoding="utf-8", newline="\n").write(build(a))
        print("sobrano:", OUT + "/" + a["slug"])


if __name__ == "__main__":
    from approaches_data import APPROACHES
    write(APPROACHES)

# -*- coding: utf-8 -*-
"""
Сборка страниц-опросников для /testy/.

Зачем генератор, а не ручная вёрстка: видимый FAQ и разметка FAQPage
обязаны совпадать слово-в-слово (см. CLAUDE.md), а это первое, что
разъезжается при правках руками. Здесь оба берутся из одного списка,
разойтись физически не могут.

Данные опросника уходят в <script type="application/json"> и читаются
общим движком assets/quiz.js — своей копии скрипта у страниц нет.

Запуск:  python tools/gen_test_page.py
"""
import io, json, os, re

SITE = "https://aitherapist.ru"
OUT = "testy"

FOOTER_LINKS = [
    ("../", "Главная"), ("./", "Тесты"), ("../blog/", "Блог"),
    ("../privacy.html", "Конфиденциальность"), ("../about.html", "О проекте"),
    ("https://t.me/AI_Therapist_APP", "Telegram"),
    ("https://max.ru/u/f9LHodD0cOLipAu8wObtKCFFNq0tcwTb1FXJH4-p1ZsA73YJgBBY1-SNVxM", "MAX"),
]

CRISIS = ('Опросник не ставит диагноз и не заменяет консультацию. Если вам прямо сейчас '
          'невыносимо тяжело или появляются мысли о том, чтобы причинить себе вред, позвоните: '
          '<strong>112</strong> — при угрозе жизни; <strong>+7 (495) 989-50-50</strong> — '
          'круглосуточная линия ЦЭПП МЧС России; <strong>8-800-2000-122</strong> — детям, '
          'подросткам и их родителям; <strong>051</strong> (с мобильного 8 (495) 051) — для Москвы.')

METRIKA = """<!-- Yandex.Metrika -->
<script type="text/javascript">
   window.__metrikaId = 110180781;
   (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
   m[i].l=1*new Date();
   for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
   k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
   (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
   ym(window.__metrikaId, "init", { clickmap:true, trackLinks:true, accurateTrackBounce:true, webvisor:true });
</script>
<noscript><div><img src="https://mc.yandex.ru/watch/110180781" style="position:absolute; left:-9999px;" alt="" /></div></noscript>
<!-- /Yandex.Metrika -->"""


def strip_tags(s):
    return re.sub(r"<[^>]+>", "", s)


def build(t):
    url = "%s/%s/%s" % (SITE, OUT, t["slug"])
    faq_html = "\n".join(
        '  <h3>%s</h3>\n  <p>%s</p>\n' % (q, a) for q, a in t["faq"])
    faq_ld = [{"@type": "Question", "name": q,
               "acceptedAnswer": {"@type": "Answer", "text": strip_tags(a)}}
              for q, a in t["faq"]]

    ld = {"@context": "https://schema.org", "@graph": [
        {"@type": "WebPage", "@id": url, "url": url, "name": t["title"],
         "description": t["desc"], "inLanguage": "ru-RU",
         "datePublished": t["published"], "dateModified": t["modified"],
         "isPartOf": {"@id": SITE + "/#website"},
         "publisher": {"@id": SITE + "/#organization"},
         "about": {"@type": "Thing", "name": t["about"]}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "Главная", "item": SITE + "/"},
            {"@type": "ListItem", "position": 2, "name": "Тесты", "item": SITE + "/" + OUT + "/"},
            {"@type": "ListItem", "position": 3, "name": t["crumb"]}]},
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
<meta property="og:type" content="website">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{ogdesc}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="AI Therapist">
<meta property="og:locale" content="ru_RU">
<meta property="og:image" content="{SITE}/assets/og.png">
<meta name="twitter:card" content="summary_large_image">
<link rel="preload" as="font" type="font/woff2" crossorigin href="../assets/fonts/manrope-400-800-cyrillic.woff2">
<link rel="preload" as="font" type="font/woff2" crossorigin href="../assets/fonts/spectral-600-cyrillic.woff2">
<link rel="icon" type="image/webp" href="../assets/apps/aitherapist.webp">
<link rel="stylesheet" href="../assets/legal.css">
<script type="application/ld+json">
{ld}
</script>
</head>
<body>

<header class="lhead">
  <div class="row">
    <a class="logo" href="../"><img class="appmark" src="../assets/apps/aitherapist.webp" alt="" width="30" height="30"> AI Therapist</a>
    <a class="back" href="./"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><line x1="19" y1="12" x2="5" y2="12"/><polyline points="12 19 5 12 12 5"/></svg> Все тесты</a>
  </div>
</header>

<main class="legal">
  <p class="crumbs"><a href="../">Главная</a> → <a href="./">Тесты</a> → {crumb}</p>
  <h1>{h1}</h1>
  <p class="date">Обновлено: {mod_ru} · {mins} на прохождение</p>

  <div class="intro">
    <p>{intro}</p>
  </div>

  <!-- ym-hide-content: ответы на тест не попадают в записи Вебвизора -->
  <section class="quiz ym-hide-content" id="quiz" aria-labelledby="quiz-stem">
    <p class="lead">{scale_name} · {nq} вопросов</p>
    <p class="stem" id="quiz-stem">{stem}</p>
    <form id="quiz-form"></form>
    <div class="qbar">
      <button type="button" id="quiz-go" disabled>Показать результат</button>
      <span class="count" id="quiz-count">Отвечено: 0 из {nq}</span>
    </div>
  </section>

  <section class="res" id="result" tabindex="-1" aria-live="polite">
    <div class="score"><span id="res-score">0</span> <small>из {max} баллов</small></div>
    <div class="scale" aria-hidden="true"></div>
    <div class="ticks" aria-hidden="true">{ticks}</div>
    <div class="lvl" id="res-level"></div>
    <div id="res-text"></div>
    <button type="button" class="again" id="res-again">Пройти заново</button>
  </section>

  <div class="note">{crisis}</div>

{body}

  <div class="cta-box">
    <p>{cta}</p>
    <a class="btn" href="../#chat">Попробовать бесплатно</a>
  </div>

  <h2 id="faq">Частые вопросы</h2>

{faq_html}
  <div class="eeat">
    <p>{eeat}</p>
    <p>Источники: {sources}.</p>
    <p>Кто отвечает за содержание сайта и по каким правилам мы готовим материалы — на странице <a href="../about.html">о проекте</a>.</p>
  </div>

  <p style="margin-top:26px"><a href="./">← Все психологические тесты</a></p>
</main>

<footer>
  <div class="row">
    <div>© 2026 AI Therapist</div>
    <div class="flinks">
{flinks}
    </div>
  </div>
</footer>

<script type="application/json" id="quiz-data">
{data}
</script>
<script src="../assets/quiz.js" defer></script>

{metrika}

</body>
</html>
""".format(title=t["title"], desc=t["desc"], ogdesc=t.get("ogdesc", t["desc"]),
           url=url, SITE=SITE, ld=json.dumps(ld, ensure_ascii=False, indent=2),
           crumb=t["crumb"], h1=t["h1"], mod_ru=t["mod_ru"], mins=t["mins"],
           intro=t["intro"], scale_name=t["scale_name"], nq=len(t["data"]["questions"]),
           stem=t["stem"], max=t["data"]["max"], ticks=t["ticks"], crisis=CRISIS,
           body=t["body"], cta=t["cta"], faq_html=faq_html, eeat=t["eeat"],
           sources=t["sources"], flinks=flinks,
           data=json.dumps(t["data"], ensure_ascii=False, indent=1), metrika=METRIKA)


def write(tests):
    if not os.path.isdir(OUT):
        os.makedirs(OUT)
    for t in tests:
        io.open(os.path.join(OUT, t["slug"]), "w", encoding="utf-8", newline="\n").write(build(t))
        print("собрано:", OUT + "/" + t["slug"])


if __name__ == "__main__":
    from tests_data import TESTS
    write(TESTS)

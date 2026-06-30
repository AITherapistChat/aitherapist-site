# AI Therapist — лендинг + веб-демо (CLAUDE.md)

Маркетинговый сайт и веб-версия чата для Android-приложения **AI Therapist** (ИИ-психолог).
Живёт на **GitHub Pages**, домен **https://aitherapist.ru**. Репозиторий: `AITherapistChat/aitherapist-site` (ветка `main`).

> Текущий статус/незакрытые задачи — в авто-памяти (`site-status-handoff.md`). Здесь — стабильное «как всё устроено».

## Деплой
- **Фронт:** просто `git push origin main` → GitHub Pages пересобирает ~1 мин. (Пуш в `main` требует явного разрешения пользователя.)
- **Supabase Edge Functions:** npx supabase CLI на этой Windows-машине НЕ работает. Деплой только через **Management API curl**:
  `curl -X POST "https://api.supabase.com/v1/projects/efniwpfjdfktfczgdpxm/functions/deploy?slug=<name>" -H "Authorization: Bearer <sbp>" -F 'metadata={"name":"<name>","entrypoint_path":"index.ts","verify_jwt":false};type=application/json' -F "file=@supabase/functions/<name>/index.ts;type=application/typescript"`
- **БД/секреты/цены:** тоже Management API (`/database/query`, `/secrets`). Прод-деплой бэкенда — только с явного разрешения пользователя.
- Проверять прод после пуша: `curl https://aitherapist.ru/...` (Pages кэширует ~1–2 мин).

## Структура
- `index.html` — весь лендинг + демо-чат (инлайн CSS/JS, тема «шалфей+песок»).
- `blog/` — статьи (используют `assets/legal.css` + инлайн-стили). `blog/index.html` — хаб.
- `privacy.html` / `terms.html` / `oferta.html` — юр-страницы (на `assets/legal.css`).
- `assets/` — `legal.css`, `blog/*.webp` (картинки статей), `apps/`, `screenshots/`, `vendor/`.
- `supabase/functions/<name>/index.ts` — исходники веб-функций (папка `supabase/` в .gitignore — в git НЕ коммитится, только деплоится).
- `robots.txt`, `sitemap.xml` — в корне.

## Бэкенд (Supabase, project ref `efniwpfjdfktfczgdpxm`)
Веб-функции (все `verify_jwt=false`, эндпоинт `https://efniwpfjdfktfczgdpxm.functions.supabase.co/<name>`):
- **chat-web** — прокси к DeepSeek (web-ключ `DEEPSEEK_API_KEY_WEB`). Режимы: анон-демо (stateless) и авторизованный (лимит 5/сутки через RPC `enforce_daily_limit_and_increment`, триал 24ч, премиум). Спец-ветки в теле запроса: `{status:true}` (статус без DeepSeek/без инкремента), `{plans:true}` (тарифы из `premium_plans`). Отдаёт заголовки `X-Remaining`/`X-Plan-Until`. Память контекста: free 15, премиум/триал 30 (как в приложении). Учёт токенов → RPC `log_token_usage` (`web-anon` для демо).
- **vk-auth** — проверяет VK access_token, upsert `users` (device_id `vk:<id>`), отдаёт HMAC-сессию + `premium_until`/`trial_until`.
- **pay-web** — Robokassa: цена из `premium_plans` (не из клиента), InvId из БД, подпись MD5 на сервере. SuccessURL/FailURL без query-параметров (Robokassa их не принимает при GET).
- **robokassa-result** — вебхук (общий с приложением, исходник в репо приложения). Проверяет подпись `MD5(OutSum:InvId:Password#2)` (OutSum как прислан) → иначе 403. Грантит премиум по `device_id`.

🚫 **Не трогать `chat-tuned`** — это прод-бэкенд Android-приложения. Веб строго изолирован (отдельные функции, отдельный ключ).

## РФ-доступ (важно)
Браузерные запросы к `*.supabase.co` в РФ нестабильны. Фронт (`apiFetch`) сначала пробует прямой Supabase (со стримингом), при сетевой ошибке/таймауте уходит на **Яндекс-прокси** `https://functions.yandexcloud.net/d4enpb1jd6ok1i1p6ffd` (CORS-копия, non-streaming → «фейк-печать»). Есть фоновая проба при загрузке + `?proxy=1` для теста.

## Конвенции
- **Тема:** `--teal #557A51`, `--teal-deep #41633E`, `--lav` (песок) `#C99A6E`, `--bg #F7F4EE`, `--bg2 #EFEBE1`. Заголовки — шрифт **Spectral** (serif), текст — **Manrope**.
- **Картинки:** только **WebP**, лёгкие (GitHub Pages ограничен по месту). Инфографику режу из исходников **строго по белым линиям-разделителям** — гаттеры искать **по каждой колонке отдельно** (панели бывают разной высоты!), Python+Pillow.
- **SEO у каждой статьи:** уникальные title/description, canonical, OG, JSON-LD (Article + BreadcrumbList + FAQPage), счётчик Метрики (ID `110180781`), запись в `sitemap.xml`, внутренние ссылки в кластер. FAQ: видимый текст обязан **совпадать слово-в-слово** с разметкой FAQPage. E-E-A-T: автор + источник (ВОЗ) + дисклеймер.
- **Метрика** (`110180781`) и verification-теги (yandex/google) — на всех страницах.

## Как писать статью в блог — SEO-рецепт (следовать КАЖДЫЙ раз)
Эталон для копирования: `blog/kak-spravitsya-s-trevogoy.html`. Объём **1500–2000 слов**, язык простой, без воды, практический (шаги/списки/таблицы).

**1. Тема = интент, не ключ.** Берём проблему пользователя и закрываем её ПОЛНОСТЬЮ: что это → почему возникает → как проявляется (симптомы) → что делать сейчас → долгосрочные решения → ошибки → когда к врачу → FAQ. Одна статья ловит 20–100 long-tail запросов.

**2. Структура (порядок H2 = «мини-учебник», Google это любит):**
- `<h1>` — проблема с цифрой/болью в заголовке.
- intro (`.intro`) — первый абзац = **прямой ответ** (под featured snippet), 2–4 предложения.
- `<figure>` hero-обложка (WebP).
- `.toc` — оглавление с якорями на все H2.
- H2-разделы по схеме из п.1, каждый начинается с **прямого утверждения**.
- Практика: нумерованные шаги (`.steps-list`), маркеры, **сравнительные таблицы** (`.cmp`) — отлично ранжируются.
- CTA-блок (`.cta-box`) → `../index.html#chat`.
- `.note` — дисклеймер + телефон **8-800-2000-122**.
- H2 `id="faq"` — Частые вопросы.
- `.eeat` — блок E-E-A-T (см. п.5).

**3. `<head>`:** уникальные `<title>` (с цифрой/выгодой) и `<meta description>`; `<link rel=canonical>`; OG (og:image = обложка статьи `assets/blog/<slug>-cover.webp`); шрифты; `legal.css`.

**4. JSON-LD `@graph`** (3 объекта): `Article` (headline/description/image/datePublished/author=Organization AI Therapist/publisher) + `BreadcrumbList` (Главная→Блог→статья) + `FAQPage`.

**5. FAQ — «золото» (тут легко ошибиться):** 4 вопроса под long-tail; ответ — **2–4 предложения, прямо**. ⚠️ Видимый текст ответа на странице обязан **совпадать слово-в-слово** с текстом в `FAQPage`-разметке, иначе сниппет не покажется. (В разметке без HTML-тегов; в видимом можно обернуть слово ссылкой — текст всё равно совпадает.)

**6. E-E-A-T** (для психологии критично): блок `.eeat` в конце — «Материал подготовлен командой AI Therapist… основан на КПТ/ACT/Mindfulness» + ссылка на авторитетный источник (`rel="noopener nofollow"`) + дисклеймер «не заменяет врача». ⚠️ Источник должен быть **по теме статьи**, а не один и тот же на весь блог (иначе он не подкрепляет контент и сигнал E-E-A-T слабее). Подбирай релевантный: тревога → ВОЗ `https://www.who.int/news-room/fact-sheets/detail/anxiety-disorders`; паника → NHS `https://www.nhs.uk/mental-health/conditions/panic-disorder/`; сон → NHS `https://www.nhs.uk/conditions/insomnia/`. Для новой темы — найди свою страницу ВОЗ/NHS и проверь, что она живая.

**7. Внутренняя перелинковка = кластер.** Каждая статья ссылается на 1–2 соседние по теме (тревога↔паника↔сон↔выгорание↔навязчивые мысли), желательно в обе стороны. Это главный долгосрочный рычаг роста.

**8. Картинки:** WebP, лёгкие; режу из исходника **строго по белым гаттерам (по колонкам!)**; hero на всю ширину + inline-схемы (`figure.narrow`) с `<figcaption>`; обязательно осмысленный `alt` (с ключом) и `width/height` (под реальный размер кропа, чтобы не было сдвига).

**9. Зарегистрировать новую статью (НЕ забыть):**
- добавить URL в `sitemap.xml`;
- добавить карточку в `blog/index.html` (хаб — там ВСЕ статьи, сетка `auto-fill`, растёт бесконечно);
- на главной `index.html` витрина «Статьи» показывает **только 3 новейшие** (чтобы блок не рос) — вставить новую карточку **сверху** и **удалить нижнюю** (см. комментарий в `.blog-grid`); полный список ведёт кнопка «Все статьи →»;
- вставить блок Яндекс.Метрики (ID `110180781`) перед `</body>` (скопировать из существующей статьи).

**10. Заголовки/CTR:** формат «Тема: N способов/шагов, которые работают» или «X: почему возникает и что делать». Цифры + конкретика + боль.

**11. Обновление (раз в 3–6 мес):** расширять FAQ/семантику, обновлять `dateModified` — часто даёт +50–200% трафика без новых статей.

## Перед публичным запуском
🔐 Ротация секретов, светившихся в чате (Robokassa #1/#2, Supabase sbp-токен, GitHub PAT в remote, DeepSeek web-ключ, VK secret).

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

## Перед публичным запуском
🔐 Ротация секретов, светившихся в чате (Robokassa #1/#2, Supabase sbp-токен, GitHub PAT в remote, DeepSeek web-ключ, VK secret).

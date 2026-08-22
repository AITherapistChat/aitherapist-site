# -*- coding: utf-8 -*-
"""
Заливает статику сайта в Yandex Object Storage (S3-совместимый API).

Зачем: GitHub Pages в РФ фильтруется по TLS (см. CLAUDE.md, раздел «Хостинг»),
поэтому боевая отдача живёт в бакете Yandex Object Storage за Yandex CDN.
Репозиторий остаётся исходником — этот скрипт синхронизирует его с бакетом.

    pip install boto3
    set YC_S3_KEY_ID=...        (в PowerShell: $env:YC_S3_KEY_ID='...')
    set YC_S3_SECRET=...
    python tools/deploy_s3.py                 # залить изменённое
    python tools/deploy_s3.py --prune         # + удалить из бакета лишнее
    python tools/deploy_s3.py --dry-run       # только показать план

Заливается лишь то, что реально публикуется: служебные файлы репозитория
(tools/, supabase/, yandex/, CLAUDE.md, BRIEF.md, CNAME…) в бакет не попадают.
"""
import argparse
import hashlib
import mimetypes
import os
import sys
from pathlib import Path

try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    sys.exit("Нужен boto3:  pip install boto3")

ROOT = Path(__file__).resolve().parent.parent
ENDPOINT = "https://storage.yandexcloud.net"
REGION = "ru-central1"
BUCKET = os.environ.get("YC_S3_BUCKET", "aitherapist.ru")

# Папки и файлы, которых на проде быть не должно.
SKIP_DIRS = {".git", ".github", ".claude", "tools", "supabase", "yandex", "__pycache__"}
SKIP_FILES = {"CLAUDE.md", "BRIEF.md", "VK.md", ".gitignore", ".nojekyll", "CNAME",
              "assets/og-card.html"}

# Content-Type для того, что mimetypes на Windows угадывает неверно или никак.
TYPES = {
    ".webp": "image/webp",
    ".woff2": "font/woff2",
    ".svg": "image/svg+xml",
    ".json": "application/json; charset=utf-8",
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".xml": "application/xml; charset=utf-8",
    ".txt": "text/plain; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".ico": "image/x-icon",
}

# HTML и карты сайта обязаны обновляться сразу после деплоя, остальное можно кэшировать:
# имена файлов не версионированы, поэтому сутки — разумный потолок, шрифты живут дольше.
def cache_control(rel: str) -> str:
    if rel.endswith((".html", ".xml", ".txt", ".json")):
        return "no-cache"
    if "/fonts/" in rel:
        return "public, max-age=2592000"
    return "public, max-age=86400"


def content_type(rel: str) -> str:
    ext = Path(rel).suffix.lower()
    if ext in TYPES:
        return TYPES[ext]
    guess, _ = mimetypes.guess_type(rel)
    return guess or "application/octet-stream"


def local_files() -> dict[str, Path]:
    """Все публикуемые файлы: ключ в бакете → путь на диске."""
    out: dict[str, Path] = {}
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(ROOT).as_posix()
        if set(rel.split("/")[:-1]) & SKIP_DIRS or rel in SKIP_FILES:
            continue
        out[rel] = path
    return out


def etag(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def remote_files(s3) -> dict[str, str]:
    """Что уже лежит в бакете: ключ → ETag (md5 для однокусочных загрузок)."""
    out: dict[str, str] = {}
    token = None
    while True:
        kw = {"Bucket": BUCKET, "MaxKeys": 1000}
        if token:
            kw["ContinuationToken"] = token
        resp = s3.list_objects_v2(**kw)
        for obj in resp.get("Contents", []):
            out[obj["Key"]] = obj["ETag"].strip('"')
        if not resp.get("IsTruncated"):
            return out
        token = resp["NextContinuationToken"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prune", action="store_true", help="удалить из бакета то, чего нет в репо")
    ap.add_argument("--dry-run", action="store_true", help="только показать, что будет сделано")
    args = ap.parse_args()

    key_id, secret = os.environ.get("YC_S3_KEY_ID"), os.environ.get("YC_S3_SECRET")
    if not (key_id and secret):
        return print("Нет YC_S3_KEY_ID / YC_S3_SECRET в окружении.") or 1

    s3 = boto3.client("s3", endpoint_url=ENDPOINT, region_name=REGION,
                      aws_access_key_id=key_id, aws_secret_access_key=secret)

    local = local_files()
    try:
        remote = remote_files(s3)
    except ClientError as e:
        return print(f"Не читается бакет {BUCKET}: {e}") or 1

    changed = [rel for rel, p in sorted(local.items()) if remote.get(rel) != etag(p)]
    extra = sorted(set(remote) - set(local)) if args.prune else []

    print(f"Бакет {BUCKET}: в репо {len(local)} файлов, в бакете {len(remote)}.")
    print(f"К заливке {len(changed)}" + (f", к удалению {len(extra)}" if args.prune else ""))

    for rel in changed:
        print(("  [dry] " if args.dry_run else "  up  ") + rel)
        if not args.dry_run:
            s3.upload_file(str(local[rel]), BUCKET, rel, ExtraArgs={
                "ContentType": content_type(rel),
                "CacheControl": cache_control(rel),
            })
    for rel in extra:
        print(("  [dry] " if args.dry_run else "  del ") + rel)
        if not args.dry_run:
            s3.delete_object(Bucket=BUCKET, Key=rel)

    if not changed and not extra:
        print("Всё совпадает — заливать нечего.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

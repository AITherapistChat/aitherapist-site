# -*- coding: utf-8 -*-
"""
Кладёт в бакет голосовые модели для озвучки в Android-приложении.

Зачем: приложение тянет модели Piper с github.com, а он в РФ фильтруется по
TLS — ровно поэтому сайт в своё время уехал с GitHub Pages в Object Storage.
Когда модель не скачалась, озвучка у человека просто молча не работает.
Приложение сначала пробует `https://aitherapist.ru/tts/...`, и только если
там 404 — идёт на github, так что заливка безопасна и обратима.

    pip install boto3
    $env:YC_S3_KEY_ID='...'; $env:YC_S3_SECRET='...'
    python tools/upload_tts_models.py --dry-run
    python tools/upload_tts_models.py

Файлы качаются во временную папку и заливаются под теми же именами, что ждёт
приложение (см. PiperTTS.kt): архивы голосов и espeak-ng-data в /tts/,
правленый русский словарь — в /tts/ru_dict/.

⚠️ В репозитории этих файлов НЕТ и быть не должно — сто мегабайт в git не
нужны. Поэтому `deploy_s3.py --prune` префикс `tts/` не трогает (см. там
PRUNE_KEEP_PREFIXES), иначе ближайший деплой сайта снёс бы модели из бакета.
"""
import argparse
import os
import sys
import tempfile
import urllib.request
from pathlib import Path

try:
    import boto3
except ImportError:
    sys.exit("Нужен boto3:  pip install boto3")

ENDPOINT = "https://storage.yandexcloud.net"
REGION = "ru-central1"
BUCKET = os.environ.get("YC_S3_BUCKET", "aitherapist.ru")
PREFIX = "tts/"

SHERPA = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"
MITROKUN = "https://raw.githubusercontent.com/mitrokun/espeak-ng-data/main/espeak-ng-data"

# (ключ в бакете, откуда качать). Голоса — те же имена, что в PiperTTS.Voice.
FILES = [
    ("espeak-ng-data.tar.bz2", f"{SHERPA}/espeak-ng-data.tar.bz2"),
    ("vits-piper-ru_RU-irina-medium-int8.tar.bz2",
     f"{SHERPA}/vits-piper-ru_RU-irina-medium-int8.tar.bz2"),
    ("vits-piper-ru_RU-dmitri-medium-int8.tar.bz2",
     f"{SHERPA}/vits-piper-ru_RU-dmitri-medium-int8.tar.bz2"),
] + [
    (f"ru_dict/{name}", f"{MITROKUN}/{name}")
    for name in ("ru_dict", "phondata", "phondata-manifest", "phonindex", "phontab")
]

# Модели неизменны и версионированы именем — год кэша безопасен.
CACHE = "public, max-age=31536000, immutable"


def download(url: str, dest: Path) -> None:
    print(f"  качаю {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "aitherapist-deploy"})
    with urllib.request.urlopen(req) as resp, dest.open("wb") as out:
        while chunk := resp.read(1 << 20):
            out.write(chunk)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="только показать план")
    ap.add_argument("--force", action="store_true", help="перезалить даже то, что уже в бакете")
    args = ap.parse_args()

    key_id, secret = os.environ.get("YC_S3_KEY_ID"), os.environ.get("YC_S3_SECRET")
    if not (key_id and secret):
        return print("Нет YC_S3_KEY_ID / YC_S3_SECRET в окружении.") or 1

    s3 = boto3.client("s3", endpoint_url=ENDPOINT, region_name=REGION,
                      aws_access_key_id=key_id, aws_secret_access_key=secret)

    existing = set()
    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=BUCKET, Prefix=PREFIX):
        for obj in page.get("Contents", []):
            existing.add(obj["Key"])

    todo = [(k, u) for k, u in FILES if args.force or PREFIX + k not in existing]
    print(f"Бакет {BUCKET}: под {PREFIX} уже {len(existing)} файлов, к заливке {len(todo)}.")
    if not todo:
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        for key, url in todo:
            target = PREFIX + key
            if args.dry_run:
                print(f"  [dry] {target}  <- {url}")
                continue
            print(f"  up  {target}")
            local = Path(tmp) / key.replace("/", "_")
            download(url, local)
            s3.upload_file(str(local), BUCKET, target, ExtraArgs={
                "ContentType": "application/octet-stream",
                "CacheControl": CACHE,
            })
            local.unlink()
    print("Готово. Проверка: curl -I https://aitherapist.ru/tts/espeak-ng-data.tar.bz2")
    return 0


if __name__ == "__main__":
    sys.exit(main())

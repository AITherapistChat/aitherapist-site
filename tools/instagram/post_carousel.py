"""Публикация карусели в Instagram @ai_therapist_ через Instagram Graph API.

    python tools/instagram/post_carousel.py <папка_с_jpg> <файл_подписи.txt> [--dry-run]

Картинки (JPEG, 1080×1350, сортировка по имени) заливаются в бакет под префикс
ig/<имя папки>/ и отдаются Instagram'у прямым адресом бакета — мимо CDN, чтобы
не упереться в кэш и запрет по IP. Дальше: контейнер на каждый слайд →
контейнер карусели → media_publish.

Токен: переменная IG_TOKEN или файл TOKEN_FILE (вне репозитория).
S3-ключи: YC_S3_KEY_ID / YC_S3_SECRET или файл S3_KEY_FILE.
После публикации слайды, подпись, лист-превью и ссылка на пост копируются
в ARCHIVE/<имя папки>.
"""
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import boto3

TOKEN_FILE = Path(r"C:\Users\XE\Desktop\gpt\сайт\instagram_token.txt")
ARCHIVE = Path(r"C:\Users\XE\Desktop\gpt\сайт\для инсты")
S3_KEY_FILE = Path(r"C:\Users\XE\Desktop\gpt\сайт\яндекс доступ облако\s3_deploy_key.txt")
BUCKET = "aitherapist.ru"
ENDPOINT = "https://storage.yandexcloud.net"
API = "https://graph.instagram.com/v23.0"


def token():
    return os.environ.get("IG_TOKEN") or TOKEN_FILE.read_text(encoding="utf-8").strip()


def s3_keys():
    kid, sec = os.environ.get("YC_S3_KEY_ID"), os.environ.get("YC_S3_SECRET")
    if kid and sec:
        return kid, sec
    text = S3_KEY_FILE.read_text(encoding="utf-8")
    found = dict(re.findall(r"\$env:(YC_S3_KEY_ID|YC_S3_SECRET)='([^']+)'", text))
    return found["YC_S3_KEY_ID"], found["YC_S3_SECRET"]


def api(method, path, **params):
    params["access_token"] = token()
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"{method} {path}: {e.code} {e.read().decode()}")


def wait_ready(cid):
    for _ in range(60):
        st = api("GET", cid, fields="status_code,status")
        if st.get("status_code") == "FINISHED":
            return
        if st.get("status_code") == "ERROR":
            sys.exit(f"контейнер {cid}: {st}")
        time.sleep(3)
    sys.exit(f"контейнер {cid} не дошёл до FINISHED")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv
    folder, caption_file = Path(args[0]), Path(args[1])
    images = sorted(p for p in folder.glob("*.jpg") if not p.name.startswith("_"))
    caption = caption_file.read_text(encoding="utf-8").strip()
    if not 2 <= len(images) <= 20:
        sys.exit(f"в карусели 2–20 слайдов, найдено {len(images)}")
    print(f"{len(images)} слайдов, подпись {len(caption)} симв.")
    if dry:
        return

    kid, sec = s3_keys()
    s3 = boto3.client("s3", endpoint_url=ENDPOINT, region_name="ru-central1",
                      aws_access_key_id=kid, aws_secret_access_key=sec)
    urls = []
    for p in images:
        key = f"ig/{folder.name}/{p.name}"
        s3.upload_file(str(p), BUCKET, key, ExtraArgs={"ContentType": "image/jpeg"})
        urls.append(f"{ENDPOINT}/{BUCKET}/{key}")
    print("залито:", urls[0], "…")

    items = []
    for u in urls:
        cid = api("POST", "me/media", image_url=u, is_carousel_item="true")["id"]
        items.append(cid)
    for cid in items:
        wait_ready(cid)
    print("слайды приняты:", len(items))

    carousel = api("POST", "me/media", media_type="CAROUSEL",
                   children=",".join(items), caption=caption)["id"]
    wait_ready(carousel)
    media_id = api("POST", "me/media_publish", creation_id=carousel)["id"]
    link = api("GET", media_id, fields="permalink").get("permalink")
    print("опубликовано:", media_id, link)

    dst = ARCHIVE / folder.name
    dst.mkdir(parents=True, exist_ok=True)
    for p in images + [caption_file] + list(folder.glob("_sheet.jpg")):
        shutil.copy2(p, dst / p.name)
    (dst / "ссылка.txt").write_text(f"{link}\nmedia_id {media_id}\n", encoding="utf-8")
    print("архив:", dst)


if __name__ == "__main__":
    main()

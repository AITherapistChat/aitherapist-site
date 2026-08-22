# -*- coding: utf-8 -*-
"""Ставит 16 постов месяца в отложку ВК.
Картинку грузим пользовательским токеном, пост — токеном сообщества.
"""
import sys, os, time, json, datetime
from vkapi import call
import vkphoto
from month import PLAN

sys.stdout.reconfigure(encoding='utf-8')
GROUP = -241004340
IMGDIR = r'C:\Users\XE\AppData\Local\Temp\vkimg3'


def upload_retry(path, tries=4):
    last = None
    for i in range(tries):
        try:
            return vkphoto.upload(path)
        except Exception as e:
            last = e
            print('   повтор загрузки:', str(e)[:120]); time.sleep(5 + 5 * i)
    raise last


def ts(date, hhmm):
    d = datetime.datetime.strptime(date + ' ' + hhmm, '%Y-%m-%d %H:%M')
    return int(time.mktime(d.timetuple()))


ok = 0
START = int(sys.argv[1]) if len(sys.argv) > 1 else 0
for date, hhmm, key, text in PLAN[START:]:
    img = os.path.join(IMGDIR, key + '.jpg')
    if not os.path.exists(img):
        print(date, 'НЕТ КАРТИНКИ', key)
        continue
    att = upload_retry(img)
    r = call('group', 'wall.post', {
        'owner_id': GROUP, 'from_group': 1, 'message': text,
        'attachments': att, 'publish_date': ts(date, hhmm)})
    good = 'response' in r
    ok += good
    print('%s %s  %-16s %s' % (date, hhmm, key,
                               'ок' if good else json.dumps(r, ensure_ascii=False)[:150]))
    time.sleep(3)

print('поставлено в отложку:', ok, 'из', len(PLAN))

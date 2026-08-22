# -*- coding: utf-8 -*-
"""python vkphoto.py <path-to-image> -> печатает attachment вида photo-241004340_123"""
import sys, os, io, json, mimetypes, urllib.request, uuid
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vkapi import call

GROUP = 241004340

def to_jpg(src):
    from PIL import Image
    im = Image.open(src).convert('RGB')
    dst = os.path.join(os.environ.get('TEMP', '.'), 'vkup_%s.jpg' % uuid.uuid4().hex[:8])
    im.save(dst, quality=93)
    return dst

def post_file(url, path):
    boundary = '----vk' + uuid.uuid4().hex
    with open(path, 'rb') as f:
        content = f.read()
    body = b''
    body += ('--%s\r\nContent-Disposition: form-data; name="photo"; filename="%s"\r\n'
             'Content-Type: image/jpeg\r\n\r\n' % (boundary, os.path.basename(path))).encode()
    body += content + ('\r\n--%s--\r\n' % boundary).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={'Content-Type': 'multipart/form-data; boundary=' + boundary})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())

def upload(src):
    jpg = to_jpg(src)
    srv = call('user', 'photos.getWallUploadServer', {'group_id': GROUP})['response']
    up = post_file(srv['upload_url'], jpg)
    r = call('user', 'photos.saveWallPhoto', {
        'group_id': GROUP, 'server': up['server'],
        'photo': up['photo'], 'hash': up['hash']})
    if 'response' not in r:
        raise RuntimeError('saveWallPhoto: %s' % r)
    saved = r['response'][0]
    os.remove(jpg)
    return 'photo%s_%s' % (saved['owner_id'], saved['id'])

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    print(upload(sys.argv[1]))

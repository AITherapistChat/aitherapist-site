# -*- coding: utf-8 -*-
"""python vkapi.py {group|user} <method> key=value ... [key@file.txt]"""
import sys, io, os, re, json, urllib.parse, urllib.request

D = r'C:\Users\XE\Desktop\gpt\сайт\вк доступ группа'
FILES = {'group': 'токен.txt', 'user': 'токен пользователя .txt'}

def token(kind):
    s = io.open(os.path.join(D, FILES[kind]), encoding='utf-8').read().strip()
    m = re.search(r'access_token=([^&\s#]+)', s)
    return m.group(1) if m else s.replace(' ', '').replace('\n', '')

def call(kind, method, params):
    p = dict(params)
    p['access_token'] = token(kind)
    p['v'] = '5.199'
    data = urllib.parse.urlencode(p).encode()
    req = urllib.request.Request('https://api.vk.com/method/' + method, data=data)
    return json.loads(urllib.request.urlopen(req, timeout=40).read().decode('utf-8'))

if __name__ == '__main__':
    kind, method = sys.argv[1], sys.argv[2]
    params = {}
    for kv in sys.argv[3:]:
        if '@' in kv.split('=')[0] or ('@' in kv and '=' not in kv.split('@')[0]):
            k, f = kv.split('@', 1)
            params[k] = io.open(f, encoding='utf-8').read()
        else:
            k, v = kv.split('=', 1)
            params[k] = v
    out = call(kind, method, params)
    sys.stdout.reconfigure(encoding='utf-8')
    print(json.dumps(out, ensure_ascii=False)[:1200])

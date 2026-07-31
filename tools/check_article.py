# -*- coding: utf-8 -*-
"""Проверка статьи: JSON-LD валиден, FAQ visible == schema, объём, ссылки, H2."""
import json, re, sys, io, os

path = sys.argv[1]
html = io.open(path, encoding='utf-8').read()

# --- JSON-LD ---
m = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.S)
data = json.loads(m.group(1))
types = [o['@type'] for o in data['@graph']]
print('JSON-LD OK, объекты:', types)

faq = [o for o in data['@graph'] if o['@type'] == 'FAQPage'][0]['mainEntity']
print('FAQ в разметке:', len(faq))

# --- видимый FAQ ---
faq_html = html.split('<h2 id="faq">')[1].split('<h2>Читать также</h2>')[0]
pairs = re.findall(r'<h3>(.*?)</h3>\s*<p>(.*?)</p>', faq_html, re.S)
print('FAQ видимых:', len(pairs))

def clean(s):
    s = re.sub(r'<[^>]+>', '', s)
    s = s.replace('&nbsp;', ' ').replace('&laquo;', '«').replace('&raquo;', '»')
    s = s.replace('&mdash;', '—').replace('&amp;', '&')
    return re.sub(r'\s+', ' ', s).strip()

bad = 0
for i, q in enumerate(faq):
    if i >= len(pairs):
        print('!! нет видимого блока для:', q['name']); bad += 1; continue
    vq, va = clean(pairs[i][0]), clean(pairs[i][1])
    sq, sa = clean(q['name']), clean(q['acceptedAnswer']['text'])
    if vq != sq:
        print('!! ВОПРОС расходится:\n  visible:', vq, '\n  schema :', sq); bad += 1
    if va != sa:
        print('!! ОТВЕТ расходится (Q%d):' % (i+1))
        print('  visible:', va)
        print('  schema :', sa)
        bad += 1
print('РАСХОЖДЕНИЙ:', bad)

# --- объём ---
body = html.split('<main class="legal">')[1].split('</main>')[0]
body = re.sub(r'<script.*?</script>', ' ', body, flags=re.S)
text = clean(body)
words = len(re.findall(r'[А-Яа-яЁёA-Za-z0-9]+', text))
print('СЛОВ:', words, '| минут чтения ~', round(words/200))

# --- H2 / картинки / ссылки ---
h2 = re.findall(r'<h2[^>]*>(.*?)</h2>', body, re.S)
print('H2:', len(h2))
figs = re.findall(r'<!-- FIGURE: ([a-z0-9\-\.]+)', body)
print('Заглушек FIGURE:', len(figs), figs)
links = sorted(set(re.findall(r'href="([a-z0-9\-]+\.html)"', body)))
print('Внутренние ссылки:', links)
for l in links:
    p = os.path.join(os.path.dirname(path), l)
    if not os.path.exists(p):
        print('  !! БИТАЯ:', l)

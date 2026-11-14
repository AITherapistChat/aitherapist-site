"""Exercise the actual PHQ-15 page and shared quiz engine in headless Chrome."""
import base64
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

from websockets.sync.client import connect

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "testy" / "telesnye-simptomy-phq-15.html"
CHROME = Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe")

SCRIPT = r"""
<script>
document.addEventListener('DOMContentLoaded', () => {
  const results = [];
  const fields = [...document.querySelectorAll('#quiz-form fieldset')];
  const go = document.getElementById('quiz-go');
  const again = document.getElementById('res-again');
  function choose(i, value, label) {
    const options = [...fields[i].querySelectorAll('label')];
    const option = options.find(x => label ? x.textContent.trim() === label : Number(x.querySelector('input').value) === value);
    if (!option) throw Error('Missing option ' + i + ': ' + value + '/' + label);
    option.querySelector('input').click();
  }
  function run(target, expected) {
    again.click();
    const values = Array(15).fill(0);
    let left = target;
    for (let i=0; i<15; i++) { values[i] = Math.min(2, left); left -= values[i]; }
    for (let i=0; i<15; i++) choose(i, values[i]);
    if (go.disabled) throw Error('Submit stays disabled at ' + target);
    if (document.getElementById('quiz-count').textContent !== 'Отвечено: 15 из 15') throw Error('Wrong count');
    go.click();
    const actual = Number(document.getElementById('res-score').textContent);
    const name = document.getElementById('res-level').textContent;
    if (actual !== target || name !== expected) throw Error('Wrong result ' + target + ': ' + actual + ', ' + name);
    if (!document.getElementById('result').classList.contains('on')) throw Error('Result hidden');
    results.push([target, name]);
  }
  try {
    if (fields.length !== 15 || !go.disabled) throw Error('Initial state');
    choose(0, 0);
    if (!go.disabled) throw Error('Incomplete quiz can submit');
    [[0,'Минимальная нагрузка симптомов'],[4,'Минимальная нагрузка симптомов'],
     [5,'Низкая нагрузка симптомов'],[9,'Низкая нагрузка симптомов'],
     [10,'Средняя нагрузка симптомов'],[14,'Средняя нагрузка симптомов'],
     [15,'Высокая нагрузка симптомов'],[30,'Высокая нагрузка симптомов']]
      .forEach(([score,name]) => run(score,name));
    again.click();
    for(let i=0; i<15; i++) choose(i,0);
    choose(3,0,'Не относится ко мне');
    choose(13,0,'Почти каждый день');
    choose(14,0,'Почти каждый день');
    go.click();
    if (document.getElementById('res-score').textContent !== '4') throw Error('Sleep/fatigue recode or N/A');
    again.click();
    if (!go.disabled || document.getElementById('quiz-count').textContent !== 'Отвечено: 0 из 15' || document.getElementById('result').classList.contains('on')) throw Error('Reset');
    document.body.insertAdjacentHTML('beforeend','<pre id="browser-check">'+JSON.stringify({ok:true,results,mobileWidth:innerWidth,docWidth:document.documentElement.scrollWidth})+'</pre>');
  } catch(e) {document.body.insertAdjacentHTML('beforeend','<pre id="browser-check">'+JSON.stringify({ok:false,error:String(e)})+'</pre>');}
});
</script>
"""

def main():
    assert CHROME.exists(), CHROME
    html = PAGE.read_text(encoding="utf-8")
    # Analytics is unrelated to the quiz and should not delay the local check.
    html = re.sub(r'<!-- Yandex\.Metrika.*?<!-- /Yandex\.Metrika -->', '', html, flags=re.S)
    html = html.replace("</body>", SCRIPT + "\n</body>")
    test_page = PAGE.parent / "_phq15_browser_check.html"
    try:
        test_page.write_text(html, encoding="utf-8")
        with tempfile.TemporaryDirectory() as profile:
            proc = subprocess.Popen([
                str(CHROME), "--headless=new", "--disable-gpu", "--no-sandbox",
                "--allow-file-access-from-files", "--disable-background-networking",
                "--disable-extensions", "--remote-debugging-port=0", "--remote-allow-origins=*",
                f"--user-data-dir={profile}", "about:blank",
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                active_port = Path(profile) / "DevToolsActivePort"
                for _ in range(100):
                    if active_port.exists():
                        break
                    time.sleep(.1)
                assert active_port.exists(), "Chrome debugging port did not start"
                port = active_port.read_text().splitlines()[0]
                tabs = json.load(urlopen(f"http://127.0.0.1:{port}/json/list"))
                tab = next(t for t in tabs if t["type"] == "page")
                with connect(tab["webSocketDebuggerUrl"], max_size=10_000_000) as ws:
                    seq = 0
                    def cdp(method, params=None):
                        nonlocal seq
                        seq += 1
                        ws.send(json.dumps({"id": seq, "method": method, "params": params or {}}))
                        while True:
                            msg = json.loads(ws.recv(timeout=10))
                            if msg.get("id") == seq:
                                if "error" in msg:
                                    raise RuntimeError(msg["error"])
                                return msg.get("result", {})
                    cdp("Page.enable")
                    cdp("Emulation.setDeviceMetricsOverride", {"width": 390, "height": 844,
                        "deviceScaleFactor": 1, "mobile": True})
                    cdp("Page.navigate", {"url": test_page.as_uri()})
                    result = None
                    for _ in range(100):
                        response = cdp("Runtime.evaluate", {"expression":
                            "document.querySelector('#browser-check')?.textContent || null", "returnByValue": True})
                        value = response.get("result", {}).get("value")
                        if value:
                            result = json.loads(value)
                            break
                        time.sleep(.1)
                    assert result, "Quiz did not complete in Chrome"
                    assert result["ok"], result
                    assert result["mobileWidth"] == 390, result
                    assert result["docWidth"] <= 390, result
                    cdp("Page.navigate", {"url": PAGE.as_uri()})
                    for _ in range(50):
                        ready = cdp("Runtime.evaluate", {"expression": "document.readyState", "returnByValue": True})
                        if ready.get("result", {}).get("value") == "complete":
                            break
                        time.sleep(.1)
                    if os.environ.get("PHQ15_SCREENSHOT"):
                        shot = cdp("Page.captureScreenshot", {"format": "png", "captureBeyondViewport": False})
                        Path(os.environ["PHQ15_SCREENSHOT"]).write_bytes(base64.b64decode(shot["data"]))
                    print(json.dumps(result, ensure_ascii=False))
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
    finally:
        test_page.unlink(missing_ok=True)

if __name__ == "__main__":
    main()

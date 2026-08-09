/* ============================================================
   Движок опросников для страниц /testy/.

   Один файл на все тесты — намеренно. В блоге мы уже наступили
   на грабли, когда одинаковый код лежал копиями в 18 файлах и
   успел разойтись; здесь логика живёт в одном месте, а страница
   отдаёт только свои данные.

   Страница должна содержать:
     <script type="application/json" id="quiz-data"> … </script>
     #quiz-form, #quiz-go, #quiz-count, #result,
     #res-score, #res-level, #res-text, #res-again, .res .scale

   Формат данных:
   {
     "goal":    "gad7_done",          // цель Яндекс.Метрики
     "max":     21,                   // максимум баллов (для подписи)
     "options": ["Ни разу", …],       // подписи вариантов, значение = индекс
     "questions": ["…", …],
     "reverse": [2, 5],               // индексы вопросов с обратным счётом
     "alert":   {"q": 8, "html": "…"},// если на этот вопрос ответ > 0 —
                                      // блок показывается поверх расшифровки
     "levels":  [{"max":4, "name":"…", "html":"…"}, …],
     "scale":   [{"flex":5, "color":"#C9D3C2"}, …]
   }

   Ответы никуда не отправляются: подсчёт целиком в браузере.
   ============================================================ */
(function () {
  var cfgEl = document.getElementById("quiz-data");
  var form  = document.getElementById("quiz-form");
  if (!cfgEl || !form) return;

  var cfg;
  try { cfg = JSON.parse(cfgEl.textContent); }
  catch (e) { console.error("[quiz] не разобрал quiz-data:", e); return; }

  var Q       = cfg.questions || [];
  var OPTS    = cfg.options || [];
  var LEVELS  = cfg.levels || [];
  var REVERSE = cfg.reverse || [];
  var TOP     = OPTS.length - 1;

  var go    = document.getElementById("quiz-go");
  var count = document.getElementById("quiz-count");
  var res   = document.getElementById("result");
  var scale = res ? res.querySelector(".scale") : null;

  /* --- шкала результата рисуется из данных, а не из разметки --- */
  if (scale && cfg.scale) {
    scale.innerHTML = cfg.scale.map(function (s) {
      return '<i style="flex:' + s.flex + '; background:' + s.color + '"></i>';
    }).join("");
  }

  /* --- вопросы --- */
  Q.forEach(function (q, i) {
    var fs = document.createElement("fieldset");
    fs.className = "q";
    var opts = OPTS.map(function (o, v) {
      return '<label><input type="radio" name="q' + i + '" value="' + v + '"><span>' + o + "</span></label>";
    }).join("");
    fs.innerHTML = "<legend><i>" + (i + 1) + ".</i>" + q + "</legend>" +
                   '<div class="opts">' + opts + "</div>";
    form.appendChild(fs);
  });

  function picked(i) {
    return form.querySelector('input[name="q' + i + '"]:checked');
  }
  function answered() {
    var n = 0;
    for (var i = 0; i < Q.length; i++) if (picked(i)) n++;
    return n;
  }
  function setCount(n) {
    count.textContent = "Отвечено: " + n + " из " + Q.length;
  }

  form.addEventListener("change", function () {
    var n = answered();
    setCount(n);
    go.disabled = n < Q.length;
  });

  go.addEventListener("click", function () {
    var score = 0, raw = [];
    for (var i = 0; i < Q.length; i++) {
      var el = picked(i);
      var v = el ? parseInt(el.value, 10) : 0;
      raw.push(v);
      score += (REVERSE.indexOf(i) > -1) ? (TOP - v) : v;
    }

    var lvl = LEVELS.filter(function (l) { return score <= l.max; })[0] || LEVELS[LEVELS.length - 1];

    document.getElementById("res-score").textContent = score;
    document.getElementById("res-level").textContent = lvl.name;

    /* Тревожный пункт (например, вопрос о самоповреждении в PHQ-9):
       если на него есть любой ненулевой ответ, предупреждение
       показывается независимо от суммы баллов — низкий общий балл
       не должен «замывать» такой ответ. */
    var html = lvl.html;
    if (cfg.alert && raw[cfg.alert.q] > 0) {
      html = '<div class="sos">' + cfg.alert.html + "</div>" + html;
    }
    document.getElementById("res-text").innerHTML = html;

    if (scale) {
      var bars = scale.querySelectorAll("i");
      var idx = LEVELS.indexOf(lvl);
      for (var j = 0; j < bars.length; j++) bars[j].className = (j === idx) ? "on" : "";
    }

    res.classList.add("on");
    res.scrollIntoView({ behavior: "smooth", block: "start" });
    res.focus({ preventScroll: true });

    if (window.ym && window.__metrikaId && cfg.goal) {
      try { ym(window.__metrikaId, "reachGoal", cfg.goal); } catch (e) {}
    }
  });

  document.getElementById("res-again").addEventListener("click", function () {
    form.reset();
    res.classList.remove("on");
    go.disabled = true;
    setCount(0);
    document.getElementById("quiz").scrollIntoView({ behavior: "smooth", block: "start" });
  });
})();

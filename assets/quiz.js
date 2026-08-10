/* ============================================================
   Движок опросников для страниц /testy/.

   Один файл на все тесты — намеренно. В блоге мы уже наступили
   на грабли, когда одинаковый код лежал копиями в 18 файлах и
   успел разойтись; здесь логика живёт в одном месте, а страница
   отдаёт только свои данные.

   Страница должна содержать:
     <script type="application/json" id="quiz-data"> … </script>
     #quiz-form, #quiz-go, #quiz-count, #result,
     #res-score, #res-level, #res-text, #res-multi, #res-again, .res .scale

   Формат данных:
   {
     "goal":    "gad7_done",          // цель Яндекс.Метрики
     "max":     21,                   // максимум баллов (для подписи)
     "offset":  16,                   // прибавляется к сумме — для шкал,
                                      //   где отсчёт начинается не с нуля (PSWQ: 16…80)
     "options": ["Ни разу", …],       // подписи вариантов, значение = индекс;
                                      //   можно {"t":"Никогда","v":0} — если баллы
                                      //   идут не подряд (AUDIT: 0/2/4)
     "questions": ["…", …],           // строка или {"q":"…","options":[…]} —
                                      //   свои варианты у отдельного вопроса (AUDIT)
     "reverse": [2, 5],               // индексы вопросов с обратным счётом
     "alert":   {"q": 8, "html": "…"},// если на этот вопрос ответ > 0 —
                                      //   блок показывается поверх расшифровки
     "levels":  [{"max":4, "name":"…", "html":"…"}, …],
     "scale":   [{"flex":5, "color":"#C9D3C2"}, …],

     "subscales": [                   // ⚠️ вместо levels/scale — если у теста
       {"name":"Депрессия",           //   несколько независимых шкал (DASS-21).
        "items":[2,4,9],              //   Общая сумма при этом не показывается:
        "mult":2,                     //   у таких опросников её не существует.
        "max":42,
        "ticks":"<span>0</span>…",
        "levels":[…], "scale":[…]}
     ]
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
  var LEVELS  = cfg.levels || [];
  var REVERSE = cfg.reverse || [];
  var OFFSET  = cfg.offset || 0;
  var SUBS    = cfg.subscales || null;

  var go    = document.getElementById("quiz-go");
  var count = document.getElementById("quiz-count");
  var res   = document.getElementById("result");
  var multi = document.getElementById("res-multi");
  var scale = res ? res.querySelector(".scale") : null;

  /* Варианты ответа: строка = значение по индексу, объект {t,v} = явный балл.
     Свои варианты у вопроса перекрывают общие (в AUDIT это два последних пункта). */
  function normOpts(list) {
    return (list || []).map(function (o, i) {
      return (typeof o === "string") ? { label: o, value: i }
                                     : { label: o.t, value: o.v };
    });
  }
  var DEFAULT_OPTS = normOpts(cfg.options);

  function optsFor(i) {
    var q = Q[i];
    return (q && typeof q === "object" && q.options) ? normOpts(q.options) : DEFAULT_OPTS;
  }
  function textOf(i) {
    var q = Q[i];
    return (typeof q === "string") ? q : q.q;
  }
  /* Верх шкалы вопроса — для обратного счёта: в PSWQ и PSS-10 «обратные»
     пункты считаются как (максимум − ответ). */
  function topOf(i) {
    return optsFor(i).reduce(function (m, o) { return Math.max(m, o.value); }, 0);
  }

  function levelFor(levels, score) {
    return levels.filter(function (l) { return score <= l.max; })[0] || levels[levels.length - 1];
  }
  function barsHtml(list) {
    return list.map(function (s) {
      return '<i style="flex:' + s.flex + '; background:' + s.color + '"></i>';
    }).join("");
  }
  function light(scaleEl, levels, lvl) {
    if (!scaleEl) return;
    var bars = scaleEl.querySelectorAll("i");
    var idx = levels.indexOf(lvl);
    for (var j = 0; j < bars.length; j++) bars[j].className = (j === idx) ? "on" : "";
  }

  /* --- шкала результата рисуется из данных, а не из разметки --- */
  if (scale && cfg.scale) scale.innerHTML = barsHtml(cfg.scale);
  if (SUBS) res.classList.add("multi");   /* CSS прячет единый балл: его нет */

  /* --- вопросы --- */
  Q.forEach(function (q, i) {
    var fs = document.createElement("fieldset");
    fs.className = "q";
    var opts = optsFor(i).map(function (o) {
      return '<label><input type="radio" name="q' + i + '" value="' + o.value +
             '"><span>' + o.label + "</span></label>";
    }).join("");
    fs.innerHTML = "<legend><i>" + (i + 1) + ".</i>" + textOf(i) + "</legend>" +
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
    var raw = [], pts = [];
    for (var i = 0; i < Q.length; i++) {
      var el = picked(i);
      var v = el ? parseInt(el.value, 10) : 0;
      raw.push(v);
      pts.push((REVERSE.indexOf(i) > -1) ? (topOf(i) - v) : v);
    }

    /* Тревожный пункт (например, вопрос о самоповреждении в PHQ-9):
       если на него есть любой ненулевой ответ, предупреждение
       показывается независимо от суммы баллов — низкий общий балл
       не должен «замывать» такой ответ. */
    var alertHtml = (cfg.alert && raw[cfg.alert.q] > 0)
      ? '<div class="sos">' + cfg.alert.html + "</div>" : "";

    if (SUBS) {
      /* Несколько независимых шкал: у каждой свой балл, своя полоса
         и своя расшифровка. Общей суммы у таких опросников нет. */
      multi.innerHTML = SUBS.map(function (s) {
        var sum = s.items.reduce(function (a, i) { return a + pts[i]; }, 0) * (s.mult || 1);
        var lvl = levelFor(s.levels, sum);
        return '<div class="sub">' +
                 '<div class="sub-h"><b>' + s.name + '</b>' +
                   '<span><em>' + sum + '</em> из ' + s.max + '</span></div>' +
                 '<div class="scale">' + barsHtml(s.scale) + '</div>' +
                 '<div class="ticks">' + (s.ticks || "") + '</div>' +
                 '<div class="lvl">' + lvl.name + '</div>' +
                 '<div class="sub-t">' + lvl.html + '</div>' +
               '</div>';
      }).join("");
      var mScales = multi.querySelectorAll(".scale");
      SUBS.forEach(function (s, k) {
        var sum = s.items.reduce(function (a, i) { return a + pts[i]; }, 0) * (s.mult || 1);
        light(mScales[k], s.levels, levelFor(s.levels, sum));
      });
      document.getElementById("res-text").innerHTML = alertHtml;
    } else {
      var score = pts.reduce(function (a, b) { return a + b; }, 0) + OFFSET;
      var lvl = levelFor(LEVELS, score);
      document.getElementById("res-score").textContent = score;
      document.getElementById("res-level").textContent = lvl.name;
      document.getElementById("res-text").innerHTML = alertHtml + lvl.html;
      light(scale, LEVELS, lvl);
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

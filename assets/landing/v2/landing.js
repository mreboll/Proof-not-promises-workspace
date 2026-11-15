// Proof, not promises: scroll landing. Without JS everything is visible and the posters stand in for the clips.
(function () {
  "use strict";
  var doc = document.documentElement;
  doc.classList.add("js");
  var REDUCED = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var SAVE_DATA = !!(navigator.connection && navigator.connection.saveData);
  var HAS_IO = "IntersectionObserver" in window;
  var $ = function (sel, root) { return (root || document).querySelector(sel); };
  var $$ = function (sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); };
  var clamp01 = function (v) { return v < 0 ? 0 : v > 1 ? 1 : v; };

  // ---------- Clips: load when near the viewport, play only while visible ----------
  function setupVideos() {
    var videos = $$("video[data-src]");
    if (REDUCED || SAVE_DATA || !HAS_IO) return; // posters only
    function load(v) { if (!v.getAttribute("src")) { v.src = v.dataset.src; v.load(); } }
    function play(v) {
      if (v.closest(".stack") && !v.classList.contains("on")) return;
      load(v);
      var p = v.play();
      if (p && p.catch) p.catch(function () { /* autoplay refused: the poster stays */ });
    }
    var near = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { load(e.target); near.unobserve(e.target); } });
    }, { rootMargin: "100% 0px" });
    var seen = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        e.target.dataset.visible = e.isIntersecting ? "1" : "";
        if (e.isIntersecting) play(e.target); else e.target.pause();
      });
    }, { threshold: 0.01 });
    videos.forEach(function (v) {
      if (!v.closest(".stack")) near.observe(v); // stage clips load one by one as they become active
      seen.observe(v);
    });
    window.landingPlay = play;
  }

  // ---------- Reveal on scroll ----------
  function setupReveal() {
    var items = $$(".reveal");
    if (!HAS_IO || REDUCED) { items.forEach(function (el) { el.classList.add("in"); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
    }, { rootMargin: "0px 0px -10% 0px", threshold: 0.08 });
    items.forEach(function (el) { io.observe(el); });
  }

  // ---------- Scene beats: text over a sticky clip ----------
  function setupBeats() {
    var beats = $$(".beat");
    if (!HAS_IO) { beats.forEach(function (b) { b.classList.add("on"); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { e.target.classList.toggle("on", e.isIntersecting); });
    }, { rootMargin: "-35% 0px -35% 0px" });
    beats.forEach(function (b) { io.observe(b); });
  }

  // ---------- How it works: active stage swaps the sticky clip ----------
  function setupStages() {
    var stages = $$(".stage"), clips = $$(".stack video"), marks = $$(".rail span");
    if (!stages.length) return;
    function activate(i) {
      stages.forEach(function (s, k) { s.classList.toggle("on", k === i); });
      marks.forEach(function (m, k) { m.classList.toggle("on", k === i); m.classList.toggle("done", k < i); });
      clips.forEach(function (v, k) {
        var on = k === i;
        v.classList.toggle("on", on);
        if (on && v.dataset.visible && window.landingPlay) window.landingPlay(v);
        else if (!on) v.pause();
      });
    }
    activate(0);
    if (!HAS_IO) { stages.forEach(function (s) { s.classList.add("on"); }); return; }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) { if (e.isIntersecting) activate(Number(e.target.dataset.stage)); });
    }, { rootMargin: "-45% 0px -45% 0px" });
    stages.forEach(function (s) { io.observe(s); });
  }

  // ---------- Concept quote: words light up as you read ----------
  function splitQuote() {
    var quote = $("#quote");
    if (!quote) return [];
    var words = [];
    Array.prototype.slice.call(quote.childNodes).forEach(function (node) {
      var isKey = node.nodeType === 1 && node.classList.contains("key");
      var text = node.textContent;
      var frag = document.createDocumentFragment();
      text.split(/(\s+)/).forEach(function (part) {
        if (!part) return;
        if (/^\s+$/.test(part)) { frag.appendChild(document.createTextNode(part)); return; }
        var span = document.createElement("span");
        span.className = "w" + (isKey ? " key" : "");
        span.textContent = part;
        frag.appendChild(span);
        words.push(span);
      });
      quote.replaceChild(frag, node);
    });
    return words;
  }

  // ---------- Scroll-driven effects (one rAF per frame) ----------
  function setupScroll() {
    var nav = $("nav.top"), hero = $(".hero"), sign = $("#sign"), counter = $("#counter");
    var hs = $(".hs"), track = $(".hs-track"), explore = $(".explore");
    var quote = $("#quote"), words = REDUCED ? [] : splitQuote();
    var links = $$('nav.top ul a[href^="#"]');
    var sections = links.map(function (a) { return document.getElementById(a.getAttribute("href").slice(1)); });
    var hsDistance = 0, hsActive = false;

    function sizeHorizontal() {
      if (!hs || !track) return;
      hsActive = !REDUCED && window.innerWidth > 900;
      hs.classList.toggle("static", !hsActive);
      if (!hsActive) { hs.style.height = ""; hs.style.removeProperty("--hs"); return; }
      hsDistance = Math.max(0, track.scrollWidth - window.innerWidth);
      hs.style.height = (window.innerHeight + hsDistance) + "px";
    }

    // Progress of an element through the viewport: 0 when its top reaches the top, 1 when its bottom reaches the bottom.
    function pinnedProgress(el) {
      var r = el.getBoundingClientRect(), span = r.height - window.innerHeight;
      return span > 0 ? clamp01(-r.top / span) : 0;
    }

    function update() {
      var vh = window.innerHeight, y = window.scrollY, max = doc.scrollHeight - vh;
      doc.style.setProperty("--scroll", max > 0 ? (y / max).toFixed(4) : 0);
      if (nav) nav.classList.toggle("solid", y > vh * 0.6);
      if (hero && !REDUCED) hero.style.setProperty("--hero", clamp01(y / vh).toFixed(3));

      if (sign && counter) {
        var p = clamp01(pinnedProgress(sign) / 0.55);
        var n = Math.round(237 - (237 - 12) * (1 - Math.pow(1 - p, 3)));
        if (REDUCED) n = 12;
        counter.textContent = n;
        counter.classList.toggle("done", n === 12);
      }
      if (hsActive) hs.style.setProperty("--hs", (pinnedProgress(hs) * hsDistance).toFixed(1));
      if (explore && !REDUCED) {
        var er = explore.getBoundingClientRect();
        explore.style.setProperty("--par", ((er.top + er.height / 2 - vh / 2) / vh).toFixed(3));
      }
      if (words.length && quote) {
        var qr = quote.getBoundingClientRect();
        var qp = clamp01((vh * 0.85 - qr.top) / (vh * 0.85 - vh * 0.3 + qr.height * 0.5));
        var lit = Math.round(qp * words.length);
        words.forEach(function (w, i) { w.classList.toggle("lit", i < lit); });
      }
      var line = vh * 0.35, current = -1;
      sections.forEach(function (s, i) { if (s && s.getBoundingClientRect().top <= line) current = i; });
      if (y >= max - 4) current = sections.length - 1;
      links.forEach(function (a, i) {
        a.classList.toggle("active", i === current);
        if (i === current) a.setAttribute("aria-current", "true"); else a.removeAttribute("aria-current");
      });
    }

    var ticking = false;
    function onScroll() { if (!ticking) { ticking = true; requestAnimationFrame(function () { ticking = false; update(); }); } }
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", function () { sizeHorizontal(); onScroll(); });
    window.addEventListener("load", function () { sizeHorizontal(); update(); });
    sizeHorizontal();
    update();
  }

  // ---------- Modal: 60 sandboxes start at once and finish green (real sweep: 60 at once, 27.4 s, 0 failures) ----------
  function setupSandboxes() {
    var grid = $("#sbx-grid"), viz = $("#sbx-viz");
    if (!grid || !viz) return;
    var N = 60, WALL = 27.4, STAGGER_MS = 18, DUR_MS = 2600, cells = [];
    for (var i = 0; i < N; i++) { var c = document.createElement("div"); c.className = "sbx-cell"; grid.appendChild(c); cells.push(c); }
    var nEl = $("#sbx-n"), tEl = $("#sbx-t");
    function finalState() { cells.forEach(function (c) { c.className = "sbx-cell ok"; }); nEl.textContent = N; tEl.textContent = WALL + " s"; }
    if (REDUCED || !HAS_IO) { finalState(); return; }
    function play() {
      cells.forEach(function (c, i) { setTimeout(function () { c.className = "sbx-cell run"; nEl.textContent = i + 1; }, i * STAGGER_MS); });
      var start = performance.now();
      (function tick() {
        var p = Math.min(1, (performance.now() - start) / DUR_MS);
        tEl.textContent = (p * WALL).toFixed(1) + " s";
        if (p < 1) requestAnimationFrame(tick);
      })();
      // Finish in a spread-out order, like real runs that end at slightly different times (17-27 s).
      cells.forEach(function (c, i) { setTimeout(function () { c.className = "sbx-cell ok"; }, 1500 + ((i * 37) % N) * STAGGER_MS); });
    }
    var io = new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) { io.disconnect(); play(); }
    }, { threshold: 0.4 });
    io.observe(viz);
  }

  // ---------- Try it: replay of the recorded run of issue #2283 (fixtures/report_2283_dotnet.json), ~60x faster ----------
  var TRY_SCRIPT = [ // [ms, step, class, text]; text is plain (set with textContent)
    [300, "t1", "phase", "▶ T1 · Triage  — 4 files in the diff, risk by static rules, scope by Gemini flash"],
    [1000, null, "", "  README.md                                   OUT · LOW   R-LOW-02 markdown"],
    [1600, null, "", "  doc/analyzers/MsgPack004.md                 OUT · LOW   R-LOW-02 markdown"],
    [2300, null, "warn", "  …/CodeAnalysis/TypeCollector.cs             IN  · HIGH  R-HIGH-03 core generator namespace"],
    [2900, null, "", "  tests/…/GenericsFormatterTests.cs           IN  · LOW   R-LOW-01 tests/"],
    [3400, "done-t1", "dim", "  1 high-risk file goes to cross-examination; 2 out of scope go to a human"],
    [3900, "t2", "phase", "▶ T2 · Evidence — Gemini writes LedgerIssue2283 from the issue text only (never the diff)"],
    [4900, null, "", "  base (before the fix)   2 failed   → red: the test reproduces the bug"],
    [5900, null, "ok", "  PR   (after the fix)    2 passed   → green"],
    [6900, null, "", "  invariance  29 cases through the source generator, base run twice"],
    [7700, null, "ok", "  21/21 general cases identical · base deterministic"],
    [8100, "done-t2", "dim", "  evidence passed. A reviewer reading only this would approve."],
    [8700, "t3", "phase", "▶ T3 · Cross-examination — Nemotron (Prosecutor) vs Gemini (Defender) on TypeCollector.cs"],
    [9500, null, "", "  Q1  Does GetObjectInfo still throw IndexOutOfRange on the other diagnostic branches?"],
    [10400, null, "ok", "      Defender test: green on PR · red on mutant → objection closed"],
    [11000, null, "", "  Q2  Does Diagnostic.Create throw when the property location comes from metadata?"],
    [11900, null, "bad", "      Defender test FAILS on the PR (2 failed) → possible defect"],
    [12500, null, "", "  Q3  Does it still crash with a closed generic reference type from another assembly?"],
    [13400, null, "bad", "      Defender test FAILS on the PR (2 failed) → possible defect"],
    [13900, "done-t3-bad", "dim", "  1 of 3 objections closed. The fix moved the crash: InvalidOperation at line 1013."],
    [14500, "v", "phase", "▶ Verdicts"],
    [15000, "tally", "bad", "  TypeCollector.cs              RED     M7 · refuses to decide: 2 open objections"],
    [15500, null, "warn", "  README.md · MsgPack004.md      YELLOW  M2 · out of scope: read the justification"],
    [15900, null, "ok", "  GenericsFormatterTests.cs     GREEN   M4 · approved on evidence, unread"],
    [16500, "done-v", "final", "Decision: MANUAL AUDIT REQUIRED  ·  report → out/report-2283.html  ·  signed by: ______"]
  ];

  function setupTry() {
    var term = $("#term"), body = $("#term-body"), btn = $("#run-btn"), again = $("#again");
    if (!term || !body || !btn) return;
    var TOTAL_MS = 17000, REAL_S = 1140; // ~19 min of real pipeline time
    var bar = $("#bar"), clock = $("#clock"), tally = $("#tally"), result = $("#result"), frame = $("#report-frame");
    var running = false, timers = [], rafId = 0, start = 0;

    function step(name, state) {
      var li = $('.steps li[data-step="' + name + '"]');
      if (!li) return;
      if (state === "active") { li.classList.add("active"); return; }
      li.classList.remove("active"); li.classList.add("done");
      if (state === "bad") li.classList.add("bad");
    }
    function line(cls, text) {
      var d = document.createElement("div");
      d.className = "term-line" + (cls ? " " + cls : "");
      d.textContent = text;
      body.appendChild(d);
      body.scrollTop = body.scrollHeight;
    }
    function fmt(s) { var m = Math.floor(s / 60), r = Math.floor(s % 60); return (m < 10 ? "0" : "") + m + ":" + (r < 10 ? "0" : "") + r; }
    function tick() {
      var p = Math.min(1, (performance.now() - start) / TOTAL_MS);
      bar.style.transform = "scaleX(" + p.toFixed(4) + ")";
      clock.textContent = fmt(p * REAL_S);
      if (p < 1 && running) rafId = requestAnimationFrame(tick);
    }
    function reset() {
      timers.forEach(clearTimeout); timers = []; cancelAnimationFrame(rafId);
      $$(".term-line:not(.prompt)", body).forEach(function (n) { n.remove(); });
      $$(".steps li").forEach(function (li) { li.className = ""; });
      bar.style.transform = "scaleX(0)";
      clock.textContent = "00:00";
      tally.hidden = true;
      ["n-green", "n-yellow", "n-red"].forEach(function (id) { document.getElementById(id).textContent = "0"; });
      result.hidden = true;
      $("#caret").style.display = "";
    }
    function onStep(s) {
      if (s === "t1" || s === "t2" || s === "t3" || s === "v") step(s, "active");
      if (s === "done-t1") step("t1", "done");
      if (s === "done-t2") step("t2", "done");
      if (s === "done-t3-bad") step("t3", "bad");
      if (s === "done-v") step("v", "bad");
      if (s === "tally") {
        tally.hidden = false;
        document.getElementById("n-red").textContent = "1";
        timers.push(setTimeout(function () { document.getElementById("n-yellow").textContent = "2"; }, 500));
        timers.push(setTimeout(function () { document.getElementById("n-green").textContent = "1"; }, 900));
      }
    }
    function finish() {
      running = false;
      btn.disabled = false;
      $("#run-hint").textContent = "Done. Scroll down for the report, or run it again.";
      // Without "#must-read" in the src: an anchor inside the iframe would also scroll this page past the decision header.
      if (!frame.getAttribute("src")) {
        frame.addEventListener("load", function () {
          try {
            var target = frame.contentDocument.getElementById("must-read");
            if (target) frame.contentWindow.scrollTo(0, target.offsetTop - 12);
          } catch (e) { /* different origin (e.g. opened from disk): the report simply starts at the top */ }
        });
        frame.setAttribute("src", "demo/2283-dotnet.html");
      }
      result.hidden = false;
      result.scrollIntoView({ behavior: REDUCED ? "auto" : "smooth", block: "start" });
    }
    function run() {
      if (running) return;
      reset();
      running = true;
      btn.disabled = true;
      $("#caret").style.display = "none";
      $("#run-hint").textContent = "Running a replay of the recorded run…";
      start = performance.now();
      rafId = requestAnimationFrame(tick);
      TRY_SCRIPT.forEach(function (row) {
        timers.push(setTimeout(function () { onStep(row[1]); line(row[2], row[3]); }, row[0]));
      });
      timers.push(setTimeout(finish, TOTAL_MS + 400));
    }
    btn.addEventListener("click", run);
    if (again) again.addEventListener("click", function () { term.scrollIntoView({ block: "center" }); run(); });
    term.addEventListener("click", function () { term.focus(); });
    term.addEventListener("focus", function () { term.classList.add("focused"); });
    term.addEventListener("blur", function () { term.classList.remove("focused"); });
    term.addEventListener("keydown", function (e) { if (e.key === "Enter") { e.preventDefault(); run(); } });
  }

  setupVideos();
  setupReveal();
  setupBeats();
  setupStages();
  setupScroll();
  setupSandboxes();
  setupTry();
})();

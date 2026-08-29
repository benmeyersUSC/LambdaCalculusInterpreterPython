/* Terminal UI. All interpretation happens in web/worker.js; this file only
 * renders and routes. */

const $ = (id) => document.getElementById(id);
const el = { boot:$("boot"), stage:$("bootstage"), panes:$("panes"), src:$("src"),
  gutter:$("gutter"), run:$("run"), revert:$("revert"), stop:$("stop"),
  scroll:$("scroll"), line:$("line"), term:$("term"), envcount:$("envcount"),
  detail:$("detail"), ast:$("p-ast"), trace:$("p-trace"), source:$("p-source"),
  note:$("detailnote"), retry:$("retry") };

const URLS = {
  interpreter: new URL("./lambda_calculus_interpreter.py", location.href).href,
  bridge:      new URL("./web/bridge.py", location.href).href,
  program:     new URL("./code.lambda", location.href).href,
};

let worker = null, ready = false, seq = 0, pending = new Map();
let lastStage = "Starting…", watchdog = null;
let program = "";           // the last text handed to the interpreter as the environment
let history = [], hpos = 0, envNames = [];

/* ---------- worker plumbing ---------- */

/* A stalled request never rejects, so nothing downstream can notice it. This
 * bounds the whole boot instead: any 45s with no progress at all is reported
 * as stuck, naming the step it stopped on, with a way to start over. */
function armWatchdog() {
  clearTimeout(watchdog);
  watchdog = setTimeout(() => {
    if (ready) return;
    el.boot.classList.add("err");
    el.stage.textContent = `Stuck on “${lastStage}”. The network stalled rather than failed.`;
    el.retry.hidden = false;
  }, 45000);
}

function spawn() {
  ready = false;
  el.retry.hidden = true;
  el.boot.classList.remove("err");
  armWatchdog();
  worker = new Worker("web/worker.js");
  worker.onmessage = (e) => {
    const m = e.data;
    if (m.type === "boot")  { lastStage = m.stage; el.stage.textContent = m.stage; armWatchdog(); return; }
    if (m.type === "ready") { onReady(m); return; }
    if (m.type === "fatal") {
      m.payload = { ok: false, kind: "fatal", error: m.error };
      if (!ready) fail(m.error);
    }
    const r = pending.get(m.id);
    if (r) { pending.delete(m.id); r(m); }
    if (!pending.size) el.stop.hidden = true;
  };
  worker.onerror = (e) => fail(e.message || "worker failed to start");
  worker.postMessage({ type: "boot", ...URLS });
}

function ask(msg) {
  const id = ++seq;
  return new Promise((resolve) => {
    pending.set(id, resolve);
    // Only offer Stop once a call has actually been slow; well-behaved terms
    // return in milliseconds and a flickering button is worse than none.
    setTimeout(() => { if (pending.has(id)) el.stop.hidden = false; }, 400);
    worker.postMessage({ ...msg, id });
  });
}

function fail(message) {
  clearTimeout(watchdog);
  el.boot.hidden = false;
  el.boot.classList.add("err");
  el.stage.textContent = "Could not start: " + message;
  el.retry.hidden = false;
}

el.retry.addEventListener("click", () => {
  if (worker) worker.terminate();
  pending.clear();
  el.stage.textContent = "Starting…";
  spawn();
});

/* ---------- rendering ---------- */

function add(cls, html) {
  const d = document.createElement("div");
  d.className = "row " + cls;
  d.innerHTML = html;
  el.scroll.appendChild(d);
  el.scroll.scrollTop = el.scroll.scrollHeight;
  return d;
}
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&":"&amp;","<":"&lt;",">":"&gt;" }[c]));

const LONG = 110;
function termHtml(text) {
  if (text.length <= LONG) return `<span>${esc(text)}</span>`;
  const uid = "t" + (++seq);
  return `<span id="${uid}">${esc(text.slice(0, LONG))}…</span>` +
         `<button class="more" data-full="${esc(text)}" data-for="${uid}">show all</button>`;
}

el.scroll.addEventListener("click", (e) => {
  const b = e.target.closest(".more");
  if (!b) return;
  document.getElementById(b.dataset.for).textContent = b.dataset.full;
  b.remove();
});

function value(v) {
  const t = `<span class="t">${termHtml(v.term)}</span>`;
  if (v.kind === "number")
    return `<div class="val"><span class="eq">=</span><span class="n">${v.value}</span>${t}</div>`;
  if (v.kind === "boolean")
    return `<div class="val"><span class="eq">=</span><span class="b">true</span>${t}</div>`;
  if (v.kind === "ambiguous")
    return `<div class="val"><span class="eq">=</span><span class="amb">0 <small>or</small> false</span>${t}</div>`;
  return `<div class="val"><span class="eq">=</span>${t}</div>`;
}

function showResults(res, opts = {}) {
  if (!res.ok) {
    add("err", (res.kind === "diverged" ? "⟲ " : "✕ ") + esc(res.error));
  } else {
    for (const r of res.results) {
      if (opts.echoSource) add("term-out", esc(r.src));
      el.scroll.insertAdjacentHTML("beforeend", value(r));
    }
    const defs = res.defined || [];
    if (opts.summarizeDefs) {
      if (defs.length) add("note", `${defs.length} definitions in scope`);
    } else {
      for (const d of defs) add("note", `${d.how} <b>${esc(d.name)}</b>`);
    }
    if (res.ok && !res.results.length && !(res.defined || []).length)
      add("note", "no expressions to evaluate");
  }
  el.scroll.scrollTop = el.scroll.scrollHeight;
}

function setDetail(res, note) {
  el.detail.hidden = false;
  if (res.ast !== undefined) el.ast.textContent = res.ast || "(not requested)";
  if (res.trace !== undefined) el.trace.textContent = res.trace || "(empty)";
  el.note.textContent = note || "";
}

/* ---------- editor gutter ---------- */

function gutter() {
  const n = el.src.value.split("\n").length;
  el.gutter.textContent = Array.from({ length: n }, (_, i) => i + 1).join("\n");
  el.gutter.scrollTop = el.src.scrollTop;
}
el.src.addEventListener("input", gutter);
el.src.addEventListener("scroll", () => { el.gutter.scrollTop = el.src.scrollTop; });
el.src.addEventListener("keydown", (e) => {
  if (e.key === "Tab") {
    e.preventDefault();
    const s = el.src.selectionStart, t = el.src.selectionEnd;
    el.src.setRangeText("  ", s, t, "end");
    gutter();
  }
  if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); runProgram(); }
});

/* ---------- actions ---------- */

async function runProgram() {
  if (!ready) return;
  const source = el.src.value;
  add("spacer", "");
  add("echo", `<span class="ps">$</span> run program`);
  const names = await ask({ type: "setProgram", source });
  envNames = names.names || [];
  const res = (await ask({ type: "run", source, wantAst: true })).payload;
  program = source;
  showResults(res, { echoSource: true, summarizeDefs: true });
  setDetail(res, `${envNames.length} definitions · ${res.ok ? res.results.length : 0} expressions`);
  el.envcount.textContent = `${envNames.length} defs`;
}

const HELP = [
  "<b>Commands</b>",
  "  :help            this text",
  "  :defs            definitions currently in scope",
  "  :ast &lt;expr&gt;      evaluate and show the syntax tree below",
  "  :church &lt;n&gt;      the Church numeral for n, as source",
  "  :run             run the program on the left",
  "  :reset           forget every definition",
  "  :clear           clear this scrollback",
  "  :diverge         why some terms never finish",
  "",
  "<b>Syntax</b>  <code>L</code> is the lambda. <code>Lx.x</code> is the identity;",
  "  <code>Lm.Ln.m scc n</code> is addition. Application is juxtaposition and",
  "  binds left to right, so <code>f g h</code> means <code>(f g) h</code>.",
  "  <code>name = expr</code> defines a name for the rest of the session.",
].join("\n");

const DIVERGE = [
  "This interpreter reduces a term until it stops changing, with no step budget",
  "and no laziness. Under that strategy a fixed-point combinator applied to a",
  "branch whose arms are both evaluated -- <code>factorial</code> here, built on",
  "<code>yComb</code> and a strict <code>if</code> -- unfolds forever, because the",
  "recursive arm is reduced whether or not the base case was taken.",
  "",
  "It is a property of the evaluation order, not a bug: the same term in a",
  "normal-order evaluator terminates. When it happens you get a recursion-limit",
  "message rather than a hung tab, and <kbd>Stop</kbd> abandons the attempt.",
].join("\n");

async function submit(raw) {
  const line = raw.trim();
  if (!line) return;
  history.push(line); hpos = history.length;
  add("echo", `<span class="ps">λ&gt;</span> ${esc(line)}`);

  if (line.startsWith(":")) {
    const [cmd, ...rest] = line.slice(1).split(/\s+/);
    const arg = rest.join(" ");
    if (cmd === "help")    return void add("banner", HELP);
    if (cmd === "diverge") return void add("banner", DIVERGE);
    if (cmd === "clear")   { el.scroll.innerHTML = ""; return; }
    if (cmd === "run")     return void runProgram();
    if (cmd === "defs") {
      const { env } = await ask({ type: "env" });
      if (!env.length) return void add("note", "nothing defined");
      return void add("note", env.map((d) => "  " + esc(d.text)).join("\n"));
    }
    if (cmd === "reset") {
      await ask({ type: "clearEnv" });
      envNames = []; el.envcount.textContent = "0 defs";
      return void add("note", "environment cleared");
    }
    if (cmd === "church") {
      const n = parseInt(arg, 10);
      if (!(n >= 0)) return void add("err", ":church needs a non-negative integer");
      const { text } = await ask({ type: "church", n });
      return void add("note", esc(text));
    }
    if (cmd === "ast") {
      if (!arg) return void add("err", ":ast needs an expression");
      const res = (await ask({ type: "repl", line: arg, wantAst: true })).payload;
      showResults(res);
      return void setDetail(res, `:ast ${arg}`);
    }
    return void add("err", `unknown command :${esc(cmd)} — try :help`);
  }

  const res = (await ask({ type: "repl", line })).payload;
  showResults(res);
  if (res.defined && res.defined.length) {
    envNames = (await ask({ type: "env" })).env.map((d) => d.name);
    el.envcount.textContent = `${envNames.length} defs`;
  }
  if (res.trace) { el.trace.textContent = res.trace; el.detail.hidden = false; }
}

el.line.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { const v = el.line.value; el.line.value = ""; submit(v); }
  else if (e.key === "ArrowUp")   { if (hpos > 0) { el.line.value = history[--hpos]; e.preventDefault(); } }
  else if (e.key === "ArrowDown") {
    if (hpos < history.length - 1) el.line.value = history[++hpos];
    else { hpos = history.length; el.line.value = ""; }
    e.preventDefault();
  }
});
el.term.addEventListener("mousedown", (e) => {
  if (!e.target.closest("button") && !window.getSelection().toString()) {
    setTimeout(() => el.line.focus(), 0);
  }
});

el.run.addEventListener("click", runProgram);
el.revert.addEventListener("click", async () => {
  el.src.value = await fetch(URLS.program, { cache: "no-cache" }).then((r) => r.text());
  gutter();
  add("note", "program restored from code.lambda");
});

el.stop.addEventListener("click", async () => {
  worker.terminate();
  for (const resolve of pending.values())
    resolve({ payload: { ok: false, kind: "stopped", error: "abandoned" } });
  pending.clear();
  el.stop.hidden = true;
  add("err", "stopped — restarting the interpreter");
  el.boot.hidden = false;
  spawn();
});

/* ---------- tabs ---------- */

document.querySelectorAll(".tab").forEach((t) => {
  t.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((x) => x.classList.toggle("is-on", x === t));
    for (const name of ["ast", "trace", "source"])
      $("p-" + name).hidden = name !== t.dataset.tab;
  });
});

/* ---------- start ---------- */

async function onReady(m) {
  ready = true;
  clearTimeout(watchdog);
  el.boot.hidden = true;
  el.panes.hidden = false;

  if (!program) {                                   // first boot
    const [prog, source] = await Promise.all(
      [URLS.program, URLS.interpreter].map((u) =>
        fetch(u, { cache: "no-cache" }).then((r) => (r.ok ? r.text() : ""))));
    el.src.value = prog;
    el.source.textContent = source;
    gutter();
    add("banner",
      `<b>Lambda calculus</b>, evaluated by <b>lambda_calculus_interpreter.py</b> ` +
      `(${m.lines} lines) on CPython ${m.python} compiled to WebAssembly.\n` +
      `Press <kbd>Run</kbd> to evaluate the program on the left, then type ` +
      `expressions here. <code>:help</code> for commands.`);
  } else {                                          // restarted after a Stop
    await ask({ type: "setProgram", source: program });
    add("note", "interpreter restarted; definitions restored");
  }
  el.line.focus();
}

spawn();

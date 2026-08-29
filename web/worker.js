/* Pyodide worker: runs the repo's own interpreter, unmodified, in CPython.
 *
 * This lives in a worker for one reason: lambda calculus lets you write terms
 * that never reduce, and this interpreter is a plain recursive evaluator with
 * no step budget. On the main thread a divergent term would freeze the tab
 * with no way back. Here the page can terminate() the worker and start a fresh
 * one, which is what the Stop button does.
 */

const PYODIDE = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
importScripts(PYODIDE + "pyodide.js");

let py = null;
let bridge = null;

const post = (msg) => self.postMessage(msg);

/* Every await in here can stall on a network that neither answers nor fails,
 * and a stalled fetch has no timeout of its own -- it simply never settles,
 * which reaches the page as a boot message that sits there forever. So each
 * step is bounded, retried, and reports which step it was on. */

async function fetchText(url, label, attempts = 3) {
  let why = "unknown";
  for (let i = 1; i <= attempts; i++) {
    post({ type: "boot", stage: i === 1 ? label : `${label} (retry ${i - 1})` });
    try {
      // First attempt revalidates so the page can never serve a stale
      // interpreter; a retry accepts whatever the cache has, because by then
      // an answer matters more than freshness.
      const r = await fetch(url, {
        cache: i === 1 ? "no-cache" : "default",
        signal: AbortSignal.timeout(12000),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return await r.text();
    } catch (err) {
      why = err.name === "TimeoutError" || /abort|signal/i.test(err.message || "")
        ? "no response after 12s" : String(err.message || err);
      post({ type: "boot", stage: `${label} — ${why}` });
    }
  }
  throw new Error(`${label.toLowerCase()} failed — ${why}. Requested ${url}`);
}

async function boot(urls) {
  post({ type: "boot", stage: "Downloading CPython (WebAssembly) — about 11 MB, once" });
  py = await loadPyodide({ indexURL: PYODIDE });

  // Fetched, not bundled: the page serves the same lambda_calculus_interpreter.py
  // that sits at the root of the repo, so the site can never drift from the source.
  const interp = await fetchText(urls.interpreter, "Loading interpreter");
  const glue = await fetchText(urls.bridge, "Loading adapter");

  post({ type: "boot", stage: "Starting Python…" });
  py.FS.writeFile("/home/pyodide/lambda_calculus_interpreter.py", interp);
  py.FS.writeFile("/home/pyodide/bridge.py", glue);

  // Deep reduction is normal here; the limit only has to sit far enough below
  // the WebAssembly stack that Python raises RecursionError (catchable) rather
  // than the runtime overflowing (fatal -- it would take the worker with it).
  py.runPython(`
import sys
sys.setrecursionlimit(${urls.recursionLimit || 2200})
sys.path.insert(0, "/home/pyodide")
import bridge
`);
  bridge = py.pyimport("bridge");
  post({ type: "ready", python: bridge.version(), lines: interp.split("\n").length });
}

function toJs(result) {
  return result.toJs ? result.toJs({ dict_converter: Object.fromEntries }) : result;
}

self.onmessage = async (e) => {
  const { type, id } = e.data;
  try {
    if (type === "boot") return await boot(e.data);
    if (type === "run") {
      const out = toJs(bridge.run(e.data.source, e.data.wantAst !== false));
      return post({ type: "result", id, payload: out });
    }
    if (type === "setProgram") {
      const names = toJs(bridge.set_program(e.data.source));
      return post({ type: "program", id, names });
    }
    if (type === "repl") {
      const out = toJs(bridge.repl(e.data.line, e.data.wantAst === true));
      return post({ type: "result", id, payload: out });
    }
    if (type === "env") return post({ type: "env", id, env: toJs(bridge.env()) });
    if (type === "clearEnv") { bridge.clear_env(); return post({ type: "env", id, env: [] }); }
    if (type === "church") return post({ type: "church", id, text: bridge.church(e.data.n) });
  } catch (err) {
    post({ type: "fatal", id, error: String((err && err.message) || err) });
  }
};

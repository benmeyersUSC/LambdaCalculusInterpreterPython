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

async function boot(urls) {
  post({ type: "boot", stage: "Downloading CPython (WebAssembly)…" });
  py = await loadPyodide({ indexURL: PYODIDE });

  post({ type: "boot", stage: "Loading interpreter…" });
  // Fetched, not bundled: the page serves the same lambda_calculus_interpreter.py
  // that sits at the root of the repo, so the site can never drift from the source.
  const [interp, glue] = await Promise.all(
    [urls.interpreter, urls.bridge].map((u) =>
      fetch(u, { cache: "no-cache" }).then((r) => {
        if (!r.ok) throw new Error(`${u} -> HTTP ${r.status}`);
        return r.text();
      })
    )
  );
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

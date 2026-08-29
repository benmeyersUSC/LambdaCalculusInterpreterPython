# Lambda Calculus Interpreter

An interpreter for the untyped lambda calculus, written from scratch in Python.

**[Try it in your browser →](https://benmeyersusc.github.io/LambdaCalculusInterpreterPython/)**

No install, no server: the page runs this repository's own
`lambda_calculus_interpreter.py` on CPython compiled to WebAssembly.

## The language

`L` is the lambda. Application is juxtaposition and associates to the left, so
`f g h` means `(f g) h`. A line of the form `name = expr` defines a name for the
rest of the program; a bare expression is evaluated and printed.

```
zero  = Ls.Lz.z
scc   = Ln.Ls.Lz.s (n s z)
add   = Lm.Ln.m scc n
mul   = Lm.Ln.m (add n) zero

two   = scc (scc zero)
three = scc two

mul two three          -- (Ls.Lz.s (s (s (s (s (s z)))))), which is 6
```

Everything else in [`code.lambda`](code.lambda) is built the same way — booleans
and conditionals as projections, pairs and lists as functions, subtraction via
the predecessor trick, the Y combinator, and a Turing machine tape as a pair of
lists with `moveLeft` / `moveRight` / `read` / `write`.

## Pipeline

| Stage | Function | What it produces |
| --- | --- | --- |
| Lex | `tokenize` | `Lambda`, `VarToken`, `LParen`, `Period`, `Equals`, … |
| Parse | `parse_statement`, `parse_expression` | a tree of `Abstraction` / `Application` / `Variable` under `AssignmentStmt` / `ExprStmt` / `BlockStmt` |
| Compile | `compile_tree` | the same tree with every defined name replaced by the term it names |
| Evaluate | `eval_expr` | a beta-reduced term, with `substitute_expr` alpha-renaming any variable that would otherwise be captured |

`visualize_tree_ascii` renders the parse tree, which is what the **Syntax tree**
tab on the live page shows.

## Running locally

```sh
python3 lambda_calculus_interpreter.py      # evaluates code.lambda
```

To serve the browser version (it needs a real origin for the worker, so opening
`index.html` from the filesystem will not work):

```sh
python3 -m http.server 8000
# then visit http://localhost:8000
```

## Layout

```
lambda_calculus_interpreter.py   the interpreter — the whole language, one file
code.lambda                      sample program: arithmetic, logic, lists, a tape
index.html                       the browser front end
web/bridge.py                    adapter: drives the interpreter, returns data not files
web/worker.js                    Pyodide host, off the main thread
web/app.js, web/app.css          editor and terminal
```

### A note on the browser build

`web/bridge.py` exists because the interpreter's own top-level entry point,
`lambda_interpret_file_viz`, reads its input from a path and writes the parse
tree back out to another one. The adapter calls the same
tokenize → parse → compile → evaluate sequence directly and returns the results
as values. It also clears the interpreter's two module globals between runs —
`EXPRS`, the list of top-level expressions, and `HIGHEST`, the alpha-renaming
counter — so that one evaluation cannot leak into the next.

The interpreter itself is not modified, and the page fetches it at load time
rather than bundling a copy, so the site cannot drift from the source.

### Non-termination

Reduction here is eager and has no step budget, so a fixed-point combinator
applied to a branch whose arms are both evaluated — `factorial`, built on
`yComb` and a strict `if` — unfolds forever. That is a property of the
evaluation order rather than a bug. In the browser the interpreter runs in a
worker, so a divergent term surfaces as a recursion-limit message and can be
abandoned with **Stop** instead of freezing the tab.

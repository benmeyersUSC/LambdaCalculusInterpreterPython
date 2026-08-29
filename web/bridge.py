"""
Browser adapter for lambda_calculus_interpreter.

The interpreter is unmodified and knows nothing about the web. Everything here
is glue. It drives the same tokenize -> parse -> compile -> eval pipeline that
lambda_interpret_file_viz() drives, with two differences:

  * No filesystem. The pipeline in the module writes the AST to disk with
    save_tree_visualization_ascii(); we call the pure visualize_tree_ascii()
    that sits underneath it and hand the string back instead.

  * A clean slate per run. The interpreter keeps two module globals -- EXPRS
    (the source text of each top-level expression) and HIGHEST (the counter
    that alpha-renames captured variables). Both survive across calls, so
    without a reset the second run in a session inherits the first run's
    expression list and starts renaming variables from wherever the previous
    run stopped.

Results are decoded structurally, off the AST objects, rather than by counting
characters in the printed term. After alpha-renaming a bound variable can be
named "0" or "4", which makes the textual approach in the module's own
format_church_numeral_output() unreliable; walking the tree is exact.
"""

import contextlib
import io
import sys

import lambda_calculus_interpreter as LI


def _reset():
    LI.EXPRS.clear()
    LI.HIGHEST = 0


def _decode(term):
    """Recognise the two encodings this interpreter's programs actually use.

    A Church numeral is Lf.Lx. f (f (... x)); the numeral is how many times f
    is applied. Booleans are the two projections Lx.Ly.x and Lx.Ly.y. Anything
    else is just a term, and is reported as one.
    """
    if not isinstance(term, LI.Abstraction):
        return None, None
    outer, inner = term.variable, term.expression
    if not isinstance(inner, LI.Abstraction):
        return None, None
    body = inner.expression

    if isinstance(body, LI.Variable):
        # Lx.Ly.x is true, Lx.Ly.y is false -- and Ls.Lz.z is also zero.
        if body.name == inner.variable:
            return "zero-or-false", 0
        if body.name == outer:
            return "boolean", True

    n, cur = 0, body
    while (isinstance(cur, LI.Application)
           and isinstance(cur.fn, LI.Variable)
           and cur.fn.name == outer):
        n += 1
        cur = cur.operand
    if n and isinstance(cur, LI.Variable) and cur.name == inner.variable:
        return "number", n
    return None, None


def _label(term):
    kind, value = _decode(term)
    if kind == "number":
        return "number", str(value)
    if kind == "boolean":
        return "boolean", "true"
    if kind == "zero-or-false":
        # Church zero and Church false are the same term. Which one it "is"
        # depends on what the program meant by it, which we cannot know.
        return "ambiguous", "0  /  false"
    return "term", None


def _assigned_names(stmt, out):
    if isinstance(stmt, LI.BlockStmt):
        _assigned_names(stmt.stmt, out)
        _assigned_names(stmt.rest, out)
    elif isinstance(stmt, LI.AssignmentStmt):
        out.append(stmt.name)
    return out


def run(source, want_ast=True):
    """Evaluate a whole program. Never raises; failures come back as data."""
    _reset()
    trace = io.StringIO()
    ast = ""
    try:
        with contextlib.redirect_stdout(trace):
            tokens = LI.tokenize(source)
            parsed = LI.parse_statement(tokens, depth=0)[0]
            names = _assigned_names(parsed, [])
            if want_ast:
                ast = LI.visualize_tree_ascii(parsed)
            compiled = LI.compile_tree(parsed)[0]
            evaluated = LI.eval_stmt(compiled)
    except RecursionError:
        return {"ok": False, "kind": "diverged", "error":
                "Reduction did not terminate (recursion limit reached). "
                "Unbounded recursion under this evaluation order will do this -- "
                "see :help diverge.", "ast": ast, "trace": trace.getvalue()}
    except IndexError:
        return {"ok": False, "kind": "syntax",
                "error": "Unexpected end of input -- unbalanced parentheses?",
                "ast": ast, "trace": trace.getvalue()}
    except Exception as exc:                        # the module raises bare Exception
        return {"ok": False, "kind": "syntax", "error": str(exc) or type(exc).__name__,
                "ast": ast, "trace": trace.getvalue()}

    results = []
    for src, term in zip(LI.EXPRS, evaluated):
        kind, value = _label(term)
        results.append({"src": src, "term": repr(term), "kind": kind, "value": value})
    return {"ok": True, "results": results, "defined": names,
            "ast": ast, "trace": trace.getvalue()}


def church(n):
    """Source text for the Church numeral n, for the :church command."""
    return LI.church_num_from_int(int(n))


def version():
    return "%d.%d.%d" % sys.version_info[:3]


# --- terminal session -------------------------------------------------------
#
# The interpreter has no notion of an environment that outlives a program: a
# definition exists only for the statements below it in the same source text.
# So the terminal keeps the definitions itself and replays them as a prelude in
# front of whatever the user just typed. That is cheap -- an assignment binds a
# name during compile_tree and evaluates nothing -- and it means the REPL and a
# plain file are running through exactly the same code path.

_prelude = []   # list of (name, source line), in definition order


def statements(source):
    """Classify each line by parsing it. The grammar is one statement per line.

    Used to tell an assignment (which joins the environment silently) from an
    expression (which produces output), without a second parser in JavaScript.
    """
    out = []
    for line in source.splitlines():
        if not line.strip():
            out.append({"text": line, "kind": "blank", "name": None})
            continue
        try:
            _reset()
            with contextlib.redirect_stdout(io.StringIO()):
                parsed = LI.parse_statement(LI.tokenize(line), depth=0)[0]
            names = _assigned_names(parsed, [])
        except Exception:
            out.append({"text": line, "kind": "error", "name": None})
            continue
        out.append({"text": line, "kind": "assign" if names else "expr",
                    "name": names[0] if names else None})
    return out


def _define(name, text):
    for i, (existing, _) in enumerate(_prelude):
        if existing == name:               # redefinition keeps its position
            _prelude[i] = (name, text)
            return "redefined"
    _prelude.append((name, text))
    return "defined"


def set_program(source):
    """Adopt a program's definitions as the terminal environment."""
    del _prelude[:]
    for s in statements(source):
        if s["kind"] == "assign":
            _define(s["name"], s["text"])
    return [name for name, _ in _prelude]


def env():
    return [{"name": n, "text": t} for n, t in _prelude]


def clear_env():
    del _prelude[:]


def repl(line, want_ast=False):
    """Evaluate one terminal line in front of the accumulated environment."""
    stmts = statements(line)
    result = run("\n".join([t for _, t in _prelude] + [line]), want_ast=want_ast)
    result["defined"] = []
    if result["ok"]:
        # The prelude is assignments only, so nothing in it can print; every
        # result belongs to the line just typed.
        for s in stmts:
            if s["kind"] == "assign":
                result["defined"].append({"name": s["name"],
                                          "how": _define(s["name"], s["text"])})
    return result

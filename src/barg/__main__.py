import os
import sys
import traceback
import argparse
import barg


def map_call_stack_to_local_selfs():
    """Captures the call stack and extracts self from all frames (locals) where it can"""
    _, _, exc_tb = sys.exc_info()
    mapped_objects = []

    # Traverse the traceback's frames
    for frame, lineno in traceback.walk_tb(exc_tb):
        code_obj = frame.f_code
        func_name = code_obj.co_name

        local_vars = frame.f_locals
        instance = None

        if "self" in local_vars:
            instance = local_vars["self"]

        if instance:
            mapped_objects.append((func_name, instance, lineno))
        else:
            mapped_objects.append((func_name, None, lineno))

    return mapped_objects


def mark_line_in_grammar(grammar: str, lineno: int) -> str:
    """a function that takes grammar[line-4:line+5], indents it all and puts an arrow before grammar[line]"""
    lineno -= 1  # lines start at 1, indices at 0
    max_lineno_len = max(map(lambda i: len(str(i)), range(lineno - 4, lineno + 5)))
    lines = grammar.splitlines()[max(0, lineno - 4) : lineno + 5]
    for i, line in enumerate(lines[: min(4, lineno)]):
        lines[i] = str(i - 4 + lineno).ljust(max_lineno_len) + "|" + " " * 4 + line
    for i, line in enumerate(lines[min(4, lineno) + 1 :]):
        lines[i + min(4, lineno) + 1] = (
            str(i + 1 + lineno).ljust(max_lineno_len) + "|" + " " * 4 + line
        )
    lines[min(4, lineno)] = "----> " + lines[min(4, lineno)]
    return "\n".join(lines)


def barg_test(args):
    print(
        "Please use `PYTHONPATH=src python -m unittest barg.tests` to run all unit-tests from the barg project root directory. To run them for the installed package, use `python -m unittest barg.tests`. To run only a subset of all tests, use `barg.tests.{Exec,CodeGen}` or `barg.tests.{Exec,CodeGen}.test123`. Example: `python -m unittest barg.tests.Exec.test1`."
    )


def barg_exec(args):
    if args.max_recursion_limit:
        sys.setrecursionlimit(args.max_recursion_limit)
    if not os.path.exists(args.text_file) or not os.path.isfile(args.text_file):
        print("Could not find file " + args.text_file)
        return
    if not os.path.exists(args.grammar) or not os.path.isfile(args.grammar):
        print("Could not find file " + args.text_file)
        return
    with open(args.text_file) as f:
        text = f.read()
    with open(args.grammar) as f:
        grammar = f.read()
    errs = []
    g = barg.parse((text,), grammar, errs, args.toplevel_name)[0]
    if isinstance(g, Exception):
        nl = "\n"
        print(f"FAILED! Error: {g};\nErrors: {nl.join(errs)}")
    else:
        try:
            m = next(g)[0]
            print(m)
        except RecursionError:
            err = "Python recursion limit exceeded. This may indicate a flawed grammar which contains infinite cycles. The Python call stack and associated barg patterns are listed below:\n"
            if args.backtrace_len_limit:
                err += f"[truncated because backtrace length limit set to {args.backtrace_len_limit}]\n[...........................]\n"
            funcs_and_selfs = map_call_stack_to_local_selfs()
            funcs_and_selfs = (
                funcs_and_selfs[-args.backtrace_len_limit :]
                if args.backtrace_len_limit
                else funcs_and_selfs
            )
            for func, s, lineno in funcs_and_selfs:
                if s is None or not hasattr(s, "line"):
                    err += f"Python function '{func}' on line {lineno} called - cannot be mapped to barg grammar...\n"
                else:
                    err += (
                        f"Python function '{func}' on line {lineno} called - belongs to barg grammar:\n"
                        + mark_line_in_grammar(grammar, s.line)
                        + "\n"
                    )
            raise RecursionError(err)
        except Exception as e:
            errs.append(
                f"On line {e.__barg_line if hasattr(e, '__barg_line') and e.__barg_line != -1 else '<unknown/eof>'}: {e}\nPython {traceback.format_exc()}"
            )


def barg_codegen(args):
    src_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
    if not os.path.exists(args.grammar) or not os.path.isfile(args.grammar):
        print("Could not find file " + args.text_file)
        return
    with open(args.grammar) as f:
        grammar = f.read()
    code = barg.generate_python_parser(src_path, grammar, args.toplevel_name)
    with open(args.outfile, "w") as f:
        f.write(code)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers()
    bex = sp.add_parser("exec")
    bcg = sp.add_parser("codegen")
    btest = sp.add_parser("test")

    bex.add_argument("text_file")
    bex.add_argument("--grammar", "-g", required=True)
    bex.add_argument("--toplevel-name", "-tn", default="Toplevel")
    bex.add_argument("--max-recursion-limit", "-rec", type=int, default=None)
    bex.add_argument("--backtrace-len-limit", "-btlen", type=int, default=None)

    bcg.add_argument("grammar")
    bcg.add_argument("--toplevel-name", "-tn", default="Toplevel")
    bcg.add_argument("--outfile", "-o", default="barg_generated_parser.py")

    bex.set_defaults(func=barg_exec)
    bcg.set_defaults(func=barg_codegen)
    btest.set_defaults(func=barg_test)
    args = ap.parse_args()
    if not hasattr(args, "func"):
        print("Invalid usage. Use the -h option for more information.")
    else:
        args.func(args)

import os
import argparse
import barg


def barg_test(args):
    print(
        "Please use `python -m unittest barg.tests` to run all unit-tests. To run only a subset of all tests, use `barg.tests.{Exec,CodeGen}` or `barg.tests.{Exec,CodeGen}.test123`. Example: `python -m unittest barg.tests.Exec.test1`."
    )


def barg_exec(args):
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
    m = next(barg.parse((text,), grammar, args.toplevel_name)[0])[0]
    print(m)


def barg_codegen(args):
    print("codegen not implemented")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers()
    bex = sp.add_parser("exec")
    bcg = sp.add_parser("codegen")
    btest = sp.add_parser("test")

    bex.add_argument("text_file")
    bex.add_argument("--grammar", "-g", required=True)
    bex.add_argument("--toplevel-name", "-tn", default="Toplevel")

    bcg.add_argument("grammar")
    bcg.add_argument("-o", default="barg_generated_parser.py")

    bex.set_defaults(func=barg_exec)
    bcg.set_defaults(func=barg_codegen)
    btest.set_defaults(func=barg_test)
    args = ap.parse_args()
    if not hasattr(args, 'func'):
        print("Invalid usage. Use the -h option for more information.")
    else:
        args.func(args)

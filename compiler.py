"""Entry point:  python3 compiler.py [--optimize] <source> <output.ll>
          or:  python3 compiler.py [--optimize] --ast <source>
          or:  python3 compiler.py [--optimize] --ast-checked <source>
          or:  python3 compiler.py --tokens <source>
The flags may stand anywhere on the command line.

source bytes --lexer--> tokens --parser--> AST --semantic pass--> checked AST
            [--optimize--> smaller checked AST] --walk (codegen)--> str(module) -> output.ll

Nothing is built until the semantic pass has approved the whole tree, and on any error
no output file is written. --ast prints the tree the parser built; --ast-checked runs
the semantic pass on it first and prints what the pass found: the type of every
expression, the value of a constant, and the declaration every name means. With
--optimize, the optimizer of src/optimizer.py runs on the checked tree before code
generation; together with --ast it prints the tree it left, in the --ast format, and
together with --ast-checked the same tree with what the semantic pass found.
"""

import sys

from src.errors import CompileError
from src.lexer import lex
from src.optimizer import optimize
from src.parser import parse
from src.semantic import check

USAGE = ("usage: python3 compiler.py [--optimize] <source> <output.ll>\n"
         "       python3 compiler.py [--optimize] --ast <source>\n"
         "       python3 compiler.py [--optimize] --ast-checked <source>\n"
         "       python3 compiler.py --tokens <source>")
MODES = ("--tokens", "--ast", "--ast-checked")


def report(e):
    print(f"compilation error: line {e.line}:{e.col}: {e.msg}", file=sys.stderr)
    sys.exit(1)


def usage():
    print(USAGE, file=sys.stderr)
    sys.exit(2)


def read_source(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as e:
        print(f"error: cannot read {path}: {e.strerror}", file=sys.stderr)
        sys.exit(2)


def main():
    # The flags may stand anywhere: first, last, or between the paths.
    flags = [arg for arg in sys.argv[1:] if arg.startswith("--")]
    paths = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    modes = [flag for flag in flags if flag in MODES]
    if any(flag not in (*MODES, "--optimize") for flag in flags) or len(modes) > 1:
        usage()
    mode = modes[0] if modes else None
    optimizing = "--optimize" in flags
    if len(paths) != (1 if mode else 2) or (optimizing and mode == "--tokens"):
        usage()

    def checked(data):
        # The optimizer runs only on a tree the semantic pass has accepted: it never sees
        # an invalid program.
        program = check(parse(lex(data)))
        return optimize(program) if optimizing else program

    if mode is not None:
        data = read_source(paths[0])
        try:
            if mode == "--tokens":           # debug: the token stream
                output = "\n".join(str(t) for t in lex(data)) + "\n"
            elif mode == "--ast" and not optimizing:   # the tree, indented by depth
                output = parse(lex(data)).dump()
            elif mode == "--ast":            # the tree the optimizer left, as --ast shows a tree
                output = checked(data).dump(notes=False)
            else:                            # the tree after the semantic pass (and the optimizer)
                output = checked(data).dump()
        except CompileError as e:
            report(e)
        print(output, end="")
        return

    # Imported only here: the front end, the semantic pass and the optimizer run without
    # llvmlite.
    from src.codegen import codegen

    src_path, out_path = paths
    data = read_source(src_path)
    try:
        # lex -> parse -> check (names, types) -> [optimize] -> emit: nothing is built
        # until the semantic pass has approved the whole tree.
        module = codegen(checked(data))
    except CompileError as e:
        report(e)                            # exits before any output file exists

    with open(out_path, "w") as f:
        f.write(str(module))


if __name__ == "__main__":
    main()

"""Entry point:  python3 compiler.py <source> <output.ll>
          or:  python3 compiler.py --ast <source>
          or:  python3 compiler.py --ast-checked <source>
          or:  python3 compiler.py --tokens <source>

source bytes --lexer--> tokens --parser--> AST --semantic pass--> checked AST
            --walk (codegen)--> str(module) -> output.ll

Nothing is built until the semantic pass has approved the whole tree, and on any error
no output file is written. --ast prints the tree the parser built; --ast-checked runs
the semantic pass on it first and prints what the pass found: the type of every
expression, the value of a constant, and the declaration every name means.
"""

import sys

from src.errors import CompileError
from src.lexer import lex
from src.parser import parse
from src.semantic import check


def report(e):
    print(f"compilation error: line {e.line}:{e.col}: {e.msg}", file=sys.stderr)
    sys.exit(1)


def read_source(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except OSError as e:
        print(f"error: cannot read {path}: {e.strerror}", file=sys.stderr)
        sys.exit(2)


def main():
    args = sys.argv[1:]
    if len(args) != 2:
        print("usage: python3 compiler.py <source> <output.ll>\n"
              "       python3 compiler.py --ast <source>\n"
              "       python3 compiler.py --ast-checked <source>\n"
              "       python3 compiler.py --tokens <source>", file=sys.stderr)
        sys.exit(2)

    if args[0] in ("--tokens", "--ast", "--ast-checked"):
        data = read_source(args[1])
        try:
            tokens = lex(data)
            if args[0] == "--tokens":        # debug: the token stream
                output = "\n".join(str(t) for t in tokens) + "\n"
            elif args[0] == "--ast":         # the tree, indented by depth
                output = parse(tokens).dump()
            else:                            # the tree after the semantic pass
                output = check(parse(tokens)).dump()
        except CompileError as e:
            report(e)
        print(output, end="")
        return

    # Imported only here: the front end and the semantic pass run without llvmlite.
    from src.codegen import codegen

    src_path, out_path = args
    data = read_source(src_path)
    try:
        # lex -> parse -> check (names, types) -> emit: nothing is built until the
        # semantic pass has approved the whole tree.
        module = codegen(check(parse(lex(data))))
    except CompileError as e:
        report(e)                            # exits before any output file exists

    with open(out_path, "w") as f:
        f.write(str(module))

if __name__ == "__main__":
    main()

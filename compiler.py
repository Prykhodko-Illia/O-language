"""Entry point:  python3 compiler.py --ast <source>
          or:  python3 compiler.py --ast-checked <source>
          or:  python3 compiler.py --tokens <source>

source bytes --lexer--> tokens --parser--> AST --semantic pass--> checked AST

--ast prints the tree the parser built; --ast-checked runs the semantic pass on it
first and prints what the pass found: the type of every expression, the value of a
constant, and the declaration every name means.
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
    if len(args) != 2 or args[0] not in ("--ast", "--ast-checked", "--tokens"):
        print("usage: python3 compiler.py --ast <source>\n"
              "       python3 compiler.py --ast-checked <source>\n"
              "       python3 compiler.py --tokens <source>", file=sys.stderr)
        sys.exit(2)

    data = read_source(args[1])
    try:
        tokens = lex(data)
        if args[0] == "--tokens":            # debug: the token stream
            output = "\n".join(str(t) for t in tokens) + "\n"
        elif args[0] == "--ast":             # the tree, indented by depth
            output = parse(tokens).dump()
        else:                                # the tree after the semantic pass
            output = check(parse(tokens)).dump()
    except CompileError as e:
        report(e)
    print(output, end="")


if __name__ == "__main__":
    main()

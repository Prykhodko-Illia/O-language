"""Entry point:  python3 compiler.py --ast <source>
          or:  python3 compiler.py --tokens <source>

source bytes --lexer--> tokens --parser--> AST

Stage 1 of the project: the front end only. Semantic checks and code generation
come in the next stages.
"""

import sys

from src.errors import CompileError
from src.lexer import lex
from src.parser import parse


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
    if len(args) != 2 or args[0] not in ("--ast", "--tokens"):
        print("usage: python3 compiler.py --ast <source>\n"
              "       python3 compiler.py --tokens <source>", file=sys.stderr)
        sys.exit(2)

    data = read_source(args[1])
    try:
        tokens = lex(data)
        if args[0] == "--tokens":            # debug: the token stream
            output = "\n".join(str(t) for t in tokens) + "\n"
        else:                                # the tree, indented by depth
            output = parse(tokens).dump()
    except CompileError as e:
        report(e)
    print(output, end="")


if __name__ == "__main__":
    main()

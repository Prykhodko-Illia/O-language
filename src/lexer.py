"""Phase 0: bytes -> tokens  (lexical errors only)

A hand-written state machine: one loop, one byte per step. The state says what we
are in the middle of (nothing, a word, a number, a string, a comment), the byte's
class says what happens next. A byte that ends a token is read again in START
(`continue` without advancing) -- the only byte ever re-examined.

Every keyword of the language is a word made of letters and '_', so a word is
checked against the keyword table only once it is complete: `tuck_in` is one word,
never `tuck` followed by `_in`. The word `lowkey` is not a token at all: it switches
the machine into COMMENT until the end of the line.

Newlines are plain whitespace: statements end with `no_bap`, not with the line.
"""

from dataclasses import dataclass

from .errors import CompileError

I64_MAX = 9223372036854775807


@dataclass
class Token:
    kind: str        # keyword | identifier | number | string | punct | eof
    text: str
    line: int
    col: int         # 1-based position of the token's first byte
    sub: str = ""    # for keywords: type | bool | operator | ...

    def __str__(self):
        fields = ", ".join(f for f in (self.text, self.kind, self.sub) if f)
        return f"({fields}) {self.line}:{self.col}"


KEYWORDS = {
    "doze": "type", "fawty": "type", "line": "type",
    "merch": "bool", "woof": "bool",
    "tuck": "decl", "sliding": "mutable", "post": "assign",
    "bump": "operator", "tuck_in": "operator", "double_back": "operator",
    "breakdown": "operator", "scraps": "operator",
    "in_tune": "compare", "fugazi": "compare",
    "spot": "if", "pivot": "else",
    "drill": "function", "cuh": "return", "scat": "exit",
    "on_the_guys": "assert", "air_out": "print",
    "no_bap": "end",
}

COMMENT_WORD = b"lowkey"

PUNCT = {ord(c): c for c in "{}():,"}

SPACE, TAB, NEWLINE, CR, QUOTE = 32, 9, 10, 13, ord('"')


def is_alpha(b):
    return 65 <= b <= 90 or 97 <= b <= 122 or b == 95      # A-Z a-z _


def is_digit(b):
    return 48 <= b <= 57                                   # 0-9


def show_byte(b):
    return repr(chr(b)) if 33 <= b <= 126 else f"0x{b:02x}"


def lex(data: bytes):
    """Return the list of tokens, ending with one eof token."""
    tokens = []
    state, start, start_line, start_col = "START", 0, 1, 1
    line, col = 1, 1
    i = 0
    while i <= len(data):                    # one extra step: the end of input
        b = data[i] if i < len(data) else None

        if state == "START":
            if b is None:
                break
            elif b in (SPACE, TAB, CR):
                pass
            elif b == NEWLINE:
                line, col = line + 1, 0      # col becomes 1 at the bottom of the loop
            elif is_alpha(b):
                state, start, start_col = "WORD", i, col
            elif is_digit(b):
                state, start, start_col = "NUMBER", i, col
            elif b == QUOTE:
                state, start, start_line, start_col = "STRING", i + 1, line, col
            elif b in PUNCT:
                tokens.append(Token("punct", PUNCT[b], line, col))
            else:
                raise CompileError(line, col, f"unexpected byte {show_byte(b)}")

        elif state == "WORD":
            if b is not None and (is_alpha(b) or is_digit(b)):
                pass
            else:                            # the word is complete: comment, keyword or name?
                word = data[start:i]
                if word == COMMENT_WORD:
                    state = "COMMENT"
                    continue
                text = word.decode()
                if text in KEYWORDS:
                    tokens.append(Token("keyword", text, line, start_col, KEYWORDS[text]))
                else:
                    tokens.append(Token("identifier", text, line, start_col))
                state = "START"
                continue                     # re-read this byte in START

        elif state == "NUMBER":
            if b is not None and is_digit(b):
                pass
            elif b is not None and is_alpha(b):
                raise CompileError(line, start_col,
                                   f"invalid number {data[start:i + 1].decode()!r}: a letter inside a number")
            else:
                text = data[start:i].decode()
                if int(text) > I64_MAX:       # the overflow check the lexer can make
                    raise CompileError(line, start_col,
                                       f"constant {text} does not fit even in fawty (max {I64_MAX})")
                tokens.append(Token("number", text, line, start_col))
                state = "START"
                continue                     # re-read this byte in START

        elif state == "STRING":
            if b is None or b == NEWLINE:
                raise CompileError(start_line, start_col, "string is not closed before the end of the line")
            elif b == QUOTE:
                text = data[start:i].decode("utf-8", errors="replace")
                tokens.append(Token("string", text, line, start_col))
                state = "START"
            elif b < 32 and b != TAB:
                raise CompileError(line, col, f"unexpected byte {show_byte(b)} inside a string")
            # anything else, emoji bytes included, is part of the string

        elif state == "COMMENT":
            if b is None or b == NEWLINE:
                state = "START"
                continue                     # the newline is handled by START
            # everything up to the end of the line is ignored

        i += 1
        col += 1

    # The end of the file sits right after the last token: when a statement is cut short,
    # that is the spot where something should have been typed.
    if tokens:
        last = tokens[-1]
        width = len(last.text.encode()) + (2 if last.kind == "string" else 0)
        line, col = last.line, last.col + width
    tokens.append(Token("eof", "", line, col))
    return tokens

# 🏀 O-language 🏙️

> *Same words from the block, a different kind of business.* 💯

🏀 🧢 👟 🏘️ 🎤 💸 🔥 🏆

**From the courts on 64th to a compiler of his own** — a language that talks like the block and parses like a pro. 🏀

## 🏘️ The lore

He grew up on O-Block, where every word had two meanings and the wrong one could cost you. One day he decided
the old life was over: no more running, no more ducking, just honest business done right. But he kept the words.
`sliding` stopped meaning pulling up on somebody and started meaning a value that is allowed to change. A `drill` stopped being
trouble and became a routine you call by name. `spot` is still about checking the situation before you move, and
`on_the_guys` is still a promise, except now the compiler holds you to it. So he wrote it all down as a language,
called it O-language, and made every program end its sentences properly: `no_bap`. 🧢

He still hoops at the court every evening 🏀, but now the playbook is a grammar, the crossover is an inverted line,
and the only thing he's shooting is clean code. Nothing but net. 🎯

### 🎤 The story, in bars

```
Verse 1
Back on the O, every corner had a ledger,
Wrong word, wrong time, and it's over forever.
Mama said "baby, you smarter than this,"
So I tucked all the pain and I sliding to fix.
Traded the block for a desk and a screen,
Keywords from the street, but the code's running clean.
Every line that I write got a no_bap at the end,
'Cause a sentence left open is a problem again.

Hook
I don't slide on nobody, I slide my values in,
I spot what's in_tune, pivot when it's fugazi then,
I drill a routine, cuh back what's merch,
On_the_guys every promise, put the word to work.

Verse 2
Lexer read byte by byte, like I'm counting my blessings,
No regex, no shortcuts, I'm learning my lessons.
Parser go deep, recursive descent,
Every node in the tree know exactly where it went.
Doze for the small things, fawty for the bread,
Line tell the truth, merch or woof, like I said.
Open the brace, do the work, close it when it's done,
Now the only thing I'm scatting is a program that run.

Outro
They said the O only knew how to take,
Now the O got a compiler, look what we make.
```

---

The course project for *Languages and Compilers Design*. **Stage 1** is the front end: a hand-written lexer
(a state machine over bytes, no regular expressions, no `split()`), a recursive-descent parser and an AST.
Semantic checks and code generation are stages 2 and 3.

```
source bytes ──lexer──► tokens ──parser──► AST ──dump──► --ast output
```

The complete grammar is in [`grammar.ebnf`](grammar.ebnf): everything the parser accepts is there, and nothing else.

---

## 🛠️ Build and run

Nothing to build: the compiler is plain Python 3 (3.8 or newer), with no packages to install.

```bash
python3 compiler.py --ast program.txt       # print the AST, indented by depth
python3 compiler.py --tokens program.txt    # print the token stream (debugging)
```

On success the tree goes to stdout, with exit code 0. On a lexical or syntax error you get one line on stderr,
exit code 1, and no output:

```
compilation error: line 2:1: expected 'no_bap' to end the declaration, found keyword 'doze'
```

`line:column` is the 1-based position of the first byte of the token that broke the rule. When the file ends too
early, it points right after the last token: the place where something should have been typed.

## 🧪 Run the tests

```bash
./run_tests.sh
```

- `tests/ok/NAME.txt` must parse, and its `--ast` dump must equal `tests/ok/NAME.expected`.
- `tests/err/NAME.txt` must fail with a non-zero exit code and no output, and its error line must equal
  `tests/err/NAME.expected`.

Each test prints `PASS` or `FAIL` (with the difference), then a summary; the script exits non-zero if any test
failed. Every test is named after what it covers: `if_else_nested.txt`, `unclosed_block.txt`.

---

## 📜 The language

### 🗣️ Words

| O-language | Means | O-language | Means |
|---|---|---|---|
| `doze` | i32 | `bump` | `+` |
| `fawty` | i64 | `tuck_in` | `-` |
| `line` | bool | `double_back` | `*` |
| `merch` / `woof` | true / false | `breakdown` | `/` |
| `type name post value` | declare (C++ style) | `scraps` | `%` |
| `sliding` | mutable | `in_tune` | `==` |
| `post` | assign / initialise | `fugazi` | `!=` |
| `spot` / `pivot` | if / else | `drill` | function |
| `{ … }` | a block | `cuh` | return |
| `no_bap` | end of a statement | `scat` | exit the program |
| `on_the_guys( … )` | assert | `air_out( … )` | print |
| `lowkey` | comment to the end of the line | `pab_on` | inverted line (see below) |

All the words are reserved: none of them can be a variable name. Names are ASCII letters, digits and `_`, and do not
start with a digit. Whitespace (spaces, tabs, newlines) is free: a statement ends with `no_bap`, not with the line.

### 💸 Types and constants

Three types: `doze` (32-bit integer), `fawty` (64-bit integer) and `line` (boolean, `merch` or `woof`).
A number is decimal digits with no sign; write `0 tuck_in 5` for -5.

```
doze small post 42 no_bap
fawty big post 9223372036854775807 no_bap
line ok post merch no_bap
```

**Overflow check:** a number above `9223372036854775807` (the fawty maximum) is rejected by the lexer:

```
fawty big post 9223372036854775808 no_bap
compilation error: line 1:16: constant 9223372036854775808 does not fit even in fawty (max 9223372036854775807)
```

When a variable is initialised with a **constant expression** (numbers and operators only), the parser works out its
value and checks it against the declared type: `doze` holds -2147483648 .. 2147483647, `fawty`
-9223372036854775808 .. 9223372036854775807. A constant division by zero is caught the same way.

```
doze x post 3000000000 no_bap
compilation error: line 1:13: doze overflow: the value 3000000000 does not fit in doze (-2147483648 .. 2147483647)

doze y post 2147483647 bump 1 no_bap
compilation error: line 1:24: doze overflow: the value 2147483648 does not fit in doze (-2147483648 .. 2147483647)
```

`doze min post 0 tuck_in 2147483648 no_bap` is fine: the value is -2147483648. A value that involves variables
(`doze y post x bump 1`) is only known once names have types, so that check comes with the semantic pass of stage 2.

### 🔒 Constant and mutable variables

C++ style: `type name post value no_bap` declares a variable. Without a marker it is **tucked** (immutable); with
`sliding` before the type it is mutable. The initial value is mandatory.

```
doze limit post 10 no_bap              lowkey tucked: never changes
sliding fawty counter post 0 no_bap    lowkey sliding: can be posted again
```

### 📮 Assignment

`name post expression no_bap`:

```
counter post counter bump 1 no_bap
```

### 🧮 Expressions

`double_back`, `breakdown` and `scraps` bind tighter than `bump` and `tuck_in`; operators of equal precedence group from
left to right; `( )` groups. A comparison (`in_tune`, `fugazi`) binds weakest and gives a `line`; only one per
expression, unless you group with `( )`.

```
doze a post 2 bump 3 double_back 4 no_bap          lowkey 2 + (3 * 4) = 14
doze b post 10 tuck_in 3 tuck_in 2 no_bap          lowkey (10 - 3) - 2 = 5
doze c post (2 bump 3) double_back 4 no_bap        lowkey 20
line d post a fugazi b no_bap                      lowkey a != b
line e post (a in_tune 14) in_tune merch no_bap
```

### 👀 if / else

`spot condition { statements }`, optionally followed by `pivot { statements }`.
Each block holds at least one statement. Blocks nest.

```
spot (counter fugazi 0) {
    counter post counter tuck_in 1 no_bap
} pivot {
    air_out("done") no_bap
}
```

### 🏀 Functions, return and calls

C++ style: `type drill name(type param, …) { … }`. The return type goes first and is optional; functions live only at the
top level. `cuh value no_bap` returns a value, `cuh no_bap` returns nothing. A call is `name(args)`, as a value or
as a statement of its own.

```
fawty drill add(doze a, fawty b) {
    cuh a bump b no_bap
}

fawty x post add(1, 2) double_back 3 no_bap
add(x, x) no_bap
```

### 🔄 Unique feature: inverted lines — `pab_on`

On the O you learn to read things backwards. Any declaration, assignment, `cuh` or `scat` can be written **back to
front**: the line opens with `pab_on` (`no_bap` reversed), the value comes first, and the statement ends where the
line ends — no `no_bap` needed, and nothing else may follow on that line.

```
pab_on 5 post counter doze sliding        lowkey = sliding doze counter post 5 no_bap
pab_on counter bump 1 post counter        lowkey = counter post counter bump 1 no_bap
pab_on 2 double_back 3 post big fawty     lowkey = fawty big post 2 double_back 3 no_bap
pab_on 0 scat                             lowkey = scat 0 no_bap
```

It is the one place where a newline means something: after a `pab_on`, the lexer emits an `eol` token at the end of
the line, and the parser requires it. An inverted line builds the same node as the straight one, and the dump marks
it: `Decl counter doze sliding (inverted)`.

```
pab_on 5 post x doze no_bap
compilation error: line 1:22: an inverted line ends with the line: unexpected keyword 'no_bap'
```

### 🤞 The invariant: `on_the_guys`

`on_the_guys(condition) no_bap` states a contract: if the condition is `woof`, the program panics on the spot.
(The check itself is generated in stage 3; stage 1 parses it into an `Assert` node.)

```
on_the_guys(target in_tune 40) no_bap
```

### 📢 Print, exit and comments

```
air_out("hello 🔥") no_bap      lowkey a string: any bytes on one line, emojis included
air_out(x bump 1) no_bap        lowkey or a value
scat 0 no_bap                   lowkey exit the program, with or without a value
lowkey everything after lowkey is ignored up to the end of the line
```

### 🏆 A whole program

```
line drill run_check(doze target) {
    sliding doze counter post target no_bap

    spot (counter fugazi 0) {
        counter post counter tuck_in 1 no_bap
        on_the_guys(counter in_tune 0) no_bap
        cuh merch no_bap
    } pivot {
        air_out("empty") no_bap
        cuh woof no_bap
    }
}
run_check(1) no_bap
```

`python3 compiler.py --ast` prints (start):

```
Program
  Function run_check returns line
    Param target doze
    Body
      Decl counter doze sliding
        Var target
      If with pivot
        Cond
          BinOp fugazi (!=)
            Var counter
            Int 0
        Then
          Assign counter
            BinOp tuck_in (-)
              Var counter
              Int 1
          ...
```

Every node shows its fields: the declared type and `sliding` / `tucked` for a declaration, the word and the symbol
of each operator, the return type of a function. `Cond`, `Then`, `Else` and `Body` are headings that group the
children of a node.

### 🚨 Errors the front end catches

| Caught by | What |
|---|---|
| lexer | an unknown byte (`+`, `=`, `/`, `:`, an emoji outside a string…); a letter inside a number (`10x`); a number above the fawty maximum; a string not closed on its line |
| parser | a missing `no_bap`, type, name, `post` initialiser, `{` or `}`; a function without `drill` (`doze f() { … }`); `sliding` after the type; an empty block; `pivot` without `spot`; two operators in a row or an operator with no right side; two comparisons without `( )`; an unclosed `(`; a keyword used as a name; a string outside `air_out`; a `drill` inside a block; a constant initialiser that overflows its type, or divides by zero; an inverted line that does not end with its line or does not end in `post name`, `cuh` or `scat` |

---

## 🗂️ What's in the repo

```
compiler.py       entry point: --ast, --tokens, error reporting
grammar.ebnf      the grammar in EBNF
src/lexer.py      Token and lex(): byte-by-byte state machine (START, WORD, NUMBER, STRING, COMMENT)
src/parser.py     Parser: recursive descent, peek()/eat(), one method per grammar rule
src/ast_nodes.py  ASTNode, ProgramNode, FunctionNode, StmtNode + statements, ExprNode + expressions, dump()
src/errors.py     CompileError with line and column
tests/ok/         valid programs and their expected AST dump
tests/err/        invalid programs and their expected error line
run_tests.sh      runs every test and reports PASS / FAIL
ai_usage.txt      how AI was used for this stage
```

---

> 🏀 *Run it back, cuh: write it clean, close your blocks, end every line with `no_bap`.* 👟💯

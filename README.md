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

The course project for *Languages and Compilers Design*. **Stage 1** was the front end: a hand-written lexer
(a state machine over bytes, no regular expressions, no `split()`), a recursive-descent parser and an AST.
**Stage 2** makes it run: a semantic pass over that tree resolves every name to its declaration and gives every
expression a type, and then a code generator walks the checked tree and builds LLVM IR through the `llvmlite`
builder. The only IR text the compiler writes is the module the builder printed. **Stage 3** gives the language
a feature of its own -- **loops**, `run_it_back` and `laps` -- an optimizer behind `--optimize` that makes the
checked tree smaller without changing what a program prints, and a real program, a free-throw session tracker,
compiled to a native binary.

```
source bytes ──lexer──► tokens ──parser──► AST ──semantic pass──► checked AST ──[--optimize]──► smaller checked AST
             ──codegen──► output.ll ──lli / llc + clang──► 🏀
```

The complete grammar is in [`grammar.ebnf`](grammar.ebnf): everything the parser accepts is there, and nothing else.

---

## 🛠️ Build and run

### 🕶️ Pull up with the right tools

Nothing to build: the compiler is plain Python 3. Code generation needs `llvmlite`, and running what it makes
needs LLVM (`lli`, or `llc` and `clang`). On Ubuntu 24.04, the setup the tests run on:

```bash
sudo apt update
sudo apt install -y llvm clang python3 python3-venv python3-pip

python3 -m venv ~/lcd
source ~/lcd/bin/activate
pip install 'llvmlite==0.49.*'
```

Every new shell starts without the venv: `source ~/lcd/bin/activate` before you touch the compiler or the tests.
(`--ast`, `--ast-checked` and `--tokens` run without llvmlite.)

### ⚙️ Run the compiler

```bash
python3 compiler.py program.txt output.ll       # compile: write the LLVM IR module
lli output.ll                                   # run it, no linker needed
```

Or go all the way to a native binary, by hand or with `full_compiler.sh`, which leaves `output.ll`, `output.o` and
`program` in the current directory:

```bash
llc -filetype=obj -relocation-model=pic output.ll -o output.o
clang -fPIE output.o -o program
./program

./full_compiler.sh tests/ok/spot_pivot_runs.txt     # zero / even / odd
```

The other modes print instead of compiling, and write no file:

```bash
python3 compiler.py --ast program.txt           # print the AST, indented by depth
python3 compiler.py --ast-checked program.txt   # run the semantic pass, then print the tree with what it found
python3 compiler.py --tokens program.txt        # print the token stream (debugging)
```

`--optimize`, anywhere on the command line, runs the optimizer (✂️ below) on the checked tree before code
generation; with `--ast` it prints the tree the optimizer left, in the `--ast` format, and with `--ast-checked`
the same tree with what the semantic pass found:

```bash
python3 compiler.py --optimize program.txt output.ll
python3 compiler.py program.txt output.ll --optimize      # the same
python3 compiler.py --optimize --ast program.txt          # the tree after the optimizer
```

`--ast-checked` adds to every expression its type, its value when it is a constant, and the declaration a name
means: `Var counter  : doze  (declared at 2:18)`.

On a lexical, syntax or semantic error you get one line on stderr, exit code 1, and no output file:

```
compilation error: line 2:1: expected 'no_bap' to end the declaration, found keyword 'doze'
```

`line:column` is the 1-based position of the first byte of the token that broke the rule. When the file ends too
early, it points right after the last token: the place where something should have been typed.

## 🧪 Run the tests

```bash
./run_tests.sh
```

(with the venv active, where `lli` is installed)

- `tests/ok/NAME.txt` must compile; the program runs under `lli`, and its whole output must equal
  `tests/ok/NAME.expected` -- the `air_out` lines, the `scat` line, a runtime error line. When `tests/ok/NAME.in`
  exists, it is the program's standard input.
- `tests/err/NAME.txt` must fail -- in the lexer, the parser or the semantic pass -- with a non-zero exit code
  and no output file, and its error line must equal `tests/err/NAME.expected`.
- When `NAME.ast` (or `NAME.ast-checked`) exists next to a program, the `--ast` (or `--ast-checked`) dump must
  equal it too: the Stage 1 tests keep their tree dumps there.
- Every program of `tests/ok` and `tests/err` is compiled a second time **with `--optimize`**, and must print the
  same output, or fail with the same error, as without it.
- `tests/opt/NAME.txt` are the tests of the optimizer: each runs with and without `--optimize`, both outputs must
  equal `NAME.expected`, and the tree after `--optimize --ast` must equal `NAME.ast`.
- `programs/NAME.txt` is a whole program with recorded sessions: `NAME.in`, `NAME.2.in`, … is what the user
  types, `NAME.expected`, `NAME.2.expected`, … the exact output, prompts included. The script builds it into a
  **native binary** with `llc` and `clang`, with and without `--optimize`, and runs every session on both (where
  `llc` or `clang` is missing it says so and uses `lli`).

Each test prints `PASS` or `FAIL` (with the difference), then a summary; the script exits non-zero if any test
failed. Every test is named after what it covers: `if_else_nested.txt`, `unclosed_block.txt`.

### 🚦 Before a push and on GitHub

GitHub Actions runs `./run_tests.sh` on every push and every pull request into `main`
([`.github/workflows/tests.yml`](.github/workflows/tests.yml)), on Ubuntu 24.04 with LLVM 18 and llvmlite 0.49, and
then builds `tests/ok/whole_program_demo` into a native binary with `full_compiler.sh` and checks what it prints.

Locally, a pre-push hook does the same before anything leaves your machine. Turn it on once per clone:

```bash
git config core.hooksPath githooks
```

Now every `git push` runs the tests first and stops if one fails, showing only the failures and the summary (the
full output stays in `.git/pre-push.log`). No `lli` or llvmlite on the machine, like on macOS? The hook runs the
tests in the Multipass VM `noble-compilers` instead, with the repository at `~/compilers-proj` and the venv at
`~/lcd`; set `COMPILERS_VM`, `O_LANGUAGE_VM_REPO` or `COMPILERS_VM_VENV` if yours differ. In a hurry?
`git push --no-verify` skips it.

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
| `squad Name { … }` | a structure: a type with fields | `a.b.c` | a field, through a chain |
| `obj.f( … )` | a member function call | `finna_hear()` | read one integer from the input |
| `run_it_back cond { … }` | while | `up_on` | `>` |
| `laps i from a thru b { … }` | for `i` from `a` to `b`, `b` included | `down_bad` | `<` |

All the words of Stages 1 and 2 are reserved: none of them can be a variable name. The Stage 3 words --
`run_it_back`, `laps` (with its `from` and `thru`), `up_on` and `down_bad` -- are **contextual**: the lexer
keeps them as names, and the parser reads one as a word only where nothing in Stage 2 could stand (`laps`
followed by a name, `run_it_back` not followed by `post`, `.` or a call's `( … ) no_bap`, `up_on` right after
an operand). So a Stage 2 program that has a variable called `from` or a drill called `laps` still compiles and
prints the same ([`tests/ok/loop_words_still_names.txt`](tests/ok/loop_words_still_names.txt)). Names are ASCII letters, digits and `_`, and do not
start with a digit. Whitespace (spaces, tabs, newlines) is free: a statement ends with `no_bap`, not with the line.

### 💸 Types and constants

Three built-in types: `doze` (32-bit integer), `fawty` (64-bit integer) and `line` (boolean, `merch` or `woof`)
-- and on top of them, your own squads (below). A number is decimal digits with no sign; write `0 tuck_in 5` for -5.

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

`doze min post 0 tuck_in 2147483648 no_bap` is fine: the value is -2147483648. A value that involves tucked
variables with constant values is checked by the semantic pass, the same way (see the constant rules below):

```
doze max post 2147483647 no_bap
doze from_names post max bump 1 no_bap
compilation error: line 2:26: doze overflow: the value 2147483648 does not fit in doze (-2147483648 .. 2147483647)
```

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
left to right; `( )` groups. A comparison (`in_tune`, `fugazi`, `up_on`, `down_bad`) binds weakest and gives a
`line`; only one per expression, unless you group with `( )`. `up_on` (`>`) and `down_bad` (`<`) compare two
integers of any widths -- *up on* the other one, or *down bad* against it; `in_tune` and `fugazi` also compare two
lines.

```
doze a post 2 bump 3 double_back 4 no_bap          lowkey 2 + (3 * 4) = 14
doze b post 10 tuck_in 3 tuck_in 2 no_bap          lowkey (10 - 3) - 2 = 5
doze c post (2 bump 3) double_back 4 no_bap        lowkey 20
line d post a fugazi b no_bap                      lowkey a != b
line e post (a in_tune 14) in_tune merch no_bap
line f post a up_on b double_back 2 no_bap         lowkey a > b * 2
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

### 👥 Squads: structures with fields

`squad Name { fields }` declares a type of your own, at the top level, above every use of its name. Each field is
`[sliding] type name no_bap`: tucked unless it says `sliding`, of a built-in type or a squad declared above (never
the squad itself). An object is made with a **literal** -- the squad's name and one value per field, in field
order -- and it is a value like any other: it initialises a variable, goes into a parameter, comes out of a drill.

```
squad Point {
    sliding doze x no_bap
    sliding doze y no_bap
}
squad Circle {
    sliding Point center no_bap
    fawty r no_bap
}

Point drill moved(Point p, doze dx) {
    cuh Point{p.x bump dx, p.y} no_bap
}

sliding Circle c post Circle{Point{1, 2}, 5} no_bap      lowkey a literal inside a literal
c.center.y post c.center.y bump 40 no_bap               lowkey a field, through a chain
Point q post moved(c.center, 3) no_bap                  lowkey a copy goes in, a copy comes out
air_out(q.x) no_bap                                     →  4
```

A field is read by name through a chain, `c.center.x`, as deep as the squads go. It is posted to only when the
whole chain is `sliding`: the variable and every field on the way. Above, `c.center.y post …` works because `c`,
`center` and `y` all are; with a tucked `Circle c`, or a tucked `center`, it is an error. A whole object is never
posted to again (`p post q` is an error: post its fields); `Point q post p` declares a copy, and changing `p`
afterwards leaves `q` as it was.

The name of a squad is a type, so `Point p post …` is a declaration and `Point{…}` a literal, while any other
name is a variable: in `spot flag { … }` the `{` still opens the block.

### 🧠 Member functions

A squad's member functions come after its fields, written like any drill. They are called on an object --
`p.d2()`, `c.center.lift(1)` -- or by name inside another member function of the same squad, on the same object.

```
squad Counter {
    sliding doze n no_bap
    doze step no_bap

    drill tick() {
        n post n bump step no_bap            lowkey writes a field: tick is mutating
    }
    drill twice() {
        tick() no_bap                        lowkey calls a mutating one on its object: mutating too
        tick() no_bap
    }
    doze drill now() {
        cuh n no_bap                         lowkey only reads: fine on any Counter
    }
}

sliding Counter c post Counter{0, 5} no_bap
c.twice() no_bap
air_out(c.now()) no_bap                      →  10

Counter fixed post Counter{1, 1} no_bap
air_out(fixed.now()) no_bap                  →  1
fixed.tick() no_bap                          →  compilation error: … cannot call 'tick' on 'fixed': it changes its object, and 'fixed' is not sliding
```

**How a name is found inside a member function.** First among its parameters and its own variables (the
innermost block wins), then among the fields of its squad, and nowhere else: a parameter or a variable with the
same name hides a field, and a top-level variable is never visible, as in any drill. A call `f(…)` inside it
looks among the member functions of its squad first, then among the drills.

**Which member functions change their object.** One that posts to a field of its object, or calls a mutating
member function on its object or on a field of it -- through any number of calls, cycles included. Such a member
function is called only on an object reached through `sliding` links: the variable and every field on the way.
The object is passed by address, so the change is seen by the caller.

### 🔄 Unique feature: inverted lines — `pab_on`

On the O you learn to read things backwards. Any declaration, assignment, `cuh` or `scat` can be written **back to
front**: the line opens with `pab_on` (`no_bap` reversed), the value comes first, and the statement ends where the
line ends — no `no_bap` needed, and nothing else may follow on that line.

```
pab_on 5 post counter doze sliding        lowkey = sliding doze counter post 5 no_bap
pab_on counter bump 1 post counter        lowkey = counter post counter bump 1 no_bap
pab_on 2 double_back 3 post big fawty     lowkey = fawty big post 2 double_back 3 no_bap
pab_on 0 scat                             lowkey = scat 0 no_bap
pab_on Point{3, 4} post p Point sliding   lowkey = sliding Point p post Point{3, 4} no_bap
pab_on p.x bump 10 post p.y               lowkey = p.y post p.x bump 10 no_bap
```

It is the one place where a newline means something: after a `pab_on`, the lexer emits an `eol` token at the end of
the line, and the parser requires it. An inverted line builds the same node as the straight one, and the dump marks
it: `Decl counter doze sliding (inverted)`.

```
pab_on 5 post x doze no_bap
compilation error: line 1:22: an inverted line ends with the line: unexpected keyword 'no_bap'
```

### 🔁 Stage 3 feature: loops — `run_it_back` and `laps`

On the court you **run it back** until you get it right, and you run **laps** from one line to the other. Before
Stage 3 the only way to repeat was a drill calling itself; now there are two loops.

`run_it_back condition { statements }` is a **while**: the condition, a `line`, is checked before every round,
and the body runs while it is `merch` -- maybe never. `laps i from a thru b { statements }` is a **for over an
integer range**: `a` and `b` are evaluated once, before the first round, `a` first; then the body runs with the
counter `i` at `a`, `a bump 1`, … up to `b`, **`b` included** -- no round at all when `a` is greater than `b`.

The rules (`src/semantic.py` checks them, `tests/ok/loop_*` and `tests/err/loop_*` test them):

- the condition of `run_it_back` is a `line`; `from` and `thru` take integers, and a constant bound must fit the
  counter's type;
- the counter has the wider type of the two bounds: `doze`, or `fawty` when one of them is a `fawty`. It is
  **tucked** -- the loop moves it, a post to it is an error -- and it lives only in the body: after the `}` it is
  gone, and the body cannot declare it again;
- a loop's body is a block: a name declared in it is fresh in every round and gone after the `}`; a body may
  shadow an outer name, and holds at least one statement;
- loops nest -- a `laps` in a `run_it_back` in a `laps` -- and stand anywhere a statement does: the top level, a
  `spot`, a drill, a member function;
- `cuh` inside a loop leaves the drill at once, `scat` ends the program. A loop never counts as *leaving* a drill
  with a result type, even with a `cuh` inside -- it may run no round -- so such a drill still ends with a `cuh`;
- there is no `break`: a loop ends when its condition is `woof` or its counter reaches `b` (or with a `cuh`).

`laps i from 9223372036854775805 thru 9223372036854775807` ends after three rounds: the counter is compared with `b`
before it is moved, so it never steps past the maximum (`tests/ok/loop_for_bounds`).

**Example 1** -- a countdown and a table, a loop inside a loop with a declaration in the body
([`tests/ok/loop_for_nested.txt`](tests/ok/loop_for_nested.txt) has more):

```
sliding doze shot_clock post 3 no_bap
run_it_back shot_clock fugazi 0 {
    air_out(shot_clock) no_bap                      lowkey 3, 2, 1
    shot_clock post shot_clock tuck_in 1 no_bap
}
laps row from 1 thru 4 {
    sliding doze sum post 0 no_bap                  lowkey a fresh sum every row
    laps col from 1 thru row {
        sum post sum bump row double_back col no_bap
    }
    air_out(sum) no_bap                             lowkey 1, 6, 18, 40
}
```

**Example 2** -- read until a 0, in a drill that leaves from inside a loop
([`tests/ok/loop_read_until_zero.txt`](tests/ok/loop_read_until_zero.txt),
[`tests/ok/loop_cuh_inside_drill.txt`](tests/ok/loop_cuh_inside_drill.txt)):

```
doze drill first_multiple(doze of, doze limit) {
    laps n from 1 thru limit {
        spot n scraps of in_tune 0 {
            cuh n no_bap                            lowkey leaves the drill at once
        }
    }
    cuh 0 tuck_in 1 no_bap                          lowkey none in range
}
sliding fawty sum post 0 no_bap
sliding doze next post finna_hear() no_bap
run_it_back next fugazi 0 {
    sum post sum bump next no_bap
    next post finna_hear() no_bap
}
air_out(sum) no_bap                                 lowkey input 5 -2 10 0  →  13
air_out(first_multiple(7, 100)) no_bap              lowkey 7
```

In the tree a loop is a `While run_it_back` with a `Cond` and a `Body`, or a `For laps i` with its `Counter`,
`From`, `Thru` and `Body`; `--ast-checked` gives the counter its type: `Counter i  : doze`.

**The IR.** `python3 compiler.py` on `laps i from 1 thru 3 { air_out(i) no_bap }` writes this `main`, twenty
lines of `output.ll` as they are:

```llvm
entry:
  %"i" = alloca i32
  store i32 1, i32* %"i"
  %"empty" = icmp sgt i32 1, 3
  br i1 %"empty", label %"laps.end", label %"laps.body"
laps.body:
  %"i.1" = load i32, i32* %"i"
  %".4" = bitcast [4 x i8]* @"str" to i8*
  %".5" = call i32 (i8*, ...) @"printf"(i8* %".4", i32 %"i.1")
  br label %"laps.next"
laps.next:
  %"i.2" = load i32, i32* %"i"
  %"last" = icmp eq i32 %"i.2", 3
  br i1 %"last", label %"laps.end", label %"laps.step"
laps.end:
  ret i32 0
laps.step:
  %"step" = add i32 %"i.2", 1
  store i32 %"step", i32* %"i"
  br label %"laps.body"
```

The `entry` block evaluates both bounds once, stores `from` into the counter's own `alloca`, and jumps straight to
`laps.end` when `from` is greater than `thru` (`icmp sgt`, here on two constants), so an empty range runs no round.
`laps.body` is the body itself, and `laps.next` compares the counter with `thru` *before* moving it, so the loop
leaves on the last value and the plain `add` of `laps.step` can never step past the maximum. The last line,
`br label %"laps.body"`, is the **back edge** -- the one branch to an earlier block, which makes this a loop -- and a
`run_it_back` has one too, from the end of `while.body` back to `while.cond`, where its condition is checked again.

### 🤞 The invariant: `on_the_guys`

`on_the_guys(condition) no_bap` states a contract: if the condition is `woof` when the line runs, the program
prints where the promise was broken and ends with exit code 1.

```
on_the_guys(target in_tune 40) no_bap
line 3:1: you said on_the_guys, but it was cap
```

### 📢 Print, exit and comments

```
air_out("hello 🔥") no_bap      lowkey a string: any bytes on one line, emojis included
air_out(x bump 1) no_bap        lowkey or a value
scat 0 no_bap                   lowkey exit the program, with or without a value
lowkey everything after lowkey is ignored up to the end of the line
```

`air_out` prints its one argument and **always ends with a newline**: a `doze` or a `fawty` as a number, a `line`
as `true` or `false`, a string as it is written (a `%` stays a `%`), and an object as its squad's name and its
fields in declaration order, each as `name: value`, a squad field the same way inside it:

```
air_out(c) no_bap         →  Circle{center: Point{x: 3, y: 5}, r: 5}
air_out(p.flipped()) no_bap   →  Point{x: 4, y: 3}       (a call result or a literal prints the same way)
```

`finna_hear()` reads one integer from the standard input -- spaces and newlines between numbers do not matter --
and is a `doze` wherever a value goes: in a literal, an argument, a condition. When the input has no number left,
the program says so and ends with exit code 1, like any runtime error:

```
Point p post Point{finna_hear(), finna_hear()} no_bap     (input: 3 4)
scat p.d2() no_bap                                         →  Program exit with result 25
```

`scat value` prints `Program exit with result value` and ends the program with exit code 0 -- wherever it
stands, inside a drill too. `scat` with no value ends it silently, and so does reaching the end of the file.
Lines after a `scat` or a `cuh` in the same block are allowed and never run.

```
sliding doze n post 3 no_bap
scat n in_tune 3 no_bap          →  Program exit with result true
```

### 💥 When it runs: runtime errors

The compiler cannot know a value that comes from a `sliding` variable, so every operation that can break is
checked when it runs. A broken one prints one line -- where, and what -- and ends the program with exit code 1:

| What | Example | Prints |
|---|---|---|
| `bump`, `tuck_in`, `double_back` out of the type's range | `x post x bump 1` with x = 2147483647 | `line 3:10: doze overflow in 'bump', the bag is too big for doze` |
| `breakdown` or `scraps` by 0 | `10 breakdown zero` | `line 2:12: 'breakdown' by 0, you can't split it with nobody` |
| the one quotient that does not fit | `low breakdown minus_one` with low = -2147483648 | `line 4:13: doze overflow in 'breakdown', the bag is too big for doze` |
| an `on_the_guys` that is `woof` | `on_the_guys(target in_tune 40)` | `line 3:1: you said on_the_guys, but it was cap` |
| `finna_hear()` with no number left on the input | `doze n post finna_hear()` | `line 2:13: finna_hear heard nothing, no number on the line` |

(`low scraps minus_one` is 0 and fine: the remainder always fits.)

### 🏆 A whole program

Squads, a member function that changes its object, a drill that makes one, input and output:

```
squad Point {
    doze x no_bap
    sliding doze y no_bap

    doze drill d2() {
        cuh x double_back x bump y double_back y no_bap
    }
    drill lift(doze dy) {                lowkey writes a field: mutating
        y post y bump dy no_bap
    }
}

squad Circle {
    sliding Point center no_bap
    fawty r no_bap
}

Point drill origin() {
    cuh Point{0, 0} no_bap
}

sliding Circle c post Circle{Point{finna_hear(), finna_hear()}, 5} no_bap
c.center.lift(1) no_bap                  lowkey c and center are sliding: ok
Point o post origin() no_bap
air_out(c) no_bap
air_out(o.x in_tune 0) no_bap
scat c.center.d2() no_bap
```

With `3 4` on the input (it is `tests/ok/whole_program_demo`):

```
Circle{center: Point{x: 3, y: 5}, r: 5}
true
Program exit with result 34
```

### 🌳 The tree: `--ast`

The Stage 1 example, a drill with a `spot` and a `pivot`:

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

The squads and member functions of the Counter above print like this -- the mutability of every field, the
squad of every member function, the number of arguments of a call, and whether a chain ends in a member call:

```
Program
  Squad Counter
    Field n doze sliding
    Field step doze tucked
    Member tick of Counter returns nothing
      Body
        Assign n
          BinOp bump (+)
            Var n
            Var step
    Member twice of Counter returns nothing
      Body
        CallStmt
          Call tick (0 args)
        ...
  Decl c Counter sliding
    Literal Counter (2 values)
      Int 0
      Int 5
  CallStmt
    Chain c ends in member call twice (0 args)
      Var c
```

Every node shows its fields: the declared type and `sliding` / `tucked` for a declaration or a field, the word and
the symbol of each operator, the parameters and the result type of a drill (`returns nothing` when it has none).
`Cond`, `Then`, `Else` and `Body` are headings that group the children of a node. `--ast-checked` prints the same
tree after the semantic pass, with what it found: the type of every expression, the value of a constant, where each
name was declared (or that it is a field of the object), the field indices of a chain, and whether a member function
is mutating:

```
    Member tick of Counter returns nothing  (mutating: changes its object)
      Body
        Assign n  (a field of the object)  (field indices [0])
          BinOp bump (+)  : doze
            Var n  : doze  (a field of the object)  (field indices [0])
            Var step  : doze  (a field of the object)  (field indices [1])
```

### 🔧 How it becomes LLVM IR

The code generator builds everything through the `llvmlite.ir` builder; `str(module)` is the only IR text the
compiler writes. What each construct becomes:

| In O-language | In the IR |
|---|---|
| `doze`, `fawty`, `line` | `i32`, `i64`, `i1`; a `doze` going where a `fawty` is expected gets a `sext` |
| a variable, a parameter | an `alloca` in the entry block, `store` and `load` |
| a constant (as the semantic pass computed it) | one `ir.Constant` of the type it lands in |
| `bump`, `tuck_in`, `double_back` | `llvm.sadd/ssub/smul.with.overflow` and a branch to a block that reports and calls `exit(1)` |
| `spot` / `pivot` | basic blocks `then`, `else`, `merge` and a `cbranch` on the `i1` condition |
| `run_it_back` | blocks `while.cond`, `while.body`, `while.end`; the body ends with a `br` back to `while.cond` |
| `laps i from a thru b` | an `alloca` for `i`, `icmp sgt` to skip an empty range, blocks `laps.body`, `laps.next`, `laps.step`, `laps.end`; `laps.step` adds 1 and branches back to `laps.body` |
| `in_tune`, `fugazi`, `up_on`, `down_bad` | `icmp eq`, `ne`, `sgt`, `slt` on two operands of one width |
| a drill `f` | `@"drill.f"`: a name with a `.` cannot clash with `main` or `printf`. Every drill is declared before any body is built, so a call may go to a drill below |
| `squad Point` | an identified struct type `%"squad.Point" = type {i32, i32}`; an object is an `alloca` of it |
| `p.x`, `c.center.x` | one `gep` with indices `0`, then each field's index from the semantic pass's squad table |
| `Point{3, 4}` | `insertvalue` into an `undef` of the struct type, field by field |
| a member function `lift` of `Point` | `@"Point.lift"(%"squad.Point"* this, …)`; a call passes the object's address, or `this` on |
| `air_out` of an object | a walk over the squad's field table: one `gep`, `load` and `printf` per field |
| `finna_hear()` | `scanf("%d")` into a slot; `printf`, `scanf` and `exit` are declared in the module, and clang links them |
| `scat v` | `printf("Program exit with result …")`, then `exit(0)` |

### 📏 Rules the semantic pass enforces

Every rule below is a sentence `src/semantic.py` implements, and each one has a test that follows it
(`tests/ok/…`) and a test that breaks it (`tests/err/…`).

**Names**

| Rule | Follows | Breaks |
|---|---|---|
| A variable is declared before it is used. | `calls` | `undeclared_variable` |
| Every `{ }` block is a scope: its names are gone after its `}`, and it may declare a name of an outer scope again (shadowing). | `shadow_in_block` | `used_after_its_block` |
| A name is declared once per block; a drill's parameters and the lines of its body share one block. | `if_else_nested` | `redeclared_in_block`, `param_declared_again_in_body` |
| Only a `sliding` variable is posted to again; a parameter never is. | `assign_mutable` | `assign_tucked`, `assign_parameter` |
| A drill sees its parameters, its own variables and every drill -- not a variable of the top level. | `design_example` | `drill_sees_no_global` |
| A drill may call itself and any drill, declared above or below. A drill is declared once, with different parameter names. | `call_below_and_recursion` | `drill_declared_twice`, `param_declared_twice`, `call_undeclared_drill` |

**Types**

| Rule | Follows | Breaks |
|---|---|---|
| A number has the narrowest type it fits: `doze`, else `fawty`. | `overflow_limits` | `constant_overflows_fawty` |
| `bump`, `tuck_in`, `double_back`, `breakdown`, `scraps` take two integers and give the wider one; a `line` operand is an error. | `function_with_return` | `line_in_arithmetic` |
| `in_tune` and `fugazi` compare two integers (any widths) or two lines, and give a `line`. | `comparisons` | `compare_line_with_doze` |
| `up_on` and `down_bad` compare two integers (any widths), and give a `line`; one comparison per expression. | `compare_up_on_down_bad` | `compare_up_on_lines`, `compare_down_bad_twice` |
| A `doze` goes where a `fawty` is expected -- the only conversion there is: never `fawty` into `doze`, never across `line`. | `widen_doze_into_fawty` | `narrow_fawty_into_doze`, `arg_fawty_into_doze` |
| The condition of `spot` and of `on_the_guys` is a `line`. | `if_pivot` | `condition_not_line`, `assert_not_line` |
| `air_out` takes a string, an integer, a line or an object; `scat` an integer, a line or nothing. | `print_string_and_value` | `string_in_expression`, `scat_a_squad` |

**Drills and calls**

| Rule | Follows | Breaks |
|---|---|---|
| A call passes one argument per parameter, each of the parameter's type (a `doze` may go into a `fawty`). | `calls` | `args_too_many`, `args_too_few`, `arg_wrong_type` |
| A drill without a result type has no value: its call is only a statement of its own. | `function_no_return_type` | `void_call_as_value` |
| `cuh` is only inside a drill; it carries a value of the drill's result type, or nothing when the drill returns nothing. | `function_with_return` | `cuh_at_top_level`, `cuh_wrong_type`, `cuh_value_in_void_drill`, `cuh_without_value` |
| A drill with a result type leaves on every path: its body ends with `cuh` or `scat`, or with a `spot`/`pivot` whose two arms both leave. | `inverted_in_blocks` | `cuh_missing_on_a_path` |

**Loops**

| Rule | Follows | Breaks |
|---|---|---|
| The condition of `run_it_back` is a `line`, checked before every round. | `loop_while_countdown` | `loop_while_cond_not_line` |
| `laps i from a thru b`: `a` and `b` are integers, evaluated once, `a` first; the body runs for `a` … `b`, `b` included, none when `a > b`. | `loop_for_bounds` | `loop_bound_is_line`, `loop_missing_thru` |
| The counter is tucked and lives in the body only; the body cannot declare it again. | `loop_for_nested` | `loop_post_to_counter`, `loop_counter_outside_body`, `loop_counter_redeclared_in_body` |
| A loop's body is a block: a name in it is fresh each round and gone after it; it holds at least one statement. Loops nest. | `loop_body_declares`, `loop_for_nested`, `loop_in_member_function` | `loop_body_name_gone_after_round`, `loop_empty_body` |
| `cuh` and `scat` may stand in a loop; a loop never counts as leaving a drill. | `loop_cuh_inside_drill`, `loop_read_until_zero` | `loop_drill_ends_with_loop` |

**Squads**

| Rule | Follows | Breaks |
|---|---|---|
| A squad is declared once, at the top level, above every use of its name, with at least one field; its fields have different names. | `squad_fields_and_chains` | `squad_declared_twice`, `field_declared_twice`, `squad_used_before_declared`, `squad_inside_block`, `empty_squad` |
| A field's type is built in or a squad above -- never the squad itself. A field has no value of its own in the declaration. | `squad_literal_widens_and_nests` | `squad_contains_itself`, `field_with_a_value` |
| A literal gives one value per field, in order, each of the field's type (a `doze` may go into a `fawty` field). | `squad_literal_widens_and_nests` | `literal_too_few_values`, `literal_too_many_values`, `literal_wrong_field_type`, `literal_fawty_into_doze_field` |
| A chain names a field that exists at every link, and every link before the last is a squad. | `squad_fields_and_chains` | `unknown_field`, `field_of_a_doze` |
| Posting through a chain needs every link `sliding`: the variable and each field. A parameter is tucked. | `squad_fields_and_chains`, `squad_inverted_lines` | `assign_through_tucked_object`, `assign_through_tucked_field`, `assign_field_of_parameter` |
| A whole object is not posted to again; a declaration from one is a copy, and so is a squad going into a parameter or out of a drill. | `squad_copy_is_a_copy`, `squad_param_and_result`, `squad_in_a_loop_of_calls` | `assign_whole_object` |
| A squad's type is its name: a `Point` goes only where a `Point` is expected. Squads are not compared, not used in arithmetic, not a value of `scat`. | `squad_param_and_result` | `squad_param_wrong_squad`, `compare_squads`, `squad_in_arithmetic`, `scat_a_squad` |
| A squad's name is a type, never a drill or a variable: `Point` alone is not a value, and no drill is called `Point`. | `squad_name_and_spot_block` | `squad_name_without_literal`, `drill_named_like_squad` |

**Member functions**

| Rule | Follows | Breaks |
|---|---|---|
| Inside a member function a name is looked up among its parameters and variables, then the fields of its squad, then nowhere: a parameter or a variable hides a field, a top-level variable is never seen. | `member_name_lookup` | `member_unknown_name`, `member_sees_no_global` |
| A call `f(…)` inside a member function looks among the member functions of its squad first, then the drills. | `member_name_lookup`, `member_calls_in_a_cycle` | `call_undeclared_drill` |
| A member function is called on an object of a squad that declares it, with one argument per parameter of its type. | `member_d2_like_the_pdf`, `member_through_a_chain` | `member_unknown`, `member_on_a_doze`, `member_args_too_many`, `member_args_too_few`, `member_arg_wrong_type` |
| A member function leaves with a value of its result type, like any drill; it posts only to `sliding` fields. | `member_d2_like_the_pdf` | `member_cuh_wrong_type`, `member_assigns_tucked_field` |
| The fields come first; a field and a member function do not share a name, nor do two member functions; a member function is never `sliding`. | `member_changes_a_sliding_object` | `field_after_member`, `member_named_like_field`, `member_declared_twice`, `sliding_member` |
| A member function that posts to a field, or calls a mutating one on its object or a field of it, is mutating; it is called only through `sliding` links. A reading one is called on any object. | `member_changes_a_sliding_object`, `member_through_a_chain`, `member_reads_on_a_tucked_object` | `mutating_on_tucked_object`, `mutating_through_another_member`, `mutating_through_tucked_field`, `mutating_on_a_parameter`, `mutating_on_tucked_field_inside_member` |

**Input and output**

| Rule | Follows | Breaks |
|---|---|---|
| `finna_hear()` takes no arguments and is a `doze`. | `read_in_every_place` | `finna_hear_with_argument`, `finna_hear_into_line` |
| `air_out` takes a string, an integer, a line or an object -- never the call of a drill that returns nothing -- and puts a newline after it. | `print_every_kind` | `print_void_call` |
| An object prints as `Squad{field: value, …}`, fields in declaration order, a squad field the same way inside; a `line` field as `true` / `false`. | `print_objects`, `whole_program_demo` | -- |

**Constants** (the overflow check)

| Rule | Follows | Breaks |
|---|---|---|
| An expression of numbers, operators and tucked variables with constant values is computed exactly, with no limit on the steps in between, and must fit the type it lands in. | `constant_through_names` | `overflow_through_names` |
| A constant of numbers only may land in any integer it fits; one with a name keeps the type of its names, widened if its value needs it. | `overflow_limits` | `narrow_fawty_into_doze` |
| A constant division by zero is an error. | `left_associative` | `division_by_zero_through_names` |

**At run time** -- what the generated code checks, tested end to end

| Rule | Follows | Breaks |
|---|---|---|
| `bump`, `tuck_in`, `double_back` and `breakdown` give a value of their type, or end the program. | `arithmetic_at_run_time` | `runtime_doze_overflow`, `runtime_fawty_overflow`, `runtime_min_breakdown_minus_one` |
| `breakdown` and `scraps` never divide by 0; they round toward zero, as in C. | `arithmetic_at_run_time` | `runtime_division_by_zero`, `runtime_scraps_by_zero` |
| `on_the_guys` with a `woof` condition ends the program. | `assert_holds_at_run_time` | `runtime_assert_breaks` |
| `scat` ends the program wherever it stands; nothing after it runs. | `scat_inside_drill`, `code_after_scat` | -- |
| `finna_hear()` reads one integer, or ends the program when there is none. | `point_read`, `read_in_every_place` | `read_with_nothing_to_hear` |
| A drill's name never meets the runtime's: `drill main` and `drill printf` are ordinary drills. | `drill_named_main_and_printf` | -- |

### 🚨 Errors the compiler catches

| Caught by | What |
|---|---|
| lexer | an unknown byte (`+`, `=`, `/`, `:`, an emoji outside a string…); a letter inside a number (`10x`); a number above the fawty maximum; a string not closed on its line |
| parser | a missing `no_bap`, type, name, `post` initialiser, `{` or `}`; a function without `drill` (`doze f() { … }`); `sliding` after the type; an empty block; `pivot` without `spot`; two operators in a row or an operator with no right side; two comparisons without `( )`; an unclosed `(`; a keyword used as a name; a string outside `air_out`; a `drill` inside a block; a constant initialiser that overflows its type, or divides by zero; an inverted line that does not end with its line or does not end in `post name`, `cuh` or `scat`; a `laps` without its counter, `from` or `thru`; an empty loop body |
| parser (squads) | a squad inside a block or without fields; a field with a `post` value; a field after a member function; a `sliding` member function; a squad's name not followed by `{`; a type that is not a squad declared above; `finna_hear` with arguments |
| semantic pass | every rule of the tables above: a name not declared or declared twice, a post to a tucked variable or through a tucked chain, a type that does not fit, a wrong number or type of arguments, a misplaced or missing `cuh`, an unknown field or member function, a wrong literal, a squad that contains itself, a mutating member function called on a tucked object, a constant that overflows or divides by zero, a loop condition that is not a `line`, a bound that is not an integer, a post to a loop's counter |
| run time | see 💥 above: an overflow, a division by 0, a broken `on_the_guys`, no number for `finna_hear` -- one line, exit code 1 |

## ✂️ The optimizer: `--optimize`

`--optimize` runs [`src/optimizer.py`](src/optimizer.py) on the tree the semantic pass has accepted and
annotated, before the code generator -- so it never sees an invalid program, and the generator never knows it
ran. Every name in that tree already points at its declaration (`decl`) and every call at its function (`fn`), so
the optimizer counts, removes and renames **by node, never by spelling**: two `x` in two blocks are two
declarations, and that is how scopes and shadowing are respected without a symbol table. Three transformations
run in rounds -- unused functions, unused variables, one inlining -- until a round changes nothing, because each one
feeds the others.

**Unused variables.** A read is a name in a value, a condition, an argument, a print, the start of a field chain,
the object of a member call; a `post` to the variable is not a read. A declaration nobody reads is removed with
every post to it -- if nothing it takes away can be seen. A value is *quiet* when it can neither be observed nor
fail: a number, `merch` / `woof`, a variable or a field, a constant the semantic pass folded (`2 double_back 3` is
the number 6), a comparison or a literal of quiet values. Everything else stays: a call (it may print, read or
never return), `finna_hear()` (it eats a line of input), and arithmetic on values (`bump` may overflow,
`breakdown` may divide by zero, and either one prints an error and ends the program). Parameters, loop counters
and fields stay too. Removing `z` (which read `y`) leaves `y` unread, so the next round counts again: `x → y → z`
takes three rounds ([`tests/opt/var_chain_and_shadow.txt`](tests/opt/var_chain_and_shadow.txt),
[`tests/opt/var_in_loops_and_posts.txt`](tests/opt/var_in_loops_and_posts.txt)). A variable that only feeds
itself (`k post k bump 1`) survives: its own right side reads it.

**Unused functions.** Every call is counted wherever it stands -- the top level, a drill, a member function, a
loop -- except a call inside the function's own body, so a drill that only calls itself is unused too. A drill or a
member function with no call left is removed with its whole body, and the calls in that body go with it: `top`
was the only caller of `middle`, `middle` of `leaf`, so they go in rounds 1, 2 and 3. Two drills that only call
each other keep each other -- counting cannot see a cycle
([`tests/opt/fn_chain_removed.txt`](tests/opt/fn_chain_removed.txt),
[`tests/opt/fn_members_and_recursion.txt`](tests/opt/fn_members_and_recursion.txt)).

**Inlining.** A drill called exactly once that is not recursive -- it cannot reach itself through the calls in its
body -- is put where it was called: each parameter becomes a tucked declaration initialised with its argument, the
body follows, its exit becomes the value where the call stood, and the drill, now with no call, is removed as
unused in the next round. Every name the body declares is renamed `f$name` -- `$` cannot be written in a
program, so nothing can collide with the caller's names, nor with another inlined body's -- and the result is
`f$result`. Member functions are not inlined: their bodies read the object they are called on.

| Inlined | Left alone |
|---|---|
| a body that leaves through its last `cuh`: `cuh value` becomes `T f$result post value` | a `cuh` inside a `run_it_back` or a `laps`: leaving a loop in the middle would need a `break` |
| a drill that returns nothing, called as a statement: just its body | a `spot` where neither arm leaves but one holds a `cuh`: the rest would be copied into both arms |
| early exits: a `spot` whose arm leaves -- the statements after it move into its other arm, so every `cuh` ends its path; then a sliding `f$result` starts at a default (0, `woof`, a literal of those) and every `cuh` posts to it. Arms nest, and both arms may leave | a call in the condition of `run_it_back`: the condition runs every round, the statements before the loop once |
| a call in a value, an argument, a print, a `spot` condition, the bounds of `laps` (evaluated once, before the loop) | a call after a part of its statement that is not quiet: `finna_hear() bump f(x)`, `y breakdown z bump f(x)` -- moving the call first would change the order |
| a `scat` in any shape: it ends the program from anywhere | a recursive drill, a drill called twice or more, a member function |

`spot n in_tune 0 { cuh 0 } spot n down_bad 0 { cuh 0 tuck_in 1 } cuh 1` becomes
`spot n in_tune 0 { r post 0 } pivot { spot n down_bad 0 { r post 0 tuck_in 1 } pivot { r post 1 } }` with
`r = sign$result` ([`tests/opt/inline_tail_exit.txt`](tests/opt/inline_tail_exit.txt),
[`tests/opt/inline_early_exit.txt`](tests/opt/inline_early_exit.txt)).

**The proof is mechanical.** `tests/opt` holds six programs, two per transformation, each with its expected
output and the tree after `--optimize --ast`; the output is the same with and without the flag, and every
program of `tests/ok` and `tests/err` passes with the flag too (`./run_tests.sh` runs them all both ways).

**Inlining in the IR.** `doze drill twice(doze n) { cuh n double_back 2 no_bap }`, called once as
`air_out(twice(x)) no_bap`. Without `--optimize`, `main` calls the drill, which has its own function:

```llvm
define i32 @"drill.twice"(i32 %"n")
  ...
  %"double_back" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %"n.2", i32 2)
  ...
  ret i32 %"double_back.1"

  ; in main:
  %"x.1" = load i32, i32* %"x"
  %".11" = call i32 @"drill.twice"(i32 %"x.1")
  %".13" = call i32 (i8*, ...) @"printf"(i8* %".12", i32 %".11")
```

With `--optimize` there is no `@"drill.twice"` in the module at all; the parameter and the result are slots of
`main`, and the multiplication -- with its overflow check -- sits where the call stood:

```llvm
  %"twice$n" = alloca i32
  %"twice$result" = alloca i32
  ...
  %"x.1" = load i32, i32* %"x"
  store i32 %"x.1", i32* %"twice$n"
  %"twice$n.1" = load i32, i32* %"twice$n"
  %"double_back" = call {i32, i1} @"llvm.smul.with.overflow.i32"(i32 %"twice$n.1", i32 2)
  ...
  store i32 %"double_back.1", i32* %"twice$result"
  %"twice$result.1" = load i32, i32* %"twice$result"
  %".19" = call i32 (i8*, ...) @"printf"(i8* %".18", i32 %"twice$result.1")
```

---

## 🏀 The real program: free throws at the O

[`programs/freethrows.txt`](programs/freethrows.txt) tracks a free-throw session at the court. It asks how many
hoopers step to the line (1 to 5), then each hooper calls their shots: `1` a make, `0` a miss, `9` done.
After each hooper it prints their `Hooper` object (makes, tries, streak, best streak), the percentage and one 🏀
per make; at the end it names the MVP, the best percentage. The squad `Hooper` has member functions `shoot`,
`percent` and `report`; `in_range` and `banner` are drills; `finna_hear()` reads every answer, `air_out` prints.
The loops carry it: a `laps` over the hoopers, a `run_it_back` over each hooper's shots, a `run_it_back` that asks
the count again until it is 1 to 5, and a `laps` in `report` that prints the balls.
- Session 1, two hoopers, 3 of 4 and 1 of 4: `./freethrows < programs/freethrows.in`
- Session 2, 0 and 7 rejected, three hoopers and a shot `5` that is no shot: `./freethrows < programs/freethrows.2.in`
- Each prints exactly `programs/freethrows.expected` / `programs/freethrows.2.expected`; `./run_tests.sh` checks both.

The binary is built with `llc` and `clang` -- `lli` is not the deliverable:

```bash
python3 compiler.py programs/freethrows.txt freethrows.ll
llc -filetype=obj -relocation-model=pic freethrows.ll -o freethrows.o
clang -fPIE freethrows.o -o freethrows
./freethrows < programs/freethrows.in
./freethrows < programs/freethrows.2.in
./freethrows
```

The last line is a session of your own. `./run_tests.sh` builds the binary both with and without `--optimize` and
runs both sessions on each (with `--optimize`, `banner` is inlined: it is called once).

---

## 🎨 Extra: VS Code highlighting

[`editors/vscode/`](editors/vscode) is a small VS Code extension that colours O-language: the types, `sliding`,
the control words (`spot`, `pivot`, `run_it_back`, `laps`, `from`, `thru`, `cuh`, `scat`), the operators (`bump`,
`post`, `in_tune`, `up_on`, …), `merch` / `woof`,
`air_out` and `finna_hear`, `no_bap`, `pab_on`, strings, numbers and `lowkey` comments. On top of the words it
knows the shapes: the name after `squad` and after `drill`, a squad used as a type (`Point p post …`,
`sliding Point center no_bap`, `Point drill origin()`), a literal `Point{3, 4}`, a field after a `.`, and a member
call `c.center.lift(1)`. `spot ok {` stays a condition and a block, as in the compiler: only a name written
right against its `{` is a literal. The contextual Stage 3 words are coloured as words everywhere, even where
a program uses one as a name. A highlighter cannot know which names are squads, so an unknown type like
`int x post 5` is coloured as one too -- the compiler is the one that rejects it.

It is a grammar and a language configuration, no code: `lowkey` is the line comment (`Cmd+/` toggles it),
brackets match and close, and a line after `{` is indented. Install it by linking the folder into VS Code's
extensions and restarting VS Code:

```bash
ln -s "$PWD/editors/vscode" ~/.vscode/extensions/o-language
```

Files ending in `.ol` or `.olang` open as O-language. The tests are `.txt`: pick *O-language* with *Change
Language Mode* in the status bar, or map them in your settings with `"files.associations": {"*.txt": "o-language"}`
for this workspace.

The grammar was checked with the TextMate engine VS Code itself uses (`vscode-textmate` and `vscode-oniguruma`)
over every program in `tests/`: every squad is coloured as a type, and no variable is.

---

## 🗂️ What's in the repo

```
compiler.py       entry point: compile to .ll, --ast, --ast-checked, --tokens, --optimize, error reporting
grammar.ebnf      the grammar in EBNF
src/lexer.py      Token and lex(): byte-by-byte state machine (START, WORD, NUMBER, STRING, COMMENT)
src/parser.py     Parser: recursive descent, peek()/eat(), one method per grammar rule
src/ast_nodes.py  ASTNode, ProgramNode, FunctionNode, StmtNode + statements, ExprNode + expressions, dump()
src/semantic.py   SemanticChecker: the symbol table, names, types, drills and constants; annotates the tree
src/optimizer.py  --optimize: unused variables, unused functions and inlining, on the checked tree
src/codegen.py    CodeGen: walks the checked tree and builds the module with the llvmlite builder
src/errors.py     CompileError with line and column
tests/ok/         valid programs, their expected output (.expected), input (.in) and tree dumps (.ast)
tests/err/        invalid programs and their expected error line
tests/opt/        tests of the optimizer: programs, their output (.expected) and the tree after --optimize --ast
programs/         freethrows.txt, the real program, and its recorded sessions (.in / .expected)
run_tests.sh      compiles and runs every test and reports PASS / FAIL
full_compiler.sh  source -> output.ll -> output.o -> program, and runs it
githooks/         pre-push: the tests before every push (git config core.hooksPath githooks)
editors/vscode/   the VS Code extension: syntax highlighting and comment / bracket rules
.github/workflows tests.yml: the tests and a native build on every push and pull request
ai_usage.txt      how AI was used for Stage 1
ai_usage_2.txt    how AI was used for Stage 2
ai_usage_3.txt    how AI was used for Stage 3
```

---

> 🏀 *Run it back, cuh: write it clean, close your blocks, end every line with `no_bap`.* 👟💯

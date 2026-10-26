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
builder. The only IR text the compiler writes is the module the builder printed.

```
source bytes ──lexer──► tokens ──parser──► AST ──semantic pass──► checked AST ──codegen──► output.ll ──lli / llc + clang──► 🏀
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
| `squad Name { … }` | a structure: a type with fields | `a.b.c` | a field, through a chain |
| `obj.f( … )` | a member function call | `finna_hear()` | read one integer from the input |

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
| parser | a missing `no_bap`, type, name, `post` initialiser, `{` or `}`; a function without `drill` (`doze f() { … }`); `sliding` after the type; an empty block; `pivot` without `spot`; two operators in a row or an operator with no right side; two comparisons without `( )`; an unclosed `(`; a keyword used as a name; a string outside `air_out`; a `drill` inside a block; a constant initialiser that overflows its type, or divides by zero; an inverted line that does not end with its line or does not end in `post name`, `cuh` or `scat` |
| parser (squads) | a squad inside a block or without fields; a field with a `post` value; a squad's name not followed by `{`; a type that is not a squad declared above |
| semantic pass | every rule of the tables above: a name not declared or declared twice, a post to a tucked variable or through a tucked chain, a type that does not fit, a wrong call, a misplaced or missing `cuh`, an unknown field, a wrong literal, a squad that contains itself, a constant that overflows or divides by zero |

---

## 🗂️ What's in the repo

```
compiler.py       entry point: compile to .ll, --ast, --ast-checked, --tokens, error reporting
grammar.ebnf      the grammar in EBNF
src/lexer.py      Token and lex(): byte-by-byte state machine (START, WORD, NUMBER, STRING, COMMENT)
src/parser.py     Parser: recursive descent, peek()/eat(), one method per grammar rule
src/ast_nodes.py  ASTNode, ProgramNode, FunctionNode, StmtNode + statements, ExprNode + expressions, dump()
src/semantic.py   SemanticChecker: the symbol table, names, types, drills and constants; annotates the tree
src/codegen.py    CodeGen: walks the checked tree and builds the module with the llvmlite builder
src/errors.py     CompileError with line and column
tests/ok/         valid programs, their expected output (.expected), input (.in) and tree dumps (.ast)
tests/err/        invalid programs and their expected error line
run_tests.sh      compiles and runs every test and reports PASS / FAIL
full_compiler.sh  source -> output.ll -> output.o -> program, and runs it
ai_usage.txt      how AI was used for this stage
```

---

> 🏀 *Run it back, cuh: write it clean, close your blocks, end every line with `no_bap`.* 👟💯

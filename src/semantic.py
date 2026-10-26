"""Phase 2: a walk over the AST that checks it  (semantic errors)

A pass of its own, run on the whole tree before the code generator is even constructed:
it rejects the program before a single instruction exists, and it can be tested without
LLVM at all. It owns the symbol table, and it answers the questions the parser cannot:
which declaration does this name mean, and what is the type of this expression?

The symbol table is a stack of frames, one per scope, each a dict name -> DeclNode (which
knows the type and whether it is sliding). The program has the bottom frame; every block
-- the arms of spot and pivot -- pushes an empty frame on entry and pops it on exit. A
declaration goes into the top frame, and only the top frame is checked for a duplicate,
so a block may declare a name again: shadowing. A use walks the frames from the top down
and takes the first hit; a name in no frame, including one whose block is already
closed, is used before its declaration.

A drill gets a stack of its own: its bottom frame holds the parameters, and the lines of
its body go into that same frame, so a parameter cannot be declared again. The program's
frames are not on that stack -- a drill sees its parameters, its own variables and the
drills, never a variable of the top level, which lives in main.

Drills sit in a table of their own, name -> FunctionNode. It is filled with every
signature before any body is checked, so a drill may call itself or one declared below.

Its contract with the code generator is a handful of fields on the tree:
  * `node.type` on every expression -- "doze", "fawty", "line", or None for the call
    of a drill that returns nothing (which is only ever a statement of its own);
  * `node.const` on every expression -- its value when the compiler knows it, else None;
  * `node.decl` on every VarNode and AssignNode -- the DeclNode or ParamNode the name
    resolved to;
  * `node.fn` on every CallNode -- the FunctionNode it calls.
The generator reads those and looks nothing up by name. With shadowing that matters:
three x in three blocks are three declarations, and this pass is the one that knows
which one is meant.

The name rules:
  * a variable is declared before it is used, and once per block;
  * a drill sees its parameters and its own variables, not the top level;
  * a drill is declared once, and its parameters have different names;
  * only a sliding variable is posted to again; a parameter never is.

The type rules:
  * a number has the narrowest type it fits: doze, else fawty;
  * bump, tuck_in, double_back, breakdown and scraps take two integers and give the
    wider of the two; a line operand is an error;
  * in_tune and fugazi take two integers (any mix of widths) or two lines, and give a line;
  * a doze value may go where a fawty is expected -- and that is the only conversion in
    the language: never fawty into doze, never across line;
  * the condition of spot and of on_the_guys is a line;
  * air_out takes a string, an integer or a line; scat takes an integer, a line, or nothing;
  * a call takes one argument per parameter, each one assignable to the parameter's
    type, and has the drill's result type; a drill that returns nothing has no value.

The drill rules:
  * cuh is only inside a drill; it carries a value of the result type, or nothing in a
    drill that returns nothing;
  * a drill with a result type leaves on every path: its body ends with cuh or scat, or
    with a spot and pivot whose arms both leave -- otherwise it could reach its end.

The constant rules (the overflow check the parser could not make):
  * an expression made of numbers, operators and tucked variables whose own value is
    such an expression is a constant: the compiler computes it exactly, with no limit on
    the size of the steps in between;
  * a constant made of numbers only has the narrowest type its value fits, and may land
    in any integer it fits -- as in stage 1, `doze min post 0 tuck_in 2147483648` is fine;
  * a constant with a name in it has the type the type rules give it, made wider when its
    value needs it -- so a fawty name keeps it a fawty, and it never lands in a doze;
  * a constant must fit the type of the place it lands in -- a doze takes
    -2147483648 .. 2147483647, a fawty -9223372036854775808 .. 9223372036854775807;
  * a constant division by zero is an error.
So `doze max post 2147483647 no_bap` then `doze y post max bump 1 no_bap` is rejected, while
`fawty big post max bump 1 no_bap` is 2147483648 -- the code generator emits a constant as
one number of the type it lands in, never as an addition that could overflow on the
way. Everything that is not constant is checked when the program runs.
"""

from .ast_nodes import DeclNode, ExitNode, FunctionNode, IfNode, ParamNode, ReturnNode, StringNode
from .errors import CompileError, error_at
from .parser import RANGES

INTEGERS = ("doze", "fawty")


def wider(left, right):
    return "fawty" if "fawty" in (left, right) else "doze"


def narrowest(value):
    """The type of a constant: doze when it fits, else fawty, else None."""
    for type_name in INTEGERS:
        low, high = RANGES[type_name]
        if low <= value <= high:
            return type_name
    return None


def fold(node, left, right):
    """The value of a constant operation, computed exactly; / and % round toward zero, as
    the generated sdiv and srem do."""
    if node.symbol in "/%" and right == 0:
        raise error_at(node, f"division by zero in a constant expression ('{node.op}' by 0)")
    if node.symbol == "+":
        return left + right
    if node.symbol == "-":
        return left - right
    if node.symbol == "*":
        return left * right
    quotient = abs(left) // abs(right) * (1 if (left < 0) == (right < 0) else -1)
    return quotient if node.symbol == "/" else left - quotient * right


def leaves(body):
    """Does a run of statements always leave -- with cuh or scat -- before its end?"""
    for stmt in body:
        if isinstance(stmt, (ReturnNode, ExitNode)):
            return True
        if isinstance(stmt, IfNode) and stmt.else_body is not None \
                and leaves(stmt.then_body) and leaves(stmt.else_body):
            return True
    return False


class SemanticChecker:
    def __init__(self):
        self.scopes = [{}]                # frames, innermost last: name -> DeclNode | ParamNode
        self.fns = {}                     # name -> FunctionNode, every signature before any body
        self.current_fn = None            # the FunctionNode whose body is being checked, or None
        self.top_level_names = set()      # names the top level declares, to explain a drill's error

    def run(self, program):
        program.accept(self)
        return program

    def find(self, name):
        """The declaration `name` means here, or None: the innermost frame that has it wins."""
        for frame in reversed(self.scopes):
            if name in frame:
                return frame[name]
        return None

    def lookup(self, node, name):
        decl = self.find(name)
        if decl is not None:
            return decl
        if self.current_fn is not None and name in self.top_level_names:
            raise error_at(node, f"drill '{self.current_fn.name}' cannot see the top-level variable "
                                 f"'{name}': a drill sees only its parameters and its own variables")
        raise error_at(node, f"variable '{name}' is used before its declaration")

    def declare(self, node):
        if node.name in self.scopes[-1]:  # only this frame: an outer one may be shadowed
            prev = self.scopes[-1][node.name]
            raise error_at(node, f"'{node.name}' is already declared in this block, "
                                 f"at line {prev.line}:{prev.col}")
        self.scopes[-1][node.name] = node

    def block(self, body):
        """A block is a scope: its names are gone after its '}'."""
        self.scopes.append({})
        for stmt in body:
            stmt.accept(self)
        self.scopes.pop()

    # -- where a value lands ------------------------------------------------

    def value(self, expr):
        """Type an expression whose value is used: a drill that returns nothing has none."""
        type_name = expr.accept(self)
        if type_name is None:
            raise error_at(expr, f"drill '{expr.name}' returns nothing: its call has no value to use")
        return type_name

    def fits(self, expr, type_name):
        """A constant must fit the integer type it lands in."""
        if expr.const is None or type_name not in RANGES:
            return
        low, high = RANGES[type_name]
        if not low <= expr.const <= high:
            raise error_at(expr, f"{type_name} overflow: the value {expr.const} does not fit in "
                                 f"{type_name} ({low} .. {high})")

    def check_value(self, expr, want, what):
        """The value `expr` lands where a `want` is expected; `what` names the place."""
        have = self.value(expr)
        if want in RANGES:
            self.fits(expr, want)         # a constant too big says so, whatever its type
        if have == want or (have == "doze" and want == "fawty"):
            return                        # the one widening the language does for you
        if getattr(expr, "numbers_only", False) and want in RANGES:
            return                        # numbers only: it fits, and that is all it needs
        raise error_at(expr, f"{what} must be {want}, got {have}")

    def operand(self, expr):
        """An integer or a line used as it is: a constant must fit at least in fawty."""
        type_name = self.value(expr)
        self.fits(expr, "fawty")
        return type_name

    # -- the program and the drills -----------------------------------------

    def visit_program(self, node):
        self.top_level_names = {s.name for s in top_level_decls(node.items)}
        for item in node.items:           # every signature first...
            if isinstance(item, FunctionNode):
                self.declare_fn(item)
        for item in node.items:           # ...then everything in program order
            item.accept(self)

    def declare_fn(self, node):
        if node.name in self.fns:
            prev = self.fns[node.name]
            raise error_at(node, f"drill '{node.name}' is already declared at line {prev.line}:{prev.col}")
        names = set()
        for param in node.params:
            if param.name in names:
                raise error_at(param, f"drill '{node.name}' already has a parameter '{param.name}'")
            names.add(param.name)
        self.fns[node.name] = node

    def visit_function(self, node):
        # A fresh stack: the parameters, and the body's lines in the same frame. Nothing of
        # the program's frames is on it, so a top-level variable is not visible here.
        outer = self.scopes
        self.scopes = [{param.name: param for param in node.params}]
        self.current_fn = node
        for stmt in node.body:
            stmt.accept(self)
        if node.return_type is not None and not leaves(node.body):
            raise error_at(node, f"drill '{node.name}' can reach its end without 'cuh': "
                                 f"it must leave with a {node.return_type}")
        self.scopes, self.current_fn = outer, None

    def visit_param(self, node):
        pass                              # its name is in the drill's bottom frame

    # -- statements ---------------------------------------------------------

    def visit_decl(self, node):
        # Typed before the name exists: `doze t post t` is an error, and in a block that
        # shadows an outer t, `fawty t post t bump 1` reads the outer one.
        self.check_value(node.init, node.type_name, f"the value of '{node.name}'")
        node.const = node.init.const if not node.mutable else None
        self.declare(node)

    def visit_assign(self, node):
        decl = self.lookup(node, node.name)
        if isinstance(decl, ParamNode):
            raise error_at(node, f"cannot post to '{node.name}': it is a parameter of "
                                 f"'{self.current_fn.name}', and parameters are tucked")
        if not decl.mutable:
            raise error_at(node, f"cannot post to '{node.name}': it is tucked, "
                                 f"declare it 'sliding {decl.type_name} {node.name}' to change it")
        self.check_value(node.value, decl.type_name, f"the value posted to '{node.name}'")
        node.decl = decl

    def visit_call_stmt(self, node):
        node.call.accept(self)            # a statement may drop the result, or have none

    def visit_if(self, node):
        self.check_value(node.cond, "line", "the condition of 'spot'")
        self.block(node.then_body)
        if node.else_body is not None:
            self.block(node.else_body)

    def visit_return(self, node):
        fn = self.current_fn
        if fn is None:
            raise error_at(node, "'cuh' leaves a drill, and this is the top level: use 'scat' to end the program")
        if fn.return_type is None:
            if node.value is not None:
                raise error_at(node.value, f"drill '{fn.name}' returns nothing, but 'cuh' carries a value")
            return
        if node.value is None:
            raise error_at(node, f"drill '{fn.name}' returns {fn.return_type}: 'cuh' needs a value")
        self.check_value(node.value, fn.return_type, f"the value of 'cuh' in '{fn.name}'")

    def visit_exit(self, node):
        if node.value is not None:
            self.operand(node.value)

    def visit_assert(self, node):
        self.check_value(node.cond, "line", "the condition of 'on_the_guys'")

    def visit_print(self, node):
        if isinstance(node.value, StringNode):
            node.value.accept(self)
        else:
            self.operand(node.value)

    # -- expressions: return the type ---------------------------------------

    def visit_binop(self, node):
        left, right = self.value(node.left), self.value(node.right)
        if node.symbol in ("==", "!="):
            if not ((left in INTEGERS and right in INTEGERS) or left == right == "line"):
                raise error_at(node, f"'{node.op}' compares two integers or two lines, got {left} and {right}")
            self.fits(node.left, "fawty")
            self.fits(node.right, "fawty")
            node.type, node.const = "line", None
            return node.type
        for side, type_name in ((node.left, left), (node.right, right)):
            if type_name not in INTEGERS:
                raise error_at(side, f"'{node.op}' takes integers, got {type_name}")
        if node.left.const is not None and node.right.const is not None:
            node.const = fold(node, node.left.const, node.right.const)
            # Too big for fawty is fine on the way: only where it lands does it count.
            fitting = narrowest(node.const) or "fawty"
            node.numbers_only = getattr(node.left, "numbers_only", False) and \
                getattr(node.right, "numbers_only", False)
            node.type = fitting if node.numbers_only else wider(wider(left, right), fitting)
            return node.type
        self.fits(node.left, "fawty")
        self.fits(node.right, "fawty")
        node.type, node.const = wider(left, right), None
        return node.type

    def visit_call(self, node):
        fn = self.fns.get(node.name)
        if fn is None:
            raise error_at(node, f"drill '{node.name}' is not declared")
        if len(node.args) != len(fn.params):
            raise error_at(node, f"drill '{fn.name}' takes {plural(len(fn.params), 'argument')}, "
                                 f"got {len(node.args)}")
        for param, arg in zip(fn.params, node.args):
            self.check_value(arg, param.type_name, f"argument '{param.name}' of '{fn.name}'")
        node.fn, node.type, node.const = fn, fn.return_type, None
        return node.type

    def visit_var(self, node):
        decl = self.lookup(node, node.name)
        node.decl, node.type = decl, decl.type_name
        node.const = getattr(decl, "const", None)   # a tucked variable with a constant value
        return node.type

    def visit_int(self, node):
        node.type, node.const = narrowest(node.value), node.value   # the lexer saw to the range
        node.numbers_only = True
        return node.type

    def visit_bool(self, node):
        node.type, node.const = "line", None
        return node.type

    def visit_string(self, node):
        node.type, node.const = "string", None   # only ever the value of air_out: the parser sees to it
        return node.type


def top_level_decls(items):
    """The declarations of the top level, in its blocks too: a drill cannot see them."""
    for item in items:
        if isinstance(item, DeclNode):
            yield item
        elif isinstance(item, IfNode):
            yield from top_level_decls(item.then_body)
            yield from top_level_decls(item.else_body or [])


def plural(count, word):
    return f"{count} {word}" + ("" if count == 1 else "s")


def check(program):
    """Check a tree and annotate it; raise CompileError on the first problem."""
    return SemanticChecker().run(program)

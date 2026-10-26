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

Squads sit in a third table, name -> SquadNode, filled first of all: a squad is declared
above every use of its name (the parser sees to that), and each of its fields gets its
`index` -- its place in the squad, the number a gep takes. A chain c.center.x is walked
link by link: c is a variable, its type is a squad, center is a field of that squad,
its type is a squad again, x is a field of that one; the field numbers go on the node,
so the code generator never looks a field up by its name.

Its contract with the code generator is a handful of fields on the tree:
  * `node.type` on every expression -- "doze", "fawty", "line", or None for the call
    of a drill that returns nothing (which is only ever a statement of its own);
  * `node.const` on every expression -- its value when the compiler knows it, else None;
  * `node.decl` on every VarNode, FieldNode and AssignNode -- the DeclNode or ParamNode
    the name resolved to;
  * `node.indices` on every FieldNode and AssignNode -- the chain as field numbers, so
    c.center.x is [0, 0] -- and `node.target_type` on every AssignNode: the type of what
    is written, the variable's or the last field's;
  * `node.squad` on every LiteralNode -- the SquadNode it builds, for its fields' types;
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
  * air_out takes a string, an integer, a line or an object; scat takes an integer, a
    line, or nothing;
  * finna_hear() reads one integer from the standard input and is a doze;
  * a call takes one argument per parameter, each one assignable to the parameter's
    type, and has the drill's result type; a drill that returns nothing has no value.

The squad rules:
  * a squad is declared once, at the top level, with at least one field, and its fields
    have different names; a field's type is built in or a squad above -- never the
    squad itself, so no squad can contain itself;
  * a squad's name is not the name of a drill;
  * a literal Point{3, 4} gives one value per field, in field order, each one of the
    field's type (a doze may go into a fawty field);
  * a chain names a field that exists at every link, and every link but the last is a
    squad;
  * posting through c.center.x needs c, center and x all sliding: a tucked link anywhere
    on the way makes the whole chain read-only, and a parameter is always tucked;
  * a whole object is not posted to again -- `p post q` is an error: its fields are,
    one by one. `Point q post p` declares a copy, and a squad goes into a parameter and
    out of a drill as a copy too;
  * squads are not compared, not used in arithmetic, and not a value of scat.

A member function is checked like a drill, with its squad around it: its own stack of
parameters and variables, and nothing of the top level. A name in none of its frames may
still be a field of the object it is called on: x means this.x, so the name resolves to
the function's ThisParam with the field first in the chain. A call f(...) in its body
looks among the member functions of the same squad first, then among the drills.

The mutation rule needs every member body at once. A member function is mutating when it
posts to a field of its object, or calls a mutating member function on its object or on
one of its fields -- and member functions may call each other in a cycle. So the member
bodies are checked first, each noting whether it writes a field and which member
functions it calls on its own object; then the mutating ones are marked: first those
that write a field, then, again and again, every one that calls a marked one, until a
pass marks nothing new. Only then is a member call inside a member body checked against
the rule; the drills and the top level come after, so their member calls are checked on
the spot. A mutating member function is called only through a chain whose every link is
sliding: the variable and each field on the way.

The member function rules:
  * a member function is called on an object: obj.f(args), c.center.f(args), or f(args)
    inside another member function of the same squad, on the same object;
  * it takes one argument per parameter, each of the parameter's type, like a drill;
  * inside it, a name is looked up among its parameters and variables first (the
    innermost block wins), then among the fields of its squad, and nowhere else: a
    parameter or a variable hides a field of the same name, and a top-level variable is
    never visible;
  * a call inside it looks among the member functions of its squad first, then the drills;
  * a field and a member function of one squad do not share a name, nor do two member
    functions;
  * a mutating member function -- one that posts to a field, or calls a mutating one on its
    object or a field of it -- is called only on an object reached through sliding links.

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

from .ast_nodes import (DeclNode, ExitNode, FunctionNode, IfNode, Link, ParamNode, ReturnNode, SquadNode,
                        StringNode, ThisParam, chain, written)
from .errors import CompileError, error_at
from .parser import RANGES

INTEGERS = ("doze", "fawty")
SCALARS = ("doze", "fawty", "line")


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
        self.squads = {}                  # name -> SquadNode, every one before anything else
        self.current_fn = None            # the FunctionNode whose body is being checked, or None
        self.top_level_names = set()      # names the top level declares, to explain a drill's error
        self.mutation_known = False       # every member function is marked mutating or not
        self.deferred = []                # member calls in member bodies, checked once it is

    def run(self, program):
        program.accept(self)
        return program

    def find(self, name):
        """The declaration `name` means here, or None: the innermost frame that has it wins."""
        for frame in reversed(self.scopes):
            if name in frame:
                return frame[name]
        return None

    def lookup(self, node, name, links):
        """The declaration `name` means here, and the chain from it: in a member function, a
        name in no frame may be a field of the object -- x is this.x."""
        decl = self.find(name)
        if decl is not None:
            return decl, links
        fn = self.current_fn
        if fn is not None and fn.squad is not None:
            field = named(self.squads[fn.squad].fields, name)
            if field is not None:
                return fn.this, [Link(name, node.line, node.col), *links]
        if fn is not None and name in self.top_level_names:
            raise error_at(node, f"drill '{qualified(fn)}' cannot see the top-level variable "
                                 f"'{name}': a drill sees only its parameters and its own variables")
        if fn is not None and fn.squad is not None:
            raise error_at(node, f"'{name}' is not a parameter, a variable or a field of '{fn.squad}'")
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

    def operand(self, expr, what):
        """An integer or a line used as it is: a constant must fit at least in fawty."""
        return self.scalar(expr, self.value(expr), what)

    def scalar(self, expr, type_name, what):
        if type_name not in SCALARS:
            raise error_at(expr, f"{what}, got {type_name}")
        self.fits(expr, "fawty")
        return type_name

    def walk_chain(self, node, write):
        """Follow node.name, then its links; store decl and indices on the node and return
        the type at the end. With `write`, every link must be sliding. Without it, the first
        link that is not is kept in node.tucked_link, for the mutation rule."""
        written_links = getattr(node, "links", [])
        decl, links = self.lookup(node, node.name, written_links)
        target = chain(node.name, written_links)
        if write and isinstance(decl, ParamNode):
            who = "it" if not links else f"'{node.name}'"
            raise error_at(node, f"cannot post to '{target}': {who} is a parameter of "
                                 f"'{qualified(self.current_fn)}', and parameters are tucked")
        if write and not decl.mutable:
            if not links:
                raise error_at(node, f"cannot post to '{node.name}': it is tucked, "
                                     f"declare it 'sliding {decl.type_name} {node.name}' to change it")
            raise error_at(node, f"cannot post to '{target}': '{node.name}' is tucked")
        if write and isinstance(decl, ThisParam):
            self.current_fn.assigns_field = True       # it changes its object: mutating
        tucked = isinstance(decl, ParamNode) or not decl.mutable
        node.tucked_link = node.name if tucked else None
        type_name, path, indices = decl.type_name, None if isinstance(decl, ThisParam) else node.name, []
        for link in links:
            squad = self.squads.get(type_name)
            if squad is None:
                raise error_at(link, f"'{path}' is {type_name}, not a squad: it has no field '{link.name}'")
            field = named(squad.fields, link.name)
            if field is None:
                raise error_at(link, f"squad '{squad.name}' has no field '{link.name}'")
            path = link.name if path is None else f"{path}.{link.name}"
            if write and not field.mutable:
                raise error_at(link, f"cannot post to '{target}': field '{link.name}' of "
                                     f"{squad.name} is tucked")
            if not field.mutable and node.tucked_link is None:
                node.tucked_link = path
            indices.append(field.index)
            type_name = field.type_name
        node.decl, node.indices = decl, indices
        return type_name

    # -- the program and the drills -----------------------------------------

    def visit_program(self, node):
        self.top_level_names = {s.name for s in top_level_decls(node.items)}
        for item in node.items:           # every squad first: each one is above its uses
            if isinstance(item, SquadNode):
                item.accept(self)
        for item in node.items:           # then every signature...
            if isinstance(item, FunctionNode):
                self.declare_fn(item)
        methods = [method for squad in self.squads.values() for method in squad.methods]
        for method in methods:            # ...then the member bodies, for the mutation rule,
            method.accept(self)
        self.mark_mutating(methods)
        self.mutation_known = True
        for call in self.deferred:
            self.check_mutation(call)
        for item in node.items:           # ...then everything else in program order
            if not isinstance(item, SquadNode):
                item.accept(self)

    def mark_mutating(self, methods):
        """Mark the member functions that change their object: those that post to a field,
        then every one that calls a marked one on its object or a field of it, until no
        pass marks a new one -- calls may go round in a cycle, so one pass is not enough."""
        for method in methods:
            method.mutating = method.assigns_field
        changed = True
        while changed:
            changed = False
            for method in methods:
                if not method.mutating and any(callee.mutating for callee in method.calls_on_self):
                    method.mutating = changed = True

    def check_mutation(self, node):
        """A mutating member function is called only through a chain of sliding links."""
        if node.fn.mutating and node.tucked_link is not None:
            raise error_at(node, f"cannot call '{node.name}' on '{node.object}': it changes its object, "
                                 f"and '{node.tucked_link}' is not sliding")

    def visit_squad(self, node):
        if node.name in self.squads:
            prev = self.squads[node.name]
            raise error_at(node, f"squad '{node.name}' is already declared at line {prev.line}:{prev.col}")
        seen = set()
        for index, field in enumerate(node.fields):
            if field.name in seen:
                raise error_at(field, f"squad '{node.name}' already has a field '{field.name}'")
            if field.type_name == node.name:
                raise error_at(field, f"squad '{node.name}' cannot contain itself: field '{field.name}' "
                                      f"would hold a {node.name}, which holds a {node.name}, ...")
            seen.add(field.name)
            field.index = index
        methods = set()
        for method in node.methods:
            if method.name in seen:
                raise error_at(method, f"squad '{node.name}' already has a field '{method.name}': "
                                       f"a member function cannot have the same name")
            if method.name in methods:
                raise error_at(method, f"squad '{node.name}' already has a member function '{method.name}'")
            methods.add(method.name)
            self.check_params(method)
            method.this = ThisParam(node.name)
            method.assigns_field, method.calls_on_self = False, []
        self.squads[node.name] = node

    def visit_field_decl(self, node):
        pass                              # checked with its squad

    def declare_fn(self, node):
        if node.name in self.squads:
            raise error_at(node, f"'{node.name}' is already the name of a squad: a drill needs another name")
        if node.name in self.fns:
            prev = self.fns[node.name]
            raise error_at(node, f"drill '{node.name}' is already declared at line {prev.line}:{prev.col}")
        self.check_params(node)
        self.fns[node.name] = node

    def check_params(self, node):
        names = set()
        for param in node.params:
            if param.name in names:
                raise error_at(param, f"drill '{qualified(node)}' already has a parameter '{param.name}'")
            names.add(param.name)

    def visit_function(self, node):
        # A fresh stack: the parameters, and the body's lines in the same frame. Nothing of
        # the program's frames is on it, so a top-level variable is not visible here.
        outer = self.scopes
        self.scopes = [{param.name: param for param in node.params}]
        self.current_fn = node
        for stmt in node.body:
            stmt.accept(self)
        if node.return_type is not None and not leaves(node.body):
            raise error_at(node, f"drill '{qualified(node)}' can reach its end without 'cuh': "
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
        target_type = self.walk_chain(node, write=True)
        target = chain(node.name, node.links)
        if target_type in self.squads:
            raise error_at(node, f"cannot post a whole {target_type} to '{target}': "
                                 f"post to its fields, one by one")
        self.check_value(node.value, target_type, f"the value posted to '{target}'")
        node.target_type = target_type

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
                raise error_at(node.value, f"drill '{qualified(fn)}' returns nothing, but 'cuh' carries a value")
            return
        if node.value is None:
            raise error_at(node, f"drill '{qualified(fn)}' returns {fn.return_type}: 'cuh' needs a value")
        self.check_value(node.value, fn.return_type, f"the value of 'cuh' in '{qualified(fn)}'")

    def visit_exit(self, node):
        if node.value is not None:
            self.operand(node.value, "'scat' takes an integer, a line or nothing")

    def visit_assert(self, node):
        self.check_value(node.cond, "line", "the condition of 'on_the_guys'")

    def visit_print(self, node):
        if isinstance(node.value, StringNode):
            node.value.accept(self)
        else:
            type_name = self.value(node.value)
            if type_name not in self.squads:                     # an object prints field by field
                self.scalar(node.value, type_name, "'air_out' takes a string, an integer, a line or an object")

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
        current = self.current_fn
        method = None
        if current is not None and current.squad is not None:
            method = named(self.squads[current.squad].methods, node.name)
        if method is not None:            # d2() inside Point: d2 on the same object
            current.calls_on_self.append(method)
            fn = method
        else:
            fn = self.fns.get(node.name)
            if fn is None:
                raise error_at(node, f"drill '{node.name}' is not declared")
        self.check_args(node, fn)
        node.fn, node.type, node.const = fn, fn.return_type, None
        return node.type

    def visit_member_call(self, node):
        target = node.target
        type_name = self.walk_chain(target, write=False)
        target.type, target.const = type_name, None
        node.object = written(target)
        squad = self.squads.get(type_name)
        if squad is None:
            raise error_at(node, f"'{node.object}' is {type_name}, not a squad: "
                                 f"it has no member function '{node.name}'")
        fn = named(squad.methods, node.name)
        if fn is None:
            raise error_at(node, f"squad '{squad.name}' has no member function '{node.name}'")
        self.check_args(node, fn)
        node.tucked_link = target.tucked_link
        if isinstance(target.decl, ThisParam):    # on a field of its own object
            self.current_fn.calls_on_self.append(fn)
        node.fn, node.type, node.const = fn, fn.return_type, None
        if self.mutation_known:
            self.check_mutation(node)
        else:                             # in a member body: not every function is marked yet
            self.deferred.append(node)
        return node.type

    def check_args(self, node, fn):
        """One argument per parameter, each assignable to the parameter's type."""
        if len(node.args) != len(fn.params):
            raise error_at(node, f"drill '{qualified(fn)}' takes {plural(len(fn.params), 'argument')}, "
                                 f"got {len(node.args)}")
        for param, arg in zip(fn.params, node.args):
            self.check_value(arg, param.type_name, f"argument '{param.name}' of '{qualified(fn)}'")

    def visit_field(self, node):
        node.type, node.const = self.walk_chain(node, write=False), None
        return node.type

    def visit_literal(self, node):
        squad = self.squads[node.type_name]       # the parser only makes a literal of a squad
        if len(node.values) != len(squad.fields):
            raise error_at(node, f"squad '{squad.name}' has {plural(len(squad.fields), 'field')}, "
                                 f"so {squad.name}{{...}} takes {plural(len(squad.fields), 'value')}, got {len(node.values)}")
        for field, value in zip(squad.fields, node.values):
            self.check_value(value, field.type_name, f"field '{field.name}' of {squad.name}")
        node.type, node.const, node.squad = squad.name, None, squad
        return node.type

    def visit_var(self, node):
        node.type = self.walk_chain(node, write=False)    # x in a member function may be this.x
        node.const = getattr(node.decl, "const", None)    # a tucked variable with a constant value
        return node.type

    def visit_read(self, node):
        node.type, node.const = "doze", None
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


def named(nodes, name):
    """The node of `nodes` -- fields or member functions -- called `name`, or None."""
    return next((node for node in nodes if node.name == name), None)


def qualified(fn):
    """A drill's name in a message: Point.lift for a member function."""
    return f"{fn.squad}.{fn.name}" if fn.squad is not None else fn.name


def plural(count, word):
    return f"{count} {word}" + ("" if count == 1 else "s")


def check(program):
    """Check a tree and annotate it; raise CompileError on the first problem."""
    return SemanticChecker().run(program)

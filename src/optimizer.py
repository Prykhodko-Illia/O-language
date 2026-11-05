"""Phase 2.5: making the checked tree smaller  (--optimize)

Three transformations of the tree the semantic pass has accepted and annotated, run
before the code generator, so the generator never knows they ran. Every name in the tree
already points at its declaration through `decl` and every call at its function through
`fn`, so nothing here looks a name up: two x in two blocks are two DeclNodes, and the
pass counts, removes and renames by node, never by spelling. That is how scopes and
shadowing are respected without a symbol table.

The three run in rounds -- unused functions, unused variables, then one inlining -- until a
round changes nothing: each one can feed the others. An inlined function has no call
left and goes as unused; an inlined body may hold a declaration nobody reads; a removed
body may hold the only call of another function. Every round that does not stop removes
a declaration or a function, or inlines one, which leaves one function fewer, so it stops.

Unused variables. A read is every VarNode and FieldNode whose `decl` is the declaration --
in a value, a condition, an argument, a print, the start of a chain, the object of a
member call. A post to it is not a read: `y post 5` on a y nobody reads is as dead as y.
A declaration with no reads is removed with every post to it -- but only when nothing
it would take away can be seen. A value is *quiet* when it can neither be observed nor
fail: a number, merch or woof, a variable or a field, a constant the semantic pass
folded, a comparison of quiet values, a literal of quiet values. Anything else is kept:
a call (it may print, read, or never return), finna_hear() (it eats a line of input), and
arithmetic that is not a constant (bump, tuck_in and double_back may overflow, breakdown
and scraps may divide by zero, and each of those prints a line and ends the program). So
a declaration whose value, or one of whose posts, is not quiet stays, and so does that
post. Parameters, counters and fields stay: they are part of a signature, a loop, a type.
Removing a declaration takes its reads with it, so the next round counts again.

Unused functions. Every call is counted, wherever it stands: in the top level, in a drill,
in a member function, in a loop. A call inside the function's own body does not count, so
a drill that only calls itself is unused as well. A drill or a member function with no
call left is removed with its whole body, and the calls in that body go with it -- the
next round may find another function at zero. Two functions that only call each other
keep each other: counting cannot see a cycle.

Inlining. A drill -- not a member function, whose body reads its object -- called exactly
once, and never recursive (it cannot reach itself through the calls in its body), is put
where it is called:
  * each parameter becomes a tucked declaration initialised with its argument, in order:
    the arguments are evaluated where they were, before the body;
  * the body follows, and its exit becomes the value that stands where the call stood: a
    body that ends with `cuh value` and has no other cuh becomes `T f$result post value`;
    a body with an early exit gets a sliding `f$result` first, with a default value
    (0, woof, or a literal of those), and every cuh becomes a post to it;
  * every name the body declares is renamed f$name: a '$' cannot be written in a program,
    so the new names cannot collide with the caller's, or with another inlined body's;
  * the call is replaced by a read of f$result -- or, for a call that was a statement of
    its own, disappears.
Then the drill has no call, and the next round removes it as unused.

The body shapes that are inlined. A cuh at the end of the body. A spot whose arm leaves
(cuh or scat at the end of it) is an early exit: the statements after the spot move into
its other arm, so every cuh becomes the last statement of its path, and the cuh then
turns into a post and the path just ends -- spot c { cuh 1 } cuh 2 is spot c { r post 1 }
pivot { r post 2 }. Both arms may leave; arms nest. Left alone: a cuh inside a
run_it_back or a laps (leaving a loop in the middle would need a break), and a spot where
neither arm leaves but one of them holds a cuh (the rest would be copied into both arms).
A scat stays where it is in every shape -- it ends the program from anywhere.

The places a call is inlined from. The statements before the call's statement are not
touched; the parameter declarations and the body go right before it. That moves the call
ahead of the parts of its statement evaluated before it, which is safe only when those
parts are quiet: f(x) bump 1, air_out(f(x)), 2 double_back 3 bump f(x) and spot f(x) ... are
inlined, while finna_hear() bump f(x) and y breakdown z bump f(x) are not (the read, or the
division that may fail, must come first). When the arguments of the call hold a member
call, which may change an object, nothing before the call may read a variable. A call in
the condition of a run_it_back is never inlined: the condition runs before every round,
and the statements before the loop run once. A call in the bounds of laps is: they are
evaluated once, before the first round.
"""

import copy

from .ast_nodes import (AssignNode, BinOpNode, BoolNode, CallNode, CallStmtNode, DeclNode, ExitNode, FieldNode,
                        ForNode, FunctionNode, IfNode, IntNode, LiteralNode, MemberCallNode, ParamNode, PrintNode,
                        AssertNode, ReturnNode, SquadNode, VarNode, WhileNode)
from .semantic import leaves

COMPARISONS = ("==", "!=", ">", "<")


# -- walking the tree ---------------------------------------------------------

def walk(node):
    """`node` and everything under it, in the order of the dump."""
    yield node
    for child in node.children():
        yield from walk(child)


def functions(program):
    """Every drill and every member function, with the list that holds it."""
    for item in program.items:
        if isinstance(item, FunctionNode):
            yield item, program.items
        elif isinstance(item, SquadNode):
            for method in item.methods:
                yield method, item.methods


def statement_lists(program):
    """Every list of statements in the program -- the top level, every body and every arm
    -- each with the function it belongs to (None for the top level)."""
    def inside(stmts, owner):
        yield stmts, owner
        for stmt in stmts:
            if isinstance(stmt, IfNode):
                yield from inside(stmt.then_body, owner)
                if stmt.else_body is not None:
                    yield from inside(stmt.else_body, owner)
            elif isinstance(stmt, (WhileNode, ForNode)):
                yield from inside(stmt.body, owner)

    yield from inside(program.items, None)          # the squads and drills in it hold no statement
    for fn, _ in functions(program):
        yield from inside(fn.body, fn)


def own_values(stmt):
    """The expressions a statement evaluates itself, in the order it evaluates them -- not
    the ones in the blocks it holds, which have statements of their own."""
    if isinstance(stmt, DeclNode):
        return [stmt.init]
    if isinstance(stmt, AssignNode):
        return [stmt.value]
    if isinstance(stmt, CallStmtNode):
        return [stmt.call]
    if isinstance(stmt, (IfNode, WhileNode, AssertNode)):
        return [stmt.cond]
    if isinstance(stmt, ForNode):
        return [stmt.start, stmt.end]
    if isinstance(stmt, (ReturnNode, ExitNode, PrintNode)):
        return [stmt.value] if stmt.value is not None else []
    return []


def parts(expr):
    """The parts of an expression that are evaluated before it, in order."""
    if isinstance(expr, BinOpNode):
        return [expr.left, expr.right]
    if isinstance(expr, (CallNode, MemberCallNode)):
        return list(expr.args)            # a member call's object is an address, not a value
    if isinstance(expr, LiteralNode):
        return list(expr.values)
    return []


def quiet(expr):
    """Can evaluating `expr` neither be observed nor fail? A call, finna_hear() and
    arithmetic the compiler could not fold are not quiet."""
    if isinstance(expr, (IntNode, BoolNode, VarNode, FieldNode)):
        return True
    if isinstance(expr, LiteralNode):
        return all(quiet(value) for value in expr.values)
    if isinstance(expr, BinOpNode):
        if expr.const is not None:        # folded: one number in the IR, nothing to fail
            return True
        return expr.symbol in COMPARISONS and quiet(expr.left) and quiet(expr.right)
    return False


def has(node, kind):
    return any(isinstance(n, kind) for n in walk(node))


# -- unused variables ---------------------------------------------------------

def remove_unused_variables(program):
    """One round: drop every declaration nobody reads whose value and posts are quiet,
    with its posts. Returns whether anything was removed."""
    reads, posts = {}, {}
    for node in walk(program):
        if isinstance(node, (VarNode, FieldNode)):
            reads[id(node.decl)] = reads.get(id(node.decl), 0) + 1
        elif isinstance(node, AssignNode):
            posts.setdefault(id(node.decl), []).append(node)
    dead = set()
    for stmts, _ in statement_lists(program):
        for stmt in stmts:
            if isinstance(stmt, DeclNode) and id(stmt) not in reads and quiet(stmt.init) \
                    and all(quiet(post.value) for post in posts.get(id(stmt), [])):
                dead.add(id(stmt))
    if not dead:
        return False
    for stmts, _ in statement_lists(program):
        stmts[:] = [stmt for stmt in stmts
                    if not (isinstance(stmt, (DeclNode, AssignNode)) and id(stmt_decl(stmt)) in dead)]
    return True


def stmt_decl(stmt):
    """The declaration a DeclNode is, or an AssignNode writes."""
    return stmt if isinstance(stmt, DeclNode) else stmt.decl


# -- unused functions ---------------------------------------------------------

def calls_in(node):
    """The FunctionNodes called under `node`, once per call."""
    return [n.fn for n in walk(node) if isinstance(n, (CallNode, MemberCallNode))]


def call_counts(program):
    """id(function) -> how many calls of it stand outside its own body."""
    counts = {}
    owners = [(None, [item for item in program.items if not isinstance(item, (FunctionNode, SquadNode))])]
    owners += [(fn, fn.body) for fn, _ in functions(program)]
    for owner, body in owners:
        for stmt in body:
            for fn in calls_in(stmt):
                if fn is not owner:
                    counts[id(fn)] = counts.get(id(fn), 0) + 1
    return counts


def remove_unused_functions(program):
    """One round: drop every drill and member function with no call outside its body."""
    counts = call_counts(program)
    dead = [(fn, holder) for fn, holder in functions(program) if id(fn) not in counts]
    for fn, holder in dead:
        holder.remove(fn)
    return bool(dead)


# -- inlining -------------------------------------------------------------------

def recursive(fn):
    """Can `fn` reach itself through the calls in its body, directly or through others?"""
    seen, todo = set(), calls_in_body(fn)
    while todo:
        callee = todo.pop()
        if callee is fn:
            return True
        if id(callee) not in seen:
            seen.add(id(callee))
            todo.extend(calls_in_body(callee))
    return False


def calls_in_body(fn):
    return [callee for stmt in fn.body for callee in calls_in(stmt)]


def tail_form(stmts):
    """The statements with every cuh moved to the end of its path, or None when the shape
    is one that is left alone. Builds new spot nodes; never changes the ones given."""
    out = []
    for index, stmt in enumerate(stmts):
        if isinstance(stmt, (ReturnNode, ExitNode)):
            out.append(stmt)
            return out                    # what follows can never run
        if isinstance(stmt, (WhileNode, ForNode)) and has(stmt, ReturnNode):
            return None                   # leaving a loop in the middle: left alone
        if isinstance(stmt, IfNode) and has(stmt, ReturnNode):
            rest = stmts[index + 1:]
            then_body, else_body = stmt.then_body, stmt.else_body or []
            then_leaves = leaves(then_body)
            else_leaves = stmt.else_body is not None and leaves(else_body)
            if then_leaves and else_leaves:
                arms = tail_form(then_body), tail_form(else_body)
            elif then_leaves and not any(has(s, ReturnNode) for s in else_body):
                arms = tail_form(then_body), tail_form(else_body + rest)
            elif else_leaves and not any(has(s, ReturnNode) for s in then_body):
                arms = tail_form(then_body + rest), tail_form(else_body)
            else:
                return None               # the rest would have to go into both arms
            if None in arms:
                return None
            node = copy.copy(stmt)
            node.then_body, node.else_body = arms[0], arms[1] or None
            out.append(node)
            return out                    # the rest went into an arm
        out.append(stmt)
    return out


def default(type_name, squads, at):
    """A value of `type_name` to start a sliding result with: 0, woof, or a literal of those."""
    if type_name in ("doze", "fawty"):
        node = IntNode(at.line, at.col, 0)
        node.const = 0
    elif type_name == "line":
        node = BoolNode(at.line, at.col, False)
        node.const = None
    else:
        squad = squads[type_name]
        node = LiteralNode(at.line, at.col, type_name,
                           [default(field.type_name, squads, at) for field in squad.fields])
        node.const, node.squad = None, squad
    node.type = type_name
    return node


def declaration(name, type_name, mutable, init, at):
    node = DeclNode(at.line, at.col, name, type_name, mutable, init)
    node.const = None
    return node


def read_of(decl, at):
    node = VarNode(at.line, at.col, decl.name)
    node.decl, node.indices, node.type, node.const = decl, [], decl.type_name, None
    return node


def post_to(decl, value, at):
    node = AssignNode(at.line, at.col, decl.name, value)
    node.decl, node.indices, node.target_type = decl, [], decl.type_name
    return node


def evaluated_before(stmt, call):
    """The parts of `stmt` evaluated before `call`, outside it -- or None when `call` is
    not among the values `stmt` evaluates itself."""
    before = []

    def visit(expr):                      # True once `call` is reached
        if expr is call:
            return True
        for part in parts(expr):
            if visit(part):
                return True
        before.append(expr)               # an operation runs after its parts
        return False

    for value in own_values(stmt):
        if visit(value):
            return before
    return None


def hoistable(stmt, call):
    """May `call` be evaluated, with its arguments, before the rest of `stmt`?"""
    if isinstance(stmt, WhileNode):
        return False                      # its condition runs before every round
    before = evaluated_before(stmt, call)
    if before is None or not all(quiet(expr) for expr in before):
        return False
    if any(has(arg, MemberCallNode) for arg in call.args):   # it may change an object read before
        return not any(isinstance(n, (VarNode, FieldNode)) for expr in before for n in walk(expr))
    return True


def find_call(program, fn):
    """The one call of `fn`: (the list, the index of its statement, the statement, the call)."""
    for stmts, _ in statement_lists(program):
        for index, stmt in enumerate(stmts):
            for value in own_values(stmt):
                for node in walk(value):
                    if isinstance(node, CallNode) and node.fn is fn:
                        return stmts, index, stmt, node
    return None


def replace(stmt, old, new):
    """Put `new` where the expression `old` stands among the values of `stmt`."""
    def swap(expr):
        if expr is old:
            return new
        if isinstance(expr, BinOpNode):
            expr.left, expr.right = swap(expr.left), swap(expr.right)
        elif isinstance(expr, (CallNode, MemberCallNode)):
            expr.args = [swap(arg) for arg in expr.args]
        elif isinstance(expr, LiteralNode):
            expr.values = [swap(value) for value in expr.values]
        return expr

    for attr in ("init", "value", "call", "cond", "start", "end"):
        if getattr(stmt, attr, None) is not None:
            setattr(stmt, attr, swap(getattr(stmt, attr)))


def rename(body, prefix, extra):
    """f$name for every name the body declares -- and the parameters' new declarations in
    `extra` -- and for every use of them."""
    renamed = {}
    for stmt in body:
        for node in walk(stmt):
            if isinstance(node, DeclNode):
                renamed[id(node)] = node
            elif isinstance(node, ForNode):
                renamed[id(node.counter)] = node.counter
    for decl in renamed.values():
        decl.name = f"{prefix}${decl.name}"
    renamed.update((id(decl), decl) for decl in extra)
    for stmt in body:
        for node in walk(stmt):
            if isinstance(node, (VarNode, FieldNode, AssignNode)) and id(node.decl) in renamed:
                node.name = node.decl.name


def retarget(body, params):
    """A use of a parameter now means the declaration that took its place."""
    for stmt in body:
        for node in walk(stmt):
            if isinstance(node, (VarNode, FieldNode, AssignNode)) and isinstance(node.decl, ParamNode) \
                    and id(node.decl) in params:
                node.decl = params[id(node.decl)]
                node.name = node.decl.name


def returns_to_posts(stmts, result):
    """Every cuh -- the last statement of its path, in tail form -- becomes a post to the
    result, or nothing in a drill that returns nothing."""
    out = []
    for stmt in stmts:
        if isinstance(stmt, ReturnNode):
            if stmt.value is not None:
                out.append(post_to(result, stmt.value, stmt))
            continue
        if isinstance(stmt, IfNode):
            stmt.then_body = returns_to_posts(stmt.then_body, result)
            if stmt.else_body is not None:
                stmt.else_body = returns_to_posts(stmt.else_body, result)
        out.append(stmt)
    return out


def inline_one(program):
    """Inline one drill called exactly once, if there is one. Returns whether it did."""
    squads = {item.name: item for item in program.items if isinstance(item, SquadNode)}
    counts = {}
    for node in walk(program):
        if isinstance(node, (CallNode, MemberCallNode)):
            counts[id(node.fn)] = counts.get(id(node.fn), 0) + 1
    for fn in [item for item in program.items if isinstance(item, FunctionNode)]:
        if counts.get(id(fn)) != 1 or recursive(fn):
            continue
        site = find_call(program, fn)
        if site is None:
            continue
        stmts, index, stmt, call = site
        body = tail_form(fn.body)
        if body is None or not hoistable(stmt, call):
            continue
        inline(fn, body, stmts, index, stmt, call, squads)
        return True
    return False


def inline(fn, body, stmts, index, stmt, call, squads):
    params = {id(param): declaration(f"{fn.name}${param.name}", param.type_name, False, arg, call)
              for param, arg in zip(fn.params, call.args)}
    retarget(body, params)
    rename(body, fn.name, params.values())
    code = list(params.values())

    result = None
    if fn.return_type is not None:
        name = f"{fn.name}$result"
        last = body[-1] if body else None
        simple = isinstance(last, ReturnNode) and not any(has(s, ReturnNode) for s in body[:-1])
        if simple:                        # cuh at the end and nowhere else
            result = declaration(name, fn.return_type, False, last.value, last)
            body = [*body[:-1], result]
        else:                             # early exits: every cuh posts to a sliding result
            result = declaration(name, fn.return_type, True, default(fn.return_type, squads, call), call)
            code.append(result)
            body = returns_to_posts(body, result)
    else:
        body = returns_to_posts(body, None)
    code.extend(body)

    if isinstance(stmt, CallStmtNode) and stmt.call is call:
        stmts[index:index + 1] = code     # the call was a statement of its own
    else:
        replace(stmt, call, read_of(result, call))
        stmts[index:index] = code


# -- the pass -----------------------------------------------------------------

def optimize(program):
    """Run the three transformations until a round changes nothing; return the tree."""
    changed = True
    while changed:
        changed = remove_unused_functions(program)
        changed = remove_unused_variables(program) or changed
        changed = inline_one(program) or changed
    return program

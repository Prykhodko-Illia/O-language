"""Phase 3: a walk over the checked AST that emits the IR

Nothing calls the builder until the whole tree stands and the semantic pass has approved
it; then this visitor walks it. One method per node kind: statement nodes return
nothing, expression nodes return the value the builder produced for them, so an
operation asks its children for their values first and then emits its own instruction --
operands before the operation, bottom-up. The only IR text the compiler ever writes is
str(module), the module this builder filled.

There are no checks here. Declared before use, declared once, sliding before a second
post and every type rule live in src/semantic.py, which ran first; this walk trusts the
tree and reads the fields that pass left on it: `node.type` and `node.const` on
expressions, `node.decl` on names, `node.fn` on calls.

Types are explicit in the IR: a doze is an i32, a fawty an i64, a line an i1. Every value
is asked for through value(expr, want), which hands back exactly a `want`:
  * a constant -- `node.const`, computed exactly by the semantic pass -- is one
    ir.Constant of the type it lands in, never an addition that could overflow on the
    way: fawty big post 2147483647 bump 1 stores the number 2147483648;
  * anything else is emitted, and the one implicit conversion of the language -- a doze
    where a fawty is expected -- becomes an explicit sext.

Every operation that can go wrong at run time is checked where it happens. bump, tuck_in
and double_back use the overflow intrinsics (llvm.sadd/ssub/smul.with.overflow), which
give the result and a flag; breakdown and scraps compare the divisor with 0, and
breakdown also catches MIN breakdown -1, the one quotient that does not fit. A failed
check -- or an on_the_guys whose condition is woof -- branches to a block of its own that
prints one line, `line L:C: ...`, and calls exit(1). The checks are what make a doze a
doze: without them a sum just wraps around, and sdiv by zero kills the process.

A block of the source is not a basic block of the IR. A source block is a scope, and the
semantic pass already resolved every name in it; here it is only a run of statements. A
basic block is a builder position: spot appends then, pivot (when there is one) and
merge blocks to the function, ends the current block with a cbranch on the i1 of the
condition, and moves the builder from one to the next. Every basic block ends with
exactly one terminator -- br, ret, or the unreachable after a call of exit -- and nothing
after it. Statements written after a cuh or a scat in the same block are legal and never
run: they go into a fresh block that nothing branches to.

A squad is an identified struct type, %"squad.Point" = type {i32, i32}, and an object is
one alloca of it. A field is reached with a gep: index 0 steps through the pointer to the
object itself, then one index per link of the chain, so c.center.x is one gep with indices
0, 0, 0. The indices come from the semantic pass; nothing here looks a field up by name.
A literal Point{3, 4} is not an object in memory but one value of the struct type, built
in registers: it starts as undef and each field goes in with insertvalue, by index. A
whole object moves as one value -- a load of %"squad.Point" and a store of it -- which is
how Point q post p copies, and how a squad goes into a parameter and out of a drill.

Every drill becomes a function of the module named @"drill.NAME": a name of the program
cannot hold a '.', so drill main or drill printf never meets the runtime's main and
printf. All of them are declared before any body is built, so a call can name a drill
whose body does not exist yet (itself, or one below). Each has its own entry block; its
parameters are stored into slots there, like declarations, so a body reads a parameter
with a load like any variable. The top-level statements are main, which returns 0 when
it reaches its end.

air_out is printf with a format by type -- "%d\\n" for a doze, "%lld\\n" for a fawty, and
"%s\\n" both for a line (a select between the global strings "true" and "false") and for
a string, whose text goes in as the argument so a % in it stays a %. scat prints
"Program exit with result ..." with the same formats and calls exit(0), wherever it
stands -- in a drill too; scat with no value just calls exit(0). Every format and text is
a private global constant, one per distinct text.

Every alloca goes to the entry block, wherever the builder is when the declaration is met:
a slot made inside spot would not exist on the pivot path, and LLVM promotes only
entry-block allocas to registers (opt -passes=mem2reg).
"""

from llvmlite import ir
import llvmlite.binding as llvm

from .ast_nodes import FunctionNode, SquadNode, StringNode, chain

I1, I8, I32, I64 = ir.IntType(1), ir.IntType(8), ir.IntType(32), ir.IntType(64)

LLVM_TYPE = {"doze": I32, "fawty": I64, "line": I1}   # the squads join them per module

FORMAT = {"doze": b"%d", "fawty": b"%lld", "line": b"%s"}

I8_PTR = ir.PointerType(I8)

FN_PREFIX = "drill."              # drill main becomes @"drill.main", not a second @main

CHECKED = {"+": "sadd_with_overflow", "-": "ssub_with_overflow", "*": "smul_with_overflow"}


class CodeGen:
    """Builds a module from a checked ProgramNode: one function per drill, and main."""

    def __init__(self):
        # A context of our own: named struct types live in the context, and the global one
        # would keep a %"squad.Point" from an earlier module in the same process.
        self.context = ir.Context()
        self.module = ir.Module(name="o_language", context=self.context)
        self.module.triple = llvm.get_default_triple()
        self.types = dict(LLVM_TYPE)      # type name -> LLVM type: built-ins, then each squad

        # The function being built. begin_function() sets these; each function has its
        # own entry block and its own run of allocas at its top.
        self.function = self.entry = self.builder = None
        self.last_slot = None      # the last alloca in entry: the next one goes after it
        self.current_fn = None     # the FunctionNode being built, or None for main

        self.fns = {}              # FunctionNode -> its ir.Function, every one before any body

        # Keyed by the declaration, not by the name: two variables in different blocks may
        # share a name, and the tree already says which one is meant.
        self.slots = {}            # DeclNode | ParamNode -> the alloca holding it

        c_type = ir.FunctionType(I32, [I8_PTR], var_arg=True)   # int f(const char *fmt, ...)
        self.printf = ir.Function(self.module, c_type, name="printf")
        self.exit = ir.Function(self.module, ir.FunctionType(ir.VoidType(), [I32]), name="exit")
        self.texts = {}            # bytes -> the global constant holding them and a NUL

    def run(self, program):
        program.accept(self)
        return self.module

    # -- helpers ------------------------------------------------------------

    def text(self, data):
        """An i8* to the global constant holding `data` and a NUL: one global per distinct
        text, however many prints use it."""
        if data not in self.texts:
            data_z = data + b"\0"
            array = ir.ArrayType(I8, len(data_z))
            variable = ir.GlobalVariable(self.module, array, name=self.module.get_unique_name("str"))
            variable.linkage, variable.global_constant = "private", True
            variable.initializer = ir.Constant(array, bytearray(data_z))
            self.texts[data] = variable
        return self.builder.bitcast(self.texts[data], I8_PTR)

    def printf_call(self, fmt, *values):
        self.builder.call(self.printf, [self.text(fmt), *values])

    def word(self, value):
        """The word for an i1: a select between the global strings "true" and "false"."""
        return self.builder.select(value, self.text(b"true"), self.text(b"false"), name="word")

    def printable(self, value, type_name):
        """A value as printf takes it under FORMAT[type_name]."""
        return self.word(value) if type_name == "line" else value

    def end_program(self, code):
        """exit(code): the C library flushes what printf buffered, and nothing follows."""
        self.builder.call(self.exit, [ir.Constant(I32, code)])
        self.builder.unreachable()

    def trap_if(self, failed, node, message):
        """When the i1 `failed` is set, print `line L:C: message` and exit(1); else go on."""
        trap_bb = self.function.append_basic_block("trap")
        ok_bb = self.function.append_basic_block("ok")
        self.builder.cbranch(failed, trap_bb, ok_bb)
        self.builder.position_at_end(trap_bb)
        self.printf_call(f"line {node.line}:{node.col}: {message}\n".encode())
        self.end_program(1)
        self.builder.position_at_end(ok_bb)

    def begin_function(self, function, fn_node):
        """Point the builder at a fresh function: its own entry block, its own slots."""
        self.function, self.current_fn = function, fn_node
        self.entry = function.append_basic_block("entry")
        self.builder = ir.IRBuilder(self.entry)
        self.last_slot = None

    def alloca_in_entry(self, llvm_type, name):
        """A slot at the top of the entry block, then back to where we were."""
        here = self.builder.block
        if self.last_slot is None:
            self.builder.position_at_start(self.entry)
        else:
            self.builder.position_after(self.last_slot)          # declaration order
        self.last_slot = self.builder.alloca(llvm_type, name=name)
        self.builder.position_at_end(here)
        return self.last_slot

    def value(self, expr, want):
        """The value of `expr` as exactly a `want`: a constant is one number of that type,
        anything else is emitted and, from a doze into a fawty, widened with sext."""
        if expr.const is not None:
            return ir.Constant(LLVM_TYPE[want], expr.const)
        result = expr.accept(self)
        if expr.type == "doze" and want == "fawty":
            return self.builder.sext(result, I64, name="wide")
        return result

    def gep(self, ptr, indices, name):
        """A pointer to a field: 0 to step through `ptr`, then one index per link."""
        return self.builder.gep(ptr, [ir.Constant(I32, i) for i in (0, *indices)], name=name)

    def statements(self, body):
        for stmt in body:
            if self.builder.block.is_terminated:                 # after a cuh or a scat:
                self.builder.position_at_end(self.function.append_basic_block("dead"))
            stmt.accept(self)

    # -- the program and the drills -----------------------------------------

    def visit_program(self, node):
        for item in node.items:                                  # the types, in program order:
            if isinstance(item, SquadNode):                      # a field's squad is above it
                item.accept(self)
        functions = [item for item in node.items if isinstance(item, FunctionNode)]
        for fn in functions:                                     # every signature first...
            result = self.types[fn.return_type] if fn.return_type else ir.VoidType()
            fn_type = ir.FunctionType(result, [self.types[p.type_name] for p in fn.params])
            self.fns[fn] = ir.Function(self.module, fn_type, name=FN_PREFIX + fn.name)
        for fn in functions:                                     # ...then the bodies
            fn.accept(self)

        main = ir.Function(self.module, ir.FunctionType(I32, []), name="main")
        self.begin_function(main, None)
        self.statements([item for item in node.items if not isinstance(item, (FunctionNode, SquadNode))])
        if not self.builder.block.is_terminated:                 # the end of the program
            self.builder.ret(ir.Constant(I32, 0))

    def visit_function(self, node):
        function = self.fns[node]
        self.begin_function(function, node)
        for param, arg in zip(node.params, function.args):      # a parameter is a copy in a slot
            arg.name = param.name
            self.slots[param] = self.alloca_in_entry(self.types[param.type_name], param.name)
            self.builder.store(arg, self.slots[param])
        self.statements(node.body)
        if not self.builder.block.is_terminated:
            if node.return_type is None:
                self.builder.ret_void()                          # a drill may just end
            else:
                self.builder.unreachable()                       # the semantic pass: every path left

    def visit_squad(self, node):
        struct_type = self.context.get_identified_type(f"squad.{node.name}")
        # Every field type is built in or a squad above, so it is already in self.types.
        struct_type.set_body(*(self.types[field.type_name] for field in node.fields))
        self.types[node.name] = struct_type

    # -- statements: emit IR, return nothing --------------------------------

    def visit_decl(self, node):
        slot = self.alloca_in_entry(self.types[node.type_name], node.name)
        self.slots[node] = slot
        self.builder.store(self.value(node.init, node.type_name), slot)   # a whole object is one store too

    def visit_assign(self, node):
        ptr = self.slots[node.decl]
        if node.indices:                                         # c.center.x post ...
            ptr = self.gep(ptr, node.indices, name=chain(node.name, node.links))
        self.builder.store(self.value(node.value, node.target_type), ptr)

    def visit_call_stmt(self, node):
        node.call.accept(self)

    def visit_if(self, node):
        cond = self.value(node.cond, "line")                     # an i1, in the current block
        then_bb = self.function.append_basic_block("then")
        else_bb = self.function.append_basic_block("else") if node.else_body is not None else None
        merge_bb = self.function.append_basic_block("merge")
        self.builder.cbranch(cond, then_bb, else_bb or merge_bb) # ends the current block

        for body, arm_bb in ((node.then_body, then_bb), (node.else_body, else_bb)):
            if body is None:
                continue
            self.builder.position_at_end(arm_bb)
            self.statements(body)
            # The block the arm ended in, not arm_bb: a nested spot moved the builder to its
            # own merge. An arm that left already has its terminator.
            if not self.builder.block.is_terminated:
                self.builder.branch(merge_bb)

        # What follows the spot goes here. When both arms leave, merge has no predecessor;
        # it still gets the statements after the spot and stays valid.
        self.builder.position_at_end(merge_bb)

    def visit_return(self, node):
        if node.value is None:
            self.builder.ret_void()
        else:
            self.builder.ret(self.value(node.value, self.current_fn.return_type))

    def visit_exit(self, node):
        value = node.value
        if value is not None:                                    # print, and end the program
            fmt = b"Program exit with result " + FORMAT[value.type] + b"\n"
            self.printf_call(fmt, self.printable(self.value(value, value.type), value.type))
        self.end_program(0)

    def visit_assert(self, node):
        cond = self.value(node.cond, "line")
        self.trap_if(self.builder.not_(cond, name="broken"), node, "you said on_the_guys, but it was cap")

    def visit_print(self, node):
        value = node.value
        if isinstance(value, StringNode):                        # its text as written: a % stays a %
            self.printf_call(b"%s\n", self.text(value.value.encode()))
            return
        self.printf_call(FORMAT[value.type] + b"\n", self.printable(self.value(value, value.type), value.type))

    # -- expressions: return the value the builder produced -----------------

    def visit_binop(self, node):
        if node.symbol in ("==", "!="):
            left, right = node.left.type, node.right.type
            width = "line" if left == "line" else ("fawty" if "fawty" in (left, right) else "doze")
            lhs, rhs = self.value(node.left, width), self.value(node.right, width)
            return self.builder.icmp_signed(node.symbol, lhs, rhs, name="cmp")

        # both operands in the result type: add i32 %a, i64 %b does not exist
        lhs, rhs = self.value(node.left, node.type), self.value(node.right, node.type)
        llvm_type = LLVM_TYPE[node.type]
        if node.symbol in CHECKED:
            pair = getattr(self.builder, CHECKED[node.symbol])(lhs, rhs, name=node.op)
            failed = self.builder.extract_value(pair, 1, name="overflow")
            self.trap_if(failed, node, f"{node.type} overflow in '{node.op}', the bag is too big for {node.type}")
            return self.builder.extract_value(pair, 0, name=node.op)

        zero = ir.Constant(llvm_type, 0)
        minus_one = ir.Constant(llvm_type, -1)
        self.trap_if(self.builder.icmp_signed("==", rhs, zero, name="by_zero"), node,
                     f"'{node.op}' by 0, you can't split it with nobody")
        if node.symbol == "/":                                   # MIN / -1 is MAX + 1
            low = ir.Constant(llvm_type, -2 ** (llvm_type.width - 1))
            failed = self.builder.and_(self.builder.icmp_signed("==", lhs, low),
                                       self.builder.icmp_signed("==", rhs, minus_one), name="too_big")
            self.trap_if(failed, node, f"{node.type} overflow in '{node.op}', the bag is too big for {node.type}")
            return self.builder.sdiv(lhs, rhs, name=node.op)
        # MIN % -1 is 0, but srem traps on it like sdiv: x % -1 and x % 1 are both 0
        is_minus_one = self.builder.icmp_signed("==", rhs, minus_one)
        rhs = self.builder.select(is_minus_one, ir.Constant(llvm_type, 1), rhs)
        return self.builder.srem(lhs, rhs, name=node.op)

    def visit_call(self, node):
        args = [self.value(arg, param.type_name)                 # a doze into a fawty parameter
                for param, arg in zip(node.fn.params, node.args)]
        return self.builder.call(self.fns[node.fn], args)

    def visit_var(self, node):
        return self.builder.load(self.slots[node.decl], name=node.name)

    def visit_field(self, node):
        name = chain(node.name, node.links)
        return self.builder.load(self.gep(self.slots[node.decl], node.indices, name=name), name=name)

    def visit_literal(self, node):
        value = ir.Constant(self.types[node.type], ir.Undefined)   # nothing in it yet
        for index, part in enumerate(node.values):               # field by field, by index
            field_type = node.squad.fields[index].type_name
            value = self.builder.insert_value(value, self.value(part, field_type), index)
        return value

    def visit_int(self, node):
        return ir.Constant(LLVM_TYPE[node.type], node.value)    # reached only through value(): a constant

    def visit_bool(self, node):
        return ir.Constant(I1, 1 if node.value else 0)


def codegen(program):
    return CodeGen().run(program)

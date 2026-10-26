"""The abstract syntax tree.

The grammar dictates the classes: where a rule says "either / or" there is an abstract
base with one subclass per alternative, and where it says "this, then that" there is a
class whose fields are the parts that carry information. Keywords disappear or become
flags -- `sliding` is a boolean, the braces, `post` and `no_bap` leave
nothing behind, and an operator keeps both its word and the symbol it stands for.

    ASTNode
    +-- ProgramNode        items: [FunctionNode | StmtNode]
    +-- FunctionNode       name, params: [ParamNode], return_type (or None), body: [StmtNode]
    +-- ParamNode          name, type_name
    +-- StmtNode     (abstract)
    |   +-- DeclNode       name, type_name, mutable, init: ExprNode
    |   +-- AssignNode     name, value: ExprNode
    |   +-- CallStmtNode   call: CallNode
    |   +-- IfNode         cond: ExprNode, then_body: [StmtNode], else_body: [StmtNode] or None
    |   +-- ReturnNode     value: ExprNode or None
    |   +-- ExitNode       value: ExprNode or None
    |   +-- AssertNode     cond: ExprNode
    |   +-- PrintNode      value: StringNode | ExprNode
    +-- ExprNode     (abstract)
        +-- BinOpNode      op (the word), symbol ('+', '-', '*', '/', '%', '==', '!='), left, right
        +-- CallNode       name, args: [ExprNode]
        +-- VarNode        name
        +-- IntNode        value
        +-- BoolNode       value (True / False)
        +-- StringNode     value   (only as the argument of air_out)

Every node keeps the line and column of the token it came from, so the later stages
can point at an error without having any tokens left. The tree holds names, numbers,
flags and child nodes: never a token.

(Not named ast.py: that would shadow the standard library's `ast` module.)
"""


class ASTNode:
    def __init__(self, line, col):
        self.line = line
        self.col = col

    def label(self):
        """This node as one line of text, without its children."""
        raise NotImplementedError

    def children(self):
        return []

    def dump(self, depth=0):
        """The tree as text, one node per line, children indented by two spaces."""
        out = "  " * depth + self.label() + "\n"
        for child in self.children():
            out += child.dump(depth + 1)
        return out


class Group(ASTNode):
    """A labelled list of children in the dump (Then / Else / Body / Args) -- not a
    node of the language, only a heading that keeps the dump readable."""

    def __init__(self, title, nodes):
        super().__init__(0, 0)
        self.title = title
        self.nodes = nodes

    def label(self):
        return self.title

    def children(self):
        return self.nodes


class StmtNode(ASTNode):
    """A statement: it does something and produces no value."""

    inverted = False                      # written back to front, on a pab_on line

    def dump(self, depth=0):
        out = super().dump(depth)
        if self.inverted:                 # mark the first line of this node
            head, rest = out.split("\n", 1)
            out = head + " (inverted)\n" + rest
        return out


class ExprNode(ASTNode):
    """An expression: it produces a value."""


class ProgramNode(ASTNode):
    def __init__(self, line, col, items):
        super().__init__(line, col)
        self.items = items                # [FunctionNode | StmtNode]

    def label(self):
        return "Program"

    def children(self):
        return self.items


class FunctionNode(ASTNode):
    def __init__(self, line, col, name, params, return_type, body):
        super().__init__(line, col)       # position of the name
        self.name = name
        self.params = params              # [ParamNode]
        self.return_type = return_type    # "doze" | "fawty" | "line" | None
        self.body = body                  # [StmtNode], at least one

    def label(self):
        return f"Function {self.name} returns {self.return_type or 'nothing'}"

    def children(self):
        return [*self.params, Group("Body", self.body)]


class ParamNode(ASTNode):
    def __init__(self, line, col, name, type_name):
        super().__init__(line, col)
        self.name = name
        self.type_name = type_name

    def label(self):
        return f"Param {self.name} {self.type_name}"


class DeclNode(StmtNode):
    def __init__(self, line, col, name, type_name, mutable, init):
        super().__init__(line, col)       # position of the name
        self.name = name
        self.type_name = type_name        # "doze" | "fawty" | "line"
        self.mutable = mutable
        self.init = init                  # ExprNode

    def label(self):
        return f"Decl {self.name} {self.type_name} {'sliding' if self.mutable else 'tucked'}"

    def children(self):
        return [self.init]


class AssignNode(StmtNode):
    def __init__(self, line, col, name, value):
        super().__init__(line, col)       # position of the name
        self.name = name
        self.value = value

    def label(self):
        return f"Assign {self.name}"

    def children(self):
        return [self.value]


class CallStmtNode(StmtNode):
    def __init__(self, line, col, call):
        super().__init__(line, col)
        self.call = call                  # CallNode

    def label(self):
        return "CallStmt"

    def children(self):
        return [self.call]


class IfNode(StmtNode):
    def __init__(self, line, col, cond, then_body, else_body):
        super().__init__(line, col)       # position of 'spot'
        self.cond = cond
        self.then_body = then_body        # [StmtNode], at least one
        self.else_body = else_body        # [StmtNode], at least one, or None

    def label(self):
        return "If" if self.else_body is None else "If with pivot"

    def children(self):
        out = [Group("Cond", [self.cond]), Group("Then", self.then_body)]
        if self.else_body is not None:
            out.append(Group("Else", self.else_body))
        return out


class ReturnNode(StmtNode):
    def __init__(self, line, col, value):
        super().__init__(line, col)       # position of 'cuh'
        self.value = value                # ExprNode | None

    def label(self):
        return "Return" if self.value is not None else "Return nothing"

    def children(self):
        return [self.value] if self.value is not None else []


class ExitNode(StmtNode):
    def __init__(self, line, col, value):
        super().__init__(line, col)       # position of 'scat'
        self.value = value                # ExprNode | None

    def label(self):
        return "Exit" if self.value is not None else "Exit nothing"

    def children(self):
        return [self.value] if self.value is not None else []


class AssertNode(StmtNode):
    def __init__(self, line, col, cond):
        super().__init__(line, col)       # position of 'on_the_guys'
        self.cond = cond

    def label(self):
        return "Assert"

    def children(self):
        return [self.cond]


class PrintNode(StmtNode):
    def __init__(self, line, col, value):
        super().__init__(line, col)       # position of 'air_out'
        self.value = value                # StringNode | ExprNode

    def label(self):
        return "Print"

    def children(self):
        return [self.value]


SYMBOLS = {
    "bump": "+", "tuck_in": "-", "double_back": "*", "breakdown": "/", "scraps": "%",
    "in_tune": "==", "fugazi": "!=",
}


class BinOpNode(ExprNode):
    def __init__(self, line, col, op, left, right):
        super().__init__(line, col)       # position of the operator
        self.op = op                      # the word: bump, tuck_in, ...
        self.symbol = SYMBOLS[op]         # what it means: +, -, ...
        self.left = left
        self.right = right

    def label(self):
        return f"BinOp {self.op} ({self.symbol})"

    def children(self):
        return [self.left, self.right]


class CallNode(ExprNode):
    def __init__(self, line, col, name, args):
        super().__init__(line, col)       # position of the name
        self.name = name
        self.args = args                  # [ExprNode]

    def label(self):
        return f"Call {self.name} ({len(self.args)} args)"

    def children(self):
        return self.args


class VarNode(ExprNode):
    def __init__(self, line, col, name):
        super().__init__(line, col)
        self.name = name

    def label(self):
        return f"Var {self.name}"


class IntNode(ExprNode):
    def __init__(self, line, col, value):
        super().__init__(line, col)
        self.value = value

    def label(self):
        return f"Int {self.value}"


class BoolNode(ExprNode):
    def __init__(self, line, col, value):
        super().__init__(line, col)
        self.value = value                # True | False

    def label(self):
        return f"Bool {'merch' if self.value else 'woof'}"


class StringNode(ExprNode):
    def __init__(self, line, col, value):
        super().__init__(line, col)
        self.value = value

    def label(self):
        return f'String "{self.value}"'

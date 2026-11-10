"""Phase 1: tokens -> AST  (syntax errors only)

Recursive descent, written by hand: one method per rule of grammar.ebnf.

  program   ::= { item }
  item      ::= squad | function | statement
  squad     ::= "squad" ident "{" field { field } { function } "}"
  field     ::= [ "sliding" ] type ident "no_bap"
  function  ::= [ type ] "drill" ident "(" [ param { "," param } ] ")" block
  param     ::= type ident
  block     ::= "{" statement { statement } "}"
  statement ::= decl | assign | call_stmt | if | return | exit | assert | print | inverted
  decl      ::= [ "sliding" ] type ident "post" expr "no_bap"
  type      ::= "doze" | "fawty" | "line" | squad_name
  assign    ::= place "post" expr "no_bap"
  place     ::= ident { "." ident }
  call_stmt ::= place args "no_bap"
  if        ::= "spot" expr block [ "pivot" block ]
  return    ::= "cuh" [ expr ] "no_bap"
  exit      ::= "scat" [ expr ] "no_bap"
  assert    ::= "on_the_guys" "(" expr ")" "no_bap"
  print     ::= "air_out" "(" ( string | expr ) ")" "no_bap"
  inverted  ::= "pab_on" expr ( "post" place [ type [ "sliding" ] ] | "cuh" | "scat" ) eol
  expr      ::= arith [ ( "in_tune" | "fugazi" ) arith ]
  arith     ::= term { ( "bump" | "tuck_in" ) term }
  term      ::= factor { ( "double_back" | "breakdown" | "scraps" ) factor }
  factor    ::= number | "merch" | "woof" | read | literal | place [ args ] | "(" expr ")"
  literal   ::= squad_name "{" expr { "," expr } "}"
  read      ::= "finna_hear" "(" ")"
  args      ::= "(" [ expr { "," expr } ] ")"

peek() returns the current token, eat() returns it and moves on. One token of
look-ahead decides every choice. Two pairs of rules share their first token, and in
both the parser eats that token first and then decides by the one after it, so it
still never looks more than one token ahead:
  - a type starts both a function (`doze drill f(...)`) and a declaration (`doze x post 1`),
    and inside a squad both a member function and a field;
  - a place starts both an assignment (`c.r post ...`) and a call (`f(...)`, `c.grow(...)`).

A place with args is a call: parse_call when it has no '.' (a CallNode, of a drill or of
a member function on the same object), parse_member_call when it has one.

A squad's name is an identifier, so the parser keeps the names of the squads declared so
far: an identifier among them is a type -- `Point p post ...` is a declaration, and
`Point{3, 4}` is a literal -- and any other identifier is a variable or a drill. That is
what keeps `spot flag { ... }` a condition and a block: flag is not a squad. A squad is
declared above every use of its name, so the set is always complete when it is needed.
"""

from .ast_nodes import (AssertNode, AssignNode, BinOpNode, BoolNode, CallNode,
                        CallStmtNode, DeclNode, ExitNode, FieldDeclNode, FieldNode,
                        FunctionNode, IfNode, IntNode, Link, LiteralNode,
                        MemberCallNode, ParamNode, ReadNode,
                        PrintNode, ProgramNode, ReturnNode, SquadNode, StringNode,
                        VarNode)
from .errors import CompileError


RANGES = {
    "doze": (-2 ** 31, 2 ** 31 - 1),
    "fawty": (-2 ** 63, 2 ** 63 - 1),
}


def constant_value(node):
    """The value of an expression made only of numbers and arithmetic, or None."""
    if isinstance(node, IntNode):
        return node.value
    if isinstance(node, BinOpNode) and node.symbol in "+-*/%":
        left, right = constant_value(node.left), constant_value(node.right)
        if left is None or right is None:
            return None
        if node.symbol in "/%" and right == 0:
            raise CompileError(node.line, node.col, f"division by zero in a constant expression ('{node.op}' by 0)")
        if node.symbol == "+":
            return left + right
        if node.symbol == "-":
            return left - right
        if node.symbol == "*":
            return left * right
        quotient = abs(left) // abs(right) * (1 if (left < 0) == (right < 0) else -1)   # C-style, toward zero
        return quotient if node.symbol == "/" else left - quotient * right
    return None


def describe(token):
    if token.kind == "eof":
        return "end of file"
    if token.kind == "eol":
        return "end of line"
    if token.kind == "keyword":
        return f"keyword '{token.text}'"
    if token.kind == "string":
        return "a string"
    return f"'{token.text}'"


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens              # [Token] from the lexer, ending with eof
        self.pos = 0
        self.squads = set()               # names of the squads declared so far: types

    # -- reading the token stream -------------------------------------------

    def peek(self):
        return self.tokens[self.pos]

    def eat(self):
        token = self.tokens[self.pos]
        if token.kind != "eof":
            self.pos += 1
        return token

    def at(self, kind, text=None):
        token = self.peek()
        return token.kind == kind and (text is None or token.text == text)

    def at_sub(self, sub):
        token = self.peek()
        return token.kind == "keyword" and token.sub == sub

    def at_type(self):
        """A built-in type, or the name of a squad declared above."""
        token = self.peek()
        return self.at_sub("type") or (token.kind == "identifier" and token.text in self.squads)

    def error(self, msg, token=None):
        token = token or self.peek()
        return CompileError(token.line, token.col, msg)

    def expect(self, kind, text, what):
        if not self.at(kind, text):
            raise self.error(f"expected {what}, found {describe(self.peek())}")
        return self.eat()

    def expect_end(self, what):
        if not self.at("keyword", "no_bap"):
            raise self.error(f"expected 'no_bap' to end the {what}, found {describe(self.peek())}")
        self.eat()

    # -- one method per rule ------------------------------------------------

    def parse_program(self):
        """program ::= { item }     item ::= function | statement"""
        first = self.peek()
        items = []
        while not self.at("eof"):
            if self.at("keyword", "squad"):
                items.append(self.parse_squad())
            elif self.at("keyword", "drill"):
                items.append(self.parse_function(None))
            elif self.at_type():
                items.append(self.parse_typed(top_level=True))
            else:
                items.append(self.parse_statement())
        return ProgramNode(first.line, first.col, items)

    def parse_typed(self, top_level):
        """A type comes first in both  function ::= [ type ] "drill" ...  and
        decl ::= [ "sliding" ] type ident ... : eat it, then the next token decides."""
        type_token = self.eat()
        if self.at("keyword", "drill"):
            if not top_level:
                raise self.error("a function can only be declared at the top level, not inside a block")
            return self.parse_function(type_token.text)
        return self.parse_decl(False, type_token.text)

    def parse_function(self, return_type, squad=None):
        """function ::= [ type ] "drill" ident "(" [ param { "," param } ] ")" block
        -- the return type, if any, is already eaten; `squad` names the squad around a
        member function"""
        self.eat()                                             # drill
        name = self.expect("identifier", None, "a function name after 'drill'")
        self.expect("punct", "(", f"'(' after the function name '{name.text}'")
        params = []
        if not self.at("punct", ")"):
            params.append(self.parse_param())
            while self.at("punct", ","):
                self.eat()
                params.append(self.parse_param())
        self.expect("punct", ")", "',' or ')' in the parameter list")
        body = self.parse_block(f"the body of '{name.text}'")
        return FunctionNode(name.line, name.col, name.text, params, return_type, body, squad)

    def parse_squad(self):
        """squad ::= "squad" ident "{" field { field } { function } "}"

        A field and a member function both may start with a type; as at the top level,
        the type is eaten first and "drill" after it decides. The fields come first: a
        field after a member function is an error."""
        self.eat()                                             # squad
        name = self.expect("identifier", None, "a squad name after 'squad'")
        self.squads.add(name.text)        # a type from here on (a field of its own type is a semantic error)
        self.expect("punct", "{", f"'{{' to open squad '{name.text}'")
        if self.at("punct", "}"):
            raise self.error(f"squad '{name.text}' is empty: a squad needs at least one field")
        fields, methods = [], []
        while not self.at("punct", "}"):
            if self.at("eof"):
                raise self.error(f"squad '{name.text}' is not closed: expected '}}'")
            if self.at("keyword", "drill"):
                methods.append(self.parse_function(None, name.text))
                continue
            sliding = self.peek()
            mutable = self.at("keyword", "sliding")
            if mutable:
                self.eat()
            type_name = self.parse_type()
            if self.at("keyword", "drill"):
                if mutable:
                    raise self.error("a member function is never sliding: the object it is called "
                                     "on decides whether it may change", sliding)
                methods.append(self.parse_function(type_name, name.text))
                continue
            if methods:
                raise self.error(f"the fields of squad '{name.text}' come before its member functions")
            fields.append(self.parse_field(mutable, type_name))
        if not fields:
            raise self.error(f"squad '{name.text}' needs at least one field")
        self.eat()                                             # }
        return SquadNode(name.line, name.col, name.text, fields, methods)

    def parse_field(self, mutable, type_name):
        """field ::= [ "sliding" ] type ident "no_bap"   -- "sliding" and the type are eaten"""
        name = self.expect("identifier", None, f"a field name after '{type_name}'")
        if self.at("keyword", "post"):
            raise self.error(f"field '{name.text}' takes no value here: every object gets its own, "
                             f"in its literal")
        self.expect_end("field")
        return FieldDeclNode(name.line, name.col, name.text, type_name, mutable)

    def parse_param(self):
        """param ::= type ident"""
        type_name = self.parse_type()
        name = self.expect("identifier", None, f"a parameter name after '{type_name}'")
        return ParamNode(name.line, name.col, name.text, type_name)

    def parse_type(self):
        """type ::= "doze" | "fawty" | "line" | squad_name"""
        if not self.at_type():
            raise self.error(f"expected a type (doze, fawty, line or a squad), found {describe(self.peek())}")
        return self.eat().text

    def parse_block(self, what):
        """block ::= "{" statement { statement } "}" """
        self.expect("punct", "{", f"'{{' to open {what}")
        if self.at("punct", "}"):
            raise self.error(f"{what} is empty: a block needs at least one statement")
        body = [self.parse_statement()]
        while not self.at("punct", "}"):
            if self.at("eof"):
                raise self.error(f"{what} is not closed: expected '}}'")
            body.append(self.parse_statement())
        self.eat()                                             # }
        return body

    def parse_statement(self):
        """statement ::= decl | assign | call_stmt | if | return | exit | assert | print"""
        token = self.peek()
        if token.kind == "keyword":
            method = {
                "spot": self.parse_if,
                "cuh": self.parse_return,
                "scat": self.parse_exit,
                "on_the_guys": self.parse_assert,
                "air_out": self.parse_print,
                "pab_on": self.parse_inverted,
            }.get(token.text)
            if method:
                return method()
            if token.sub == "type":
                return self.parse_typed(top_level=False)
            if token.text == "sliding":
                self.eat()
                return self.parse_decl(True, self.parse_type())
            if token.text == "drill":
                raise self.error("a function can only be declared at the top level, not inside a block")
            if token.text == "squad":
                raise self.error("a squad can only be declared at the top level, not inside a block")
        if self.at_type():                                     # Point p post ...
            return self.parse_typed(top_level=False)
        if token.kind == "identifier":
            return self.parse_assign_or_call()
        raise self.error(f"a statement cannot start with {describe(token)}")

    def parse_decl(self, mutable, type_name):
        """decl ::= [ "sliding" ] type ident "post" expr "no_bap"
        -- "sliding" and the type are already eaten"""
        name = self.expect("identifier", None, f"a variable name after '{type_name}'")
        if self.at("punct", "("):
            raise self.error(f"a function needs 'drill' before its name: {type_name} drill {name.text}(...)")
        if not self.at("keyword", "post"):
            raise self.error(f"variable '{name.text}' needs an initial value: 'post' and an expression")
        self.eat()                                             # post
        init = self.parse_expr()
        self.check_overflow(type_name, init)
        self.expect_end("declaration")
        return DeclNode(name.line, name.col, name.text, type_name, mutable, init)

    def parse_inverted(self):
        """inverted ::= "pab_on" expr ( "post" ident [ type [ "sliding" ] ] | "cuh" | "scat" ) eol

        A statement written back to front, ending at the end of its line:
            pab_on 5 post x doze sliding    is    sliding doze x post 5 no_bap
            pab_on x bump 1 post x          is    x post x bump 1 no_bap
            pab_on merch cuh                is    cuh merch no_bap
            pab_on 0 scat                   is    scat 0 no_bap
        The value comes first, so it is parsed first; the word after it says which
        statement this was. The node is the same one the straight form builds."""
        flip = self.eat()                                      # pab_on
        value = self.parse_expr()
        if self.at("keyword", "post"):
            self.eat()
            name = self.expect("identifier", None, "a variable name after 'post'")
            links = self.parse_links()
            if links:                                          # pab_on 5 post c.center.x
                node = AssignNode(name.line, name.col, name.text, value, links)
            elif self.at_type():
                type_name = self.eat().text
                mutable = self.at("keyword", "sliding")
                if mutable:
                    self.eat()
                self.check_overflow(type_name, value)
                node = DeclNode(name.line, name.col, name.text, type_name, mutable, value)
            else:
                node = AssignNode(name.line, name.col, name.text, value)
        elif self.at("keyword", "cuh"):
            self.eat()
            node = ReturnNode(flip.line, flip.col, value)
        elif self.at("keyword", "scat"):
            self.eat()
            node = ExitNode(flip.line, flip.col, value)
        else:
            raise self.error(f"an inverted line goes 'value post name', 'value cuh' or 'value scat', "
                             f"found {describe(self.peek())}")
        if not self.at("eol"):
            raise self.error(f"an inverted line ends with the line: unexpected {describe(self.peek())}")
        self.eat()
        node.inverted = True
        return node

    def check_overflow(self, type_name, init):
        """The overflow check the parser can make: when an integer variable is
        initialised with a constant expression (numbers and operators only), its value
        is known now, and it must fit the declared type. Expressions with names are
        checked in stage 2, once names have types."""
        if type_name not in RANGES:
            return
        value = constant_value(init)
        if value is None:
            return
        low, high = RANGES[type_name]
        if not low <= value <= high:
            raise CompileError(init.line, init.col,
                               f"{type_name} overflow: the value {value} does not fit in {type_name} "
                               f"({low} .. {high})")

    def parse_assign_or_call(self):
        """assign ::= place "post" expr "no_bap"     call_stmt ::= place args "no_bap" """
        name = self.eat()
        links = self.parse_links()
        if self.at("keyword", "post"):
            self.eat()
            node = AssignNode(name.line, name.col, name.text, self.parse_expr(), links)
            self.expect_end("assignment")
            return node
        if links and self.at("punct", "("):                   # c.center.lift(1) no_bap
            node = CallStmtNode(name.line, name.col, self.parse_member_call(name, links))
            self.expect_end("call")
            return node
        if links:
            raise self.error(f"expected 'post' or '(' after '{links[-1].name}', found {describe(self.peek())}")
        if self.at("punct", "("):
            node = CallStmtNode(name.line, name.col, self.parse_call(name))
            self.expect_end("call")
            return node
        if self.at("identifier"):
            raise self.error(f"'{name.text}' is not a type (doze, fawty, line or a squad declared above), "
                             f"and a name cannot be followed by another name", name)
        raise self.error(f"expected 'post' or '(' after '{name.text}', found {describe(self.peek())}")

    def parse_if(self):
        """if ::= "spot" expr block [ "pivot" block ]"""
        keyword = self.eat()                                   # spot
        cond = self.parse_expr()
        then_body = self.parse_block("the 'spot' block")
        else_body = None
        if self.at("keyword", "pivot"):
            self.eat()
            else_body = self.parse_block("the 'pivot' block")
        return IfNode(keyword.line, keyword.col, cond, then_body, else_body)

    def parse_return(self):
        """return ::= "cuh" [ expr ] "no_bap" """
        keyword = self.eat()
        value = None if self.at("keyword", "no_bap") else self.parse_expr()
        self.expect_end("'cuh' statement")
        return ReturnNode(keyword.line, keyword.col, value)

    def parse_exit(self):
        """exit ::= "scat" [ expr ] "no_bap" """
        keyword = self.eat()
        value = None if self.at("keyword", "no_bap") else self.parse_expr()
        self.expect_end("'scat' statement")
        return ExitNode(keyword.line, keyword.col, value)

    def parse_assert(self):
        """assert ::= "on_the_guys" "(" expr ")" "no_bap" """
        keyword = self.eat()
        self.expect("punct", "(", "'(' after 'on_the_guys'")
        cond = self.parse_expr()
        self.expect("punct", ")", "')' to close 'on_the_guys'")
        self.expect_end("'on_the_guys' check")
        return AssertNode(keyword.line, keyword.col, cond)

    def parse_print(self):
        """print ::= "air_out" "(" ( string | expr ) ")" "no_bap" """
        keyword = self.eat()
        self.expect("punct", "(", "'(' after 'air_out'")
        if self.at("string"):
            token = self.eat()
            value = StringNode(token.line, token.col, token.text)
        else:
            value = self.parse_expr()
        self.expect("punct", ")", "')' to close 'air_out'")
        self.expect_end("'air_out' statement")
        return PrintNode(keyword.line, keyword.col, value)

    def parse_expr(self):
        """expr ::= arith [ ( "in_tune" | "fugazi" ) arith ]"""
        node = self.parse_arith()
        if self.at_sub("compare"):
            op = self.eat()
            node = BinOpNode(op.line, op.col, op.text, node, self.parse_arith())
            if self.at_sub("compare"):
                raise self.error("only one comparison is allowed in an expression: use ( ) to group")
        return node

    def parse_arith(self):
        """arith ::= term { ( "bump" | "tuck_in" ) term }"""
        node = self.parse_term()
        while self.at("keyword", "bump") or self.at("keyword", "tuck_in"):
            op = self.eat()
            node = BinOpNode(op.line, op.col, op.text, node, self.parse_term())
        return node

    def parse_term(self):
        """term ::= factor { ( "double_back" | "breakdown" | "scraps" ) factor }"""
        node = self.parse_factor()
        while (self.at("keyword", "double_back") or self.at("keyword", "breakdown")
               or self.at("keyword", "scraps")):
            op = self.eat()
            node = BinOpNode(op.line, op.col, op.text, node, self.parse_factor())
        return node

    def parse_factor(self):
        """factor ::= number | "merch" | "woof" | read | literal | place [ args ] | "(" expr ")" """
        token = self.peek()
        if token.kind == "number":
            self.eat()
            return IntNode(token.line, token.col, int(token.text))
        if self.at_sub("bool"):
            self.eat()
            return BoolNode(token.line, token.col, token.text == "merch")
        if self.at("keyword", "finna_hear"):
            self.eat()
            self.expect("punct", "(", "'(' after 'finna_hear'")
            self.expect("punct", ")", "')': finna_hear takes no arguments")
            return ReadNode(token.line, token.col)
        if token.kind == "identifier" and token.text in self.squads:
            return self.parse_literal()
        if token.kind == "identifier":
            self.eat()
            if self.at("punct", "("):
                return self.parse_call(token)
            links = self.parse_links()
            if links and self.at("punct", "("):
                return self.parse_member_call(token, links)
            if links:
                return FieldNode(token.line, token.col, token.text, links)
            return VarNode(token.line, token.col, token.text)
        if self.at("punct", "("):
            self.eat()
            node = self.parse_expr()
            self.expect("punct", ")", "')' to close '('")
            return node
        if token.kind == "string":
            raise self.error("a string can only be printed with air_out")
        raise self.error(f"expected a value (a number, merch, woof, a name or '('), found {describe(token)}")

    def parse_links(self):
        """place ::= ident { "." ident }   -- the ident is already eaten: the links only"""
        links = []
        while self.at("punct", "."):
            self.eat()
            field = self.expect("identifier", None, "a field name after '.'")
            links.append(Link(field.text, field.line, field.col))
        return links

    def parse_literal(self):
        """literal ::= squad_name "{" expr { "," expr } "}" """
        name = self.eat()
        if not self.at("punct", "{"):
            raise self.error(f"'{name.text}' is a squad: make one with {name.text}{{...}}, "
                             f"a value for every field")
        self.eat()                                             # {
        if self.at("punct", "}"):
            raise self.error(f"{name.text}{{}} is empty: give a value for every field")
        values = [self.parse_expr()]
        while self.at("punct", ","):
            self.eat()
            values.append(self.parse_expr())
        self.expect("punct", "}", f"',' or '}}' in the literal of '{name.text}'")
        return LiteralNode(name.line, name.col, name.text, values)

    def parse_call(self, name):
        """place args with no '.': a call of a drill -- the name is already eaten"""
        return CallNode(name.line, name.col, name.text, self.parse_args(name.text))

    def parse_member_call(self, name, links):
        """place args: the last link names the member function, the rest is the object --
        p.d2() is d2 on p, c.center.lift(1) is lift on c.center"""
        method = links[-1]
        target = (FieldNode(name.line, name.col, name.text, links[:-1]) if len(links) > 1
                  else VarNode(name.line, name.col, name.text))
        return MemberCallNode(method.line, method.col, target, method.name, self.parse_args(method.name))

    def parse_args(self, callee):
        """args ::= "(" [ expr { "," expr } ] ")" """
        self.eat()                                             # (
        args = []
        if not self.at("punct", ")"):
            args.append(self.parse_expr())
            while self.at("punct", ","):
                self.eat()
                args.append(self.parse_expr())
        self.expect("punct", ")", f"',' or ')' in the call to '{callee}'")
        return args


def parse(tokens):
    """Return the ProgramNode for a lexed source."""
    return Parser(tokens).parse_program()

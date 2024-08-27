import regex
import barg
from enum import Enum, auto
from typing import Iterable, Dict, List, Tuple, Any, Optional, Generator

# TODO python parser code generation


class BadGrammarError(Exception):
    pass


class InternalError(Exception):
    pass


class GenTyKind(Enum):
    STRUCT = 0
    ENUM = 1


class TokenType(Enum):
    IDENTIFIER = auto()
    STRING = auto()
    ASSIGN = auto()
    STRUCT = auto()
    ENUM = auto()
    LIST = auto()
    COMMA = auto()
    DOT = auto()
    COLON = auto()
    DOLLAR = auto()
    SEMICOLON = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()
    LPAREN = auto()
    RPAREN = auto()
    NUMBER = auto()
    ASTERISK = auto()
    PLUS = auto()
    QUESTION = auto()
    BAR = auto()
    # not actually used but typing '=' instead of ':=' will cause an error if this is a separate token
    EQUALS = auto()


class Token:
    def __init__(self, type: TokenType, value: str, line: int):
        self.type = type
        self.value = value
        self.line = line

    def __str__(self):
        return f"Token(type={self.type}, value='{self.value}', line={self.line})"


class Lexer:
    def __init__(self, source_code: str):
        self.source_code = source_code
        self._tokens = None
        self.patterns = {
            r"\bstruct\b": TokenType.STRUCT,
            r"\benum\b": TokenType.ENUM,
            r"\blist\b": TokenType.LIST,
            # do not support _ in last character so I can assume that any values in the generated python parser (eg barg builtin functions) suffixed with _ cannot be shadowed by bad user naming. thus, I force char after _ prefix.
            r"([a-zA-Z]([a-zA-Z0-9_]*[a-zA-Z0-9])?)|(_[a-zA-Z0-9_]*[a-zA-Z0-9])": TokenType.IDENTIFIER,
            r'".*?[^\\]"': TokenType.STRING,
            r":=": TokenType.ASSIGN,
            r",": TokenType.COMMA,
            r"\.": TokenType.DOT,
            r":": TokenType.COLON,
            r"\$": TokenType.DOLLAR,
            r";": TokenType.SEMICOLON,
            r"\{": TokenType.LBRACE,
            r"\}": TokenType.RBRACE,
            r"\[": TokenType.LBRACKET,
            r"\]": TokenType.RBRACKET,
            r"\(": TokenType.LPAREN,
            r"\)": TokenType.RPAREN,
            r"-?\d+": TokenType.NUMBER,
            r"\*": TokenType.ASTERISK,
            r"\+": TokenType.PLUS,
            r"\?": TokenType.QUESTION,
            r"\|": TokenType.BAR,
            r"=": TokenType.EQUALS,
        }
        self.compiled_patterns = {
            regex.compile(pattern): token_type
            for pattern, token_type in self.patterns.items()
        }

    def _tokenize(self):
        self._tokens = []
        pos = 0
        comment = False
        line = 1
        while pos < len(self.source_code):
            if self.source_code[pos] == "\n":
                comment = False
            elif self.source_code[pos] == "#":
                comment = True
            if comment:
                pos += 1
                continue

            m = None
            for pat, token_type in self.compiled_patterns.items():
                m = pat.match(self.source_code, pos)
                if m:
                    token_value = m.group(0)
                    self._tokens.append(Token(token_type, token_value, line))
                    pos = m.end()
                    break
            if not m:
                if self.source_code[pos] == "\n":
                    line += 1
                pos += 1  # Skipping any unrecognized characters

    def tokenize(self):
        if self._tokens is None:
            self._tokenize()
        return self._tokens


class TokenIter:
    def __init__(self, tokens):
        self.tokens = tokens
        self.position = 0

    def next(self):
        if self.position < len(self.tokens):
            token = self.tokens[self.position]
            self.position += 1
            return token
        return None

    def peek(self, n=0):
        if self.position + n < len(self.tokens):
            return self.tokens[self.position + n]
        return None


class ModuleInfo:
    def __init__(self, toplevel: "AstToplevel", barg_transforms: Dict[str, Any]):
        self.toplevel = toplevel
        self.definitions: Dict[AstVariable, AstNode] = {
            ast_assign.identifier: ast_assign.expression
            for ast_assign in toplevel.assignments
        }
        self.regex_cache = {}  # pattern to compiled regex object
        self.generated_types = {}  # generated classes are uniqued
        self.barg_transforms = barg_transforms
        self.internal_vars = {}


class AstNode:
    def __repr__(self):
        return str(self)

    def match(
        self,
        string: str,
        module: "ModuleInfo",
        symbol: Optional[str] = None,
    ):
        raise NotImplementedError()

    def __hash__(self):
        raise NotImplementedError()

    def __eq__(self, other: object, /) -> bool:
        raise NotImplementedError()


class AstAssignment(AstNode):
    def __init__(self, identifier, expression):
        self.identifier = identifier
        self.expression = expression

    def __str__(self):
        return (
            f"AstAssignment(identifier={self.identifier}, expression={self.expression})"
        )

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        for m, ncons in self.expression.match(string, module):
            yield m, ncons

    def __hash__(self):
        return hash((self.identifier, self.expression))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstAssignment) and (
            self.identifier,
            self.expression,
        ) == (other.identifier, other.expression)


class AstVariable(AstNode):
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return f"AstVariable(name={self.name})"

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        if self not in module.definitions:
            raise BadGrammarError(f"usage of undefined variable '{self.name}'")
        defn = module.definitions[self]
        for m, ncons in defn.match(string, module):
            yield m, ncons

    def __hash__(self):
        return hash((self.name,))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstVariable) and self.name == other.name


class AstString(AstNode):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return f'AstString(value="{self.value}")'

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        str_pat = "^" + self.value
        if string in module.regex_cache:
            pat = module.regex_cache[str_pat]
        else:
            pat = regex.compile(str_pat)
            module.regex_cache[str_pat] = pat
        for m in pat.finditer(string, overlapped=True):
            yield m.group(0), m.end(0)

    def __hash__(self):
        return hash((self.value,))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstString) and self.value == other.value


class AstStruct(AstNode):
    def __init__(self, fields: Tuple[Tuple[str, Any]]):
        fields_used = []
        for f in fields:
            fname = f[0]
            if fname in fields_used:
                raise BadGrammarError(
                    f"invalid list of fields: field name '{fname}' used multiple times in struct definition"
                )
            else:
                fields_used.append(fname)
        self.fields = fields  # fields is a list of (fieldname, expression) tuples

    def __str__(self):
        return f"AstStruct(fields={self.fields})"

    def _match(self, string: str, module: "ModuleInfo", matched_fields: List):
        if len(matched_fields) == len(self.fields):
            field_names = list(map(lambda p: p[0], self.fields))
            if self not in module.generated_types:
                g = {"GenTyKind_": GenTyKind}
                field_args = ", ".join(field_names)
                field_assigns = ("\n" + " " * 8).join(
                    map(lambda name: f"self.{name} = {name}", field_names)
                )
                code = f"""\
class BargGeneratedType:
    def __init__(self, {field_args}):
        self.type_ = GenTyKind_.STRUCT
        {field_assigns}

    def __str__(self):
        quote = '"'
        empty = ''
        return f'struct {{{{{', '.join(map(
            lambda name: name + ': {quote if isinstance(self.' + name + ', str) else empty}'
                + '{self.' + name + '}'
                + '{quote if isinstance(self.' + name + ', str) else empty}',
            field_names
        ))}}}}}'

    def __repr__(self):
        return str(self)
"""
                exec(code, g)
                typ = g["BargGeneratedType"]
                module.generated_types[self] = typ
            else:
                typ = module.generated_types[self]
            yield typ(*matched_fields), 0
        else:
            pat = self.fields[len(matched_fields)][1]
            for local_m, local_ncons in pat.match(string, module):
                for m, ncons in self._match(
                    string[local_ncons:], module, matched_fields + [local_m]
                ):
                    yield m, local_ncons + ncons

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        for m in self._match(string, module, []):
            yield m

    def __hash__(self):
        return hash((self.fields,))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstStruct) and self.fields == other.fields


class AstEnum(AstNode):
    def __init__(self, variants: Tuple[Tuple[str, Any]]):
        self.variants = variants  # variants is a list of (tag, expression) tuples

    def __str__(self):
        return f"AstEnum(variants={self.variants})"

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        if self not in module.generated_types:
            g = {"GenTyKind_": GenTyKind}
            code = """\
class BargGeneratedType:
    def __init__(self, tag: int, value):
        self.type_ = GenTyKind_.ENUM
        self.tag = tag
        self.value = value

    def __str__(self):
        quote = '"'
        return f'enum {{{self.tag}: {quote if isinstance(self.value, str) else ""}{self.value}{quote if isinstance(self.value, str) else ""}}}'

    def __repr__(self):
        return str(self)
"""
            exec(code, g)
            typ: Any = g["BargGeneratedType"]
            module.generated_types[self] = typ
        else:
            typ: Any = module.generated_types[self]

        for tag, expr in self.variants:
            for m, ncons in expr.match(string, module):
                yield typ(tag, m), ncons

    def __hash__(self):
        return hash((self.variants,))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstEnum) and self.variants == other.variants


class AstTransform(AstNode):
    def __init__(self, name, pattern_arg, args: Tuple[str | int] = tuple()):
        self.name = name
        self.pattern_arg = pattern_arg
        self.args = args

    def __str__(self):
        return f"AstTransform(name={self.name}, args={self.args})"

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        transform = barg.get_transform(module.barg_transforms, self.name)
        for pattern_arg, ncons in self.pattern_arg.match(string, module):
            yield transform(module, pattern_arg, *self.args), ncons

    def __hash__(self):
        return hash((self.name, self.pattern_arg, self.args))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstTransform) and (
            self.name,
            self.pattern_arg,
            self.args,
        ) == (other.name, other.pattern_arg, other.args)


class AstList(AstNode):
    def __init__(self, range_start, range_end, mode, expression):
        if mode not in ("greedy", "lazy"):
            raise BadGrammarError(
                "unknown list matching mode '" + mode + "': modes are 'greedy', 'lazy'"
            )
        self.range_start = range_start
        self.range_end = range_end
        self.mode = mode
        self.expression = expression

    def __str__(self):
        return f"AstList(mode={self.mode}, range=[{self.range_start}..{self.range_end if self.range_end is not None else ''}], expression={self.expression})"

    def _match_lazy(self, string: str, module: "ModuleInfo", matched_exprs: List):
        if self.range_end is not None and len(matched_exprs) >= self.range_end:
            return

        if self.range_start <= len(matched_exprs):
            yield matched_exprs, 0

        for local_m, local_ncons in self.expression.match(string, module):
            for m, ncons in self._match_lazy(
                string[local_ncons:], module, matched_exprs + [local_m]
            ):
                yield m, local_ncons + ncons

    def _match_greedy(self, string: str, module: "ModuleInfo", matched_exprs: List):
        if self.range_end is not None and len(matched_exprs) >= self.range_end:
            return

        for local_m, local_ncons in self.expression.match(string, module):
            for m, ncons in self._match_greedy(
                string[local_ncons:], module, matched_exprs + [local_m]
            ):
                yield m, local_ncons + ncons

        if self.range_start <= len(matched_exprs):
            yield matched_exprs, 0

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        for m, ncons in (
            self._match_lazy if self.mode == "lazy" else self._match_greedy
        )(string, module, []):
            yield m, ncons

    def __hash__(self):
        return hash((self.mode, self.range_start, self.range_end, self.expression))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstList) and (
            self.mode,
            self.range_start,
            self.range_end,
            self.expression,
        ) == (other.mode, other.range_start, other.range_end, other.expression)


class AstToplevel(AstNode):
    def __init__(self, statements: Tuple[AstAssignment | AstNode]):
        assignments = []
        n = 0
        for stmt in statements:
            if isinstance(stmt, AstAssignment):
                assignments.append(stmt)
            else:
                assignments.append(AstAssignment(f"_{n}", stmt))
                n += 1
        self.assignments = assignments

    def __str__(self) -> str:
        return f"AstToplevel(assignments={self.assignments})"

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        if not symbol:
            raise ValueError(
                "match function of AstToplevel requires symbol (str) which represents the pattern to match the string against"
            )
        expr = module.definitions[AstVariable(symbol)]
        for m, ncons in expr.match(string, module):
            yield m, ncons

    def __iter__(self):
        return iter(self.assignments)

    def __hash__(self):
        return hash((self.assignments,))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstToplevel) and self.assignments == other.assignments


class Parser:
    def __init__(self, tokens):
        self.tokens = TokenIter(tokens)
        self.ast = None

    def parse(self):
        if self.ast is None:
            assignments = []
            while self.tokens.peek():
                try:
                    assignments.append(self.parse_assignment())
                except Exception:
                    pass
            self.ast = AstToplevel(tuple(assignments))
        return self.ast

    def parse_assignment(self):
        if (
            self.tokens.peek(1)
            and self.tokens.peek().type == TokenType.IDENTIFIER
            and self.tokens.peek(1).type == TokenType.ASSIGN
        ):
            identifier = self.tokens.next()
            self.tokens.next()
            expression = self.parse_expression()
            self.expect(TokenType.SEMICOLON)
            return AstAssignment(AstVariable(identifier.value), expression)
        else:
            expression = self.parse_expression()
            self.expect(TokenType.SEMICOLON)
            return expression

    def parse_expression(self):
        seqs = [[self.parse_atomic_expression()]]
        while (token := self.tokens.peek()) and token.type not in (
            TokenType.COMMA,
            TokenType.SEMICOLON,
            TokenType.RBRACE,
            TokenType.RPAREN,
        ):
            if token.type == TokenType.ASTERISK:
                self.tokens.next()
                seqs[-1].append(
                    AstList(
                        0,
                        None,
                        "lazy"
                        if self.tokens.peek()
                        and self.tokens.peek().type == TokenType.QUESTION
                        and self.tokens.next()
                        else "greedy",
                        seqs[-1].pop(),
                    )
                )
            elif token.type == TokenType.PLUS:
                self.tokens.next()
                seqs[-1].append(
                    AstList(
                        1,
                        None,
                        "lazy"
                        if self.tokens.peek()
                        and self.tokens.peek().type == TokenType.QUESTION
                        and self.tokens.next()
                        else "greedy",
                        seqs[-1].pop(),
                    )
                )
            elif token.type == TokenType.QUESTION:
                self.tokens.next()
                seqs[-1].append(AstList(0, 1, "greedy", seqs[-1].pop()))
            elif token.type == TokenType.LBRACE:
                self.tokens.next()
                n = int(self.expect(TokenType.NUMBER))
                self.expect(TokenType.RBRACE)
                seqs[-1].append(AstList(n, n, "greedy", seqs[-1].pop()))
            elif token.type == TokenType.BAR:
                self.tokens.next()
                seqs.append([self.parse_atomic_expression()])
            elif token.type == TokenType.LPAREN:
                self.tokens.next()
                seqs[-1].append(self.parse_expression())
                self.expect(TokenType.RPAREN)
            else:
                seqs[-1].append(self.parse_atomic_expression())

        seq_structs = [
            AstStruct(tuple([(f"_{i}", seqs[j][i]) for i in range(len(seqs[j]))]))
            if len(seqs[j]) > 1
            else seqs[j][0]
            for j in range(len(seqs))
        ]
        seq_enum = (
            AstTransform(
                barg.TAKE_BUILTIN_NAME,
                AstEnum(
                    tuple([(f"_{i}", struct) for i, struct in enumerate(seq_structs)])
                ),
            )
            if len(seqs) > 1
            else seq_structs[0]
        )
        return seq_enum

    def parse_atomic_expression(self):
        token = self.tokens.peek()
        if token.type == TokenType.STRING:
            self.tokens.next()
            return AstString(token.value[1:-1])  # cut off quotes
        elif token.type == TokenType.IDENTIFIER:
            self.tokens.next()
            return AstVariable(token.value)
        elif token.type == TokenType.STRUCT:
            return self.parse_struct()
        elif token.type == TokenType.ENUM:
            return self.parse_enum()
        elif token.type == TokenType.LIST:
            return self.parse_list()
        elif token.type == TokenType.DOLLAR:
            return self.parse_transform_call()
        else:
            raise BadGrammarError(f"Unexpected token: {token}")

    def parse_transform_call(self):
        self.expect(TokenType.DOLLAR)

        transform_path = [self.expect(TokenType.IDENTIFIER).value]
        while (token := self.tokens.peek()) and token.type == TokenType.DOT:
            self.tokens.next()
            transform_path.append(self.expect(TokenType.IDENTIFIER).value)

        self.expect(TokenType.LPAREN)
        pattern_arg = self.parse_expression()
        token = self.expect_one_of(TokenType.RPAREN, TokenType.COMMA)

        args = []
        while (
            token and token.type != TokenType.RPAREN and (token := self.tokens.next())
        ):
            if token.type == TokenType.NUMBER:
                args.append(int(token.value))
            elif token.type == TokenType.IDENTIFIER:
                args.append(token.value)
            else:
                raise BadGrammarError(
                    "unexpected type of token for transform args: first arg must be pattern, the rest must be identifiers or integers"
                )
            token = self.expect_one_of(TokenType.RPAREN, TokenType.COMMA)

        return AstTransform(".".join(transform_path), pattern_arg, tuple(args))

    def parse_struct(self):
        self.expect(TokenType.STRUCT)
        fields = []
        self.expect(TokenType.LBRACE)
        while self.tokens.peek() and self.tokens.peek().type != TokenType.RBRACE:
            # if no name is provided, make it "_n" where n is the first unsigned number not already used
            if (
                self.tokens.peek(1)
                and self.tokens.peek().type == TokenType.IDENTIFIER
                and self.tokens.peek(1).type == TokenType.COLON
            ):
                fieldname = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.COLON)
            else:
                fieldn = 0
                while f"_{fieldn}" in map(lambda t: t[0], fields):
                    fieldn += 1
                fieldname = f"_{fieldn}"

            expression = self.parse_expression()
            fields.append((fieldname, expression))
            if self.tokens.peek() and self.tokens.peek().type == TokenType.COMMA:
                self.tokens.next()
        self.expect(TokenType.RBRACE)
        return AstStruct(tuple(fields))

    def parse_enum(self):
        self.expect(TokenType.ENUM)
        variants = []
        self.expect(TokenType.LBRACE)
        while self.tokens.peek() and self.tokens.peek().type != TokenType.RBRACE:
            # if no name is provided, make it "_n" where n is the first unsigned number not already used
            if (
                self.tokens.peek(1)
                and self.tokens.peek().type == TokenType.IDENTIFIER
                and self.tokens.peek(1).type == TokenType.COLON
            ):
                tag = self.expect(TokenType.IDENTIFIER).value
                self.expect(TokenType.COLON)
            else:
                fieldn = 0
                while f"_{fieldn}" in map(lambda t: t[0], variants):
                    fieldn += 1
                tag = f"_{fieldn}"

            expression = self.parse_expression()
            variants.append((tag, expression))
            if self.tokens.peek() and self.tokens.peek().type == TokenType.COMMA:
                self.tokens.next()
        self.expect(TokenType.RBRACE)
        return AstEnum(tuple(variants))

    def parse_list(self):
        mode = "greedy"
        self.expect(TokenType.LIST)
        self.expect(TokenType.LBRACKET)
        if (token := self.tokens.peek()) and token.type == TokenType.IDENTIFIER:
            self.tokens.next()
            mode = token.value
        range_start = int(self.expect(TokenType.NUMBER).value)
        range_end = None

        self.expect(TokenType.DOT)
        self.expect(TokenType.DOT)
        if self.tokens.peek() and self.tokens.peek().type == TokenType.NUMBER:
            range_end = int(self.tokens.next().value)

        self.expect(TokenType.RBRACKET)
        self.expect(TokenType.LBRACE)
        expression = self.parse_expression()
        self.expect(TokenType.RBRACE)

        return AstList(range_start, range_end, mode, expression)

    def expect(self, token_type):
        token = self.tokens.next()
        if not token or token.type != token_type:
            raise BadGrammarError(f"Expected token type {token_type}, but got {token}")
        return token

    def expect_one_of(self, *token_types):
        token = self.tokens.next()
        if not token or token.type not in token_types:
            raise BadGrammarError(f"Expected one of {token_types}, but got {token}")
        return token


def parse(
    strings: Iterable[str],
    grammar: str,
    grammar_toplevel_name: str = "Toplevel",
    barg_exec_transforms=None,
) -> List[Generator]:
    if barg_exec_transforms is None:
        barg_exec_transforms = barg.BARG_EXEC_BUILTINS
    tokens = Lexer(grammar).tokenize()
    ast = Parser(tokens).parse()
    module = ModuleInfo(ast, barg_exec_transforms)
    return [ast.match(string, module, grammar_toplevel_name) for string in strings]

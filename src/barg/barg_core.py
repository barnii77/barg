import traceback
import regex
import barg
from enum import Enum, auto
from typing import Iterable, Dict, List, Tuple, Any, Optional, Generator

# TODO better python parser code generation


# It is strongly recommended to pass `None` as the value for parameter `line`.
class BadGrammarError(Exception):
    def __init__(self, msg: str, line: Optional[int] = None):
        super().__init__(line, msg)
        if line is not None:
            self.__barg_line = line


# It is strongly recommended to pass `None` as the value for parameter `line`.
class InternalError(Exception):
    def __init__(self, msg: str, line: Optional[int] = None):
        super().__init__(line, msg)
        if line is not None:
            self.__barg_line = line


class GenTyKind(Enum):
    STRUCT = 0
    ENUM = 1


class TokenType(Enum):
    IDENTIFIER = auto()
    STRING = auto()
    MULTILINE_TEXT_STRING = auto()
    TEXT_STRING = auto()
    MULTILINE_STRING = auto()
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
    def __init__(self, type_: TokenType, value: str, line: int):
        self.type_ = type_
        self.value = value
        self.line = line

    def __str__(self):
        return f"Token(type={self.type_}, value='{self.value}', line={self.line})"


class Lexer:
    def __init__(self, source_code: str):
        self.errors = []
        self.source_code = source_code
        self._tokens = None
        self.patterns = {
            r"\bstruct\b": TokenType.STRUCT,
            r"\benum\b": TokenType.ENUM,
            r"\blist\b": TokenType.LIST,
            # do not support _ in last character so I can assume that any values in the generated python parser (eg barg builtin functions) suffixed with _ cannot be shadowed by bad user naming. thus, I force char after _ prefix.
            r"([a-zA-Z]([a-zA-Z0-9_]*[a-zA-Z0-9])?)|(_[a-zA-Z0-9_]*[a-zA-Z0-9])": TokenType.IDENTIFIER,
            r"```(.|\n)*?[^\\]```": TokenType.MULTILINE_TEXT_STRING,
            r"`.*?[^\\\n]`": TokenType.TEXT_STRING,
            r'"""(.|\n)*?[^\\]"""': TokenType.MULTILINE_STRING,
            r'".*?[^\\\n]"': TokenType.STRING,
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
                if self.source_code[pos] not in " \n":
                    self.errors.append(
                        f"On line {line}: Skipping unexpected character '{self.source_code[pos]}'"
                    )
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

    def next(self) -> Optional["Token"]:
        if self.position < len(self.tokens):
            token = self.tokens[self.position]
            self.position += 1
            return token
        return None

    def peek(self, n=0) -> Optional["Token"]:
        if self.position + n < len(self.tokens):
            return self.tokens[self.position + n]
        return None


class ModuleInfo:
    def __init__(self, toplevel: "AstToplevel", barg_transforms: Dict[str, Any]):
        self.toplevel = toplevel
        self.definitions: Dict[str, AstNode] = {
            ast_assign.identifier: ast_assign.expression
            for ast_assign in toplevel.assignments
        }
        self.regex_cache = {}  # pattern to compiled regex object
        self.generated_types = {}  # generated classes are uniqued
        self.barg_transforms = barg_transforms
        self.internal_vars = {}

    def __str__(self):
        return f"ModuleInfo({self.toplevel}, {self.definitions}, {self.regex_cache}, {self.generated_types}, {self.barg_transforms}, {self.internal_vars})"

    def __repr__(self) -> str:
        return str(self)


class AstNode:
    line: int = -1

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
    def __init__(self, line: int, identifier: str, expression):
        self.line = line
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
    def __init__(self, line: int, name: str):
        self.line = line
        self.name = name

    def __str__(self):
        return f"AstVariable(name={self.name})"

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        if self.name not in module.definitions:
            raise BadGrammarError(
                f"usage of undefined variable '{self.name}'", self.line
            )
        defn = module.definitions[self.name]
        for m, ncons in defn.match(string, module):
            yield m, ncons

    def __hash__(self):
        return hash((self.name,))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstVariable) and self.name == other.name


class AstString(AstNode):
    def __init__(self, line: int, value: str):
        self.line = line
        self.value = value

    def __str__(self):
        return f'AstString(value="{self.value}")'

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        str_pat = "^" + self.value
        if string in module.regex_cache:
            pat = module.regex_cache[str_pat]
        else:
            try:
                pat = regex.compile(str_pat)
            except Exception as e:
                e.__barg_line = self.line
                raise e
            module.regex_cache[str_pat] = pat
        for m in pat.finditer(string, overlapped=True):
            yield m.group(0), m.end(0)

    def __hash__(self):
        return hash((self.value,))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstString) and self.value == other.value


class AstStruct(AstNode):
    def __init__(self, line: int, fields: Tuple[Tuple[str, Any], ...]):
        self.line = line
        fields_used = []
        for f in fields:
            fname = f[0]
            if fname in fields_used:
                raise BadGrammarError(
                    f"invalid list of fields: field name '{fname}' used multiple times in struct definition",
                    self.line,
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
                try:
                    exec(code, g)
                except Exception as e:
                    e.__barg_line = self.line
                    raise e
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
    def __init__(self, line: int, variants: Tuple[Tuple[str, Any], ...]):
        self.line = line
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
            try:
                exec(code, g)
            except Exception as e:
                e.__barg_line = self.line  # attach barg grammar line info
                raise e
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
    def __init__(self, line: int, name, pattern_arg, args: Tuple[str | int] = tuple()):
        self.line = line
        self.name = name
        self.pattern_arg = pattern_arg
        self.args = args

    def __str__(self):
        return f"AstTransform(name={self.name}, args={self.args})"

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        transform = barg.get_transform(module.barg_transforms, self.name)
        for pattern_arg, ncons in self.pattern_arg.match(string, module):
            try:
                yield transform(module, pattern_arg, *self.args), ncons
            except Exception as e:
                e.__barg_line = self.line  # attach barg grammar line info
                raise e

    def __hash__(self):
        return hash((self.name, self.pattern_arg, self.args))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstTransform) and (
            self.name,
            self.pattern_arg,
            self.args,
        ) == (other.name, other.pattern_arg, other.args)


class AstList(AstNode):
    def __init__(self, line: int, range_start, range_end, mode, expression):
        self.line = line
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
    def __init__(self, line: int, statements: Tuple[AstAssignment | AstNode]):
        self.line = line
        assignments = []
        n = 0
        for stmt in statements:
            if isinstance(stmt, AstAssignment):
                assignments.append(stmt)
            else:
                assignments.append(AstAssignment(stmt.line, f"_{n}", stmt))
                n += 1
        self.assignments: List[AstAssignment] = assignments

    def __str__(self) -> str:
        return f"AstToplevel(assignments={self.assignments})"

    def match(self, string: str, module: "ModuleInfo", symbol: Optional[str] = None):
        if not symbol:
            raise ValueError(
                "match function of AstToplevel requires symbol (str) which represents the pattern to match the string against"
            )
        if symbol not in module.definitions:
            raise InternalError(
                f"specified toplevel symbol is not defined: '{symbol}'", -1
            )
        expr = module.definitions[symbol]
        for m, ncons in expr.match(string, module):
            yield m, ncons

    def __hash__(self):
        return hash((self.assignments,))

    def __eq__(self, other: object, /) -> bool:
        return isinstance(other, AstToplevel) and self.assignments == other.assignments


class AstTextString(AstNode):
    def __init__(self, line: int, value: str):
        self.line = line
        self.value = value


class Parser:
    def __init__(self, tokens):
        self.tokens = TokenIter(tokens)
        self.ast = None
        self.errors = []

    def parse(self):
        if self.ast is None:
            assignments = []
            while self.tokens.peek():
                try:
                    assignments.append(self.parse_assignment())
                except Exception as e:
                    token = self.tokens.peek()
                    if token:
                        self.errors.append(
                            f"On line {token.line}: {e}\nPython {traceback.format_exc()}"
                        )
                    else:
                        self.errors.append(
                            f"End of file: {e}\nPython {traceback.format_exc()}"
                        )
                    # consume until next statement
                    while (
                        self.tokens.peek()
                        and self.tokens.next().type_ != TokenType.SEMICOLON
                    ):
                        pass
            self.ast = AstToplevel(0, tuple(assignments))
        return self.ast

    def parse_assignment(self):
        if (
            self.tokens.peek(1)
            and self.tokens.peek().type_ == TokenType.IDENTIFIER
            and self.tokens.peek(1).type_ == TokenType.ASSIGN
        ):
            identifier = self.expect(TokenType.IDENTIFIER)
            self.expect(TokenType.ASSIGN)
            expression = self.parse_expression()
            self.expect(TokenType.SEMICOLON)
            return AstAssignment(
                identifier.line,
                identifier.value,
                expression,
            )
        else:
            expression = self.parse_expression()
            self.expect(TokenType.SEMICOLON)
            return expression

    def parse_expression(self):
        seqs = [[self.parse_atomic_expression()]]
        while (token := self.tokens.peek()) and token.type_ not in (
            TokenType.COMMA,
            TokenType.SEMICOLON,
            TokenType.RBRACE,
            TokenType.RPAREN,
        ):
            if token.type_ == TokenType.ASTERISK:
                self.tokens.next()
                seqs[-1].append(
                    AstList(
                        token.line,
                        0,
                        None,
                        "lazy"
                        if self.tokens.peek()
                        and self.tokens.peek().type_ == TokenType.QUESTION
                        and self.tokens.next()
                        else "greedy",
                        seqs[-1].pop(),
                    )
                )
            elif token.type_ == TokenType.PLUS:
                self.tokens.next()
                seqs[-1].append(
                    AstList(
                        token.line,
                        1,
                        None,
                        "lazy"
                        if self.tokens.peek()
                        and self.tokens.peek().type_ == TokenType.QUESTION
                        and self.tokens.next()
                        else "greedy",
                        seqs[-1].pop(),
                    )
                )
            elif token.type_ == TokenType.QUESTION:
                self.tokens.next()
                seqs[-1].append(AstList(token.line, 0, 2, "greedy", seqs[-1].pop()))
            elif token.type_ == TokenType.LBRACE:
                self.tokens.next()
                n = int(self.expect(TokenType.NUMBER).value)
                self.expect(TokenType.RBRACE)
                seqs[-1].append(AstList(token.line, n, n + 1, "greedy", seqs[-1].pop()))
            elif token.type_ == TokenType.BAR:
                self.tokens.next()
                seqs.append([self.parse_atomic_expression()])
            elif token.type_ == TokenType.LPAREN:
                self.tokens.next()
                seqs[-1].append(self.parse_expression())
                self.expect(TokenType.RPAREN)
            else:
                seqs[-1].append(self.parse_atomic_expression())

        seq_structs = [
            AstStruct(
                token.line if token else -1,
                tuple([(f"_{i}", seqs[j][i]) for i in range(len(seqs[j]))]),
            )
            if len(seqs[j]) > 1
            else seqs[j][0]
            for j in range(len(seqs))
        ]
        seq_enum = (
            AstTransform(
                token.line if token else -1,
                barg.TAKE_BUILTIN_NAME,
                AstEnum(
                    token.line if token else -1,
                    tuple([(f"_{i}", struct) for i, struct in enumerate(seq_structs)]),
                ),
            )
            if len(seqs) > 1
            else seq_structs[0]
        )
        return seq_enum

    def parse_atomic_expression(self):
        token: Optional[Token] = self.tokens.peek()
        if token is None:
            raise BadGrammarError("expected expression", -1)
        if token.type_ == TokenType.STRING:
            self.tokens.next()
            return AstString(token.line, token.value[1:-1])
        elif token.type_ == TokenType.MULTILINE_STRING:
            self.tokens.next()
            return AstString(token.line, token.value[3:-3])
        elif token.type_ == TokenType.TEXT_STRING:
            self.tokens.next()
            return AstTextString(token.line, token.value[1:-1])
        elif token.type_ == TokenType.MULTILINE_TEXT_STRING:
            self.tokens.next()
            return AstTextString(token.line, token.value[3:-3])
        elif token.type_ == TokenType.IDENTIFIER:
            self.tokens.next()
            return AstVariable(token.line, token.value)
        elif token.type_ == TokenType.STRUCT:
            return self.parse_struct()
        elif token.type_ == TokenType.ENUM:
            return self.parse_enum()
        elif token.type_ == TokenType.LIST:
            return self.parse_list()
        elif token.type_ == TokenType.DOLLAR:
            return self.parse_transform_call()
        elif token.type_ == TokenType.LPAREN:
            self.tokens.next()
            out = self.parse_expression()
            self.expect(TokenType.RPAREN)
            return out
        else:
            raise BadGrammarError(f"Unexpected token: {token}", token.line)

    def parse_transform_call(self):
        dollar = self.expect(TokenType.DOLLAR)

        transform_path = [self.expect(TokenType.IDENTIFIER).value]
        while (token := self.tokens.peek()) and token.type_ == TokenType.DOT:
            self.tokens.next()
            transform_path.append(self.expect(TokenType.IDENTIFIER).value)

        self.expect(TokenType.LPAREN)
        pattern_arg = self.parse_expression()
        token = self.expect_one_of(TokenType.RPAREN, TokenType.COMMA)

        args = []
        while (
            token and token.type_ != TokenType.RPAREN and (token := self.tokens.next())
        ):
            if token.type_ == TokenType.NUMBER:
                args.append(int(token.value))
            elif token.type_ == TokenType.IDENTIFIER:
                args.append(token.value)
            elif token.type_ == TokenType.MULTILINE_TEXT_STRING:
                args.append(AstTextString(token.line, token.value[3:-3]))
            elif token.type_ == TokenType.TEXT_STRING:
                args.append(AstTextString(token.line, token.value[1:-1]))
            else:
                raise BadGrammarError(
                    "unexpected type of token for transform args: first arg must be pattern, the rest must be identifiers or integers",
                    token.line,
                )
            token = self.expect_one_of(TokenType.RPAREN, TokenType.COMMA)

        return AstTransform(
            dollar.line, ".".join(transform_path), pattern_arg, tuple(args)
        )

    def parse_struct(self):
        struct_kwd = self.expect(TokenType.STRUCT)
        fields = []
        self.expect(TokenType.LBRACE)
        while self.tokens.peek() and self.tokens.peek().type_ != TokenType.RBRACE:
            # if no name is provided, make it "_n" where n is the first unsigned number not already used
            if (
                self.tokens.peek(1)
                and self.tokens.peek().type_ == TokenType.IDENTIFIER
                and self.tokens.peek(1).type_ == TokenType.COLON
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
            if self.tokens.peek() and self.tokens.peek().type_ == TokenType.COMMA:
                self.tokens.next()
        self.expect(TokenType.RBRACE)
        return AstStruct(struct_kwd.line, tuple(fields))

    def parse_enum(self):
        enum_kwd = self.expect(TokenType.ENUM)
        variants = []
        self.expect(TokenType.LBRACE)
        while self.tokens.peek() and self.tokens.peek().type_ != TokenType.RBRACE:
            # if no name is provided, make it "_n" where n is the first unsigned number not already used
            if (
                self.tokens.peek(1)
                and self.tokens.peek().type_ == TokenType.IDENTIFIER
                and self.tokens.peek(1).type_ == TokenType.COLON
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
            if self.tokens.peek() and self.tokens.peek().type_ == TokenType.COMMA:
                self.tokens.next()
        self.expect(TokenType.RBRACE)
        return AstEnum(enum_kwd.line, tuple(variants))

    def parse_list(self):
        mode = "greedy"
        list_kwd = self.expect(TokenType.LIST)
        self.expect(TokenType.LBRACKET)
        if (token := self.tokens.peek()) and token.type_ == TokenType.IDENTIFIER:
            self.tokens.next()
            mode = token.value
        range_start = int(self.expect(TokenType.NUMBER).value)
        range_end = None

        self.expect(TokenType.DOT)
        self.expect(TokenType.DOT)
        if self.tokens.peek() and self.tokens.peek().type_ == TokenType.NUMBER:
            range_end = int(self.tokens.next().value)

        self.expect(TokenType.RBRACKET)
        self.expect(TokenType.LBRACE)
        expression = self.parse_expression()
        self.expect(TokenType.RBRACE)

        return AstList(list_kwd.line, range_start, range_end, mode, expression)

    def expect(self, token_type):
        token = self.tokens.peek()
        if not token or token.type_ != token_type:
            raise BadGrammarError(
                f"Expected token type {token_type}, but got {token}",
                token.line if token else -1,
            )
        self.tokens.next()
        return token

    def expect_one_of(self, *token_types):
        token = self.tokens.peek()
        if not token or token.type_ not in token_types:
            raise BadGrammarError(
                f"Expected one of {token_types}, but got {token}",
                token.line if token else -1,
            )
        self.tokens.next()
        return token


def parse(
    strings: Iterable[str],
    grammar: str,
    error_out: List[str],
    grammar_toplevel_name: str = "Toplevel",
    barg_exec_transforms=None,
) -> List[Generator]:
    if barg_exec_transforms is None:
        barg_exec_transforms = barg.BARG_EXEC_BUILTINS
    lexer = Lexer(grammar)
    tokens = lexer.tokenize()
    error_out.extend(lexer.errors)
    parser = Parser(tokens)
    ast = parser.parse()
    error_out.extend(parser.errors)
    module = ModuleInfo(ast, barg_exec_transforms)
    out = [ast.match(string, module, grammar_toplevel_name) for string in strings]
    return out


def generate_python_parser(
    barg_source_path: str, grammar: str, grammar_toplevel_name: str
) -> str:
    code = f'GRAMMAR = """{grammar}"""\nGRAMMAR_TOPLEVEL_NAME = "{grammar_toplevel_name}"\n\n'
    with open(f"{barg_source_path}/barg/barg_exec_builtins.py") as f:
        code += f.read() + "\n\n"
    with open(f"{barg_source_path}/barg/barg_core.py") as f:
        code += f.read() + "\n\n"
    code += """
def parse(
    strings: Iterable[str],
    error_out: List[str],
    barg_exec_transforms=None,
) -> List[Generator | Exception]:
    if barg_exec_transforms is None:
        barg_exec_transforms = barg.BARG_EXEC_BUILTINS
    lexer = Lexer(GRAMMAR)
    tokens = lexer.tokenize()
    error_out.extend(lexer.errors)
    parser = Parser(tokens)
    ast = parser.parse()
    error_out.extend(parser.errors)
    module = ModuleInfo(ast, barg_exec_transforms)
    out = []
    for string in strings:
        try:
            out.append(ast.match(string, module, GRAMMAR_TOPLEVEL_NAME))
        except Exception as e:
            error_out.append(
                f"On line {e.__barg_line if hasattr(e, '__barg_line') and e.__barg_line != -1 else '<unknown/eof>'}: {e}\\nPython {traceback.format_exc()}"
            )
            out.append(Exception("parsing failed"))
    return out
"""
    return code

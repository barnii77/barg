import barg
from typing import Dict, Optional, List


def indent(text: str) -> str:
    return "\n".join(" " * 4 + line for line in text.splitlines())


class CodeGenerator:
    """
    Abstract codegen backend for different codegen targets
    """

    def __init__(self, ast: "barg.AstToplevel", mod: "barg.ModuleInfo"):
        self.mod = mod
        self.uid = 0

    @staticmethod
    def preprocess_pattern(pattern: str) -> str:
        return "^" + pattern

    def next_uid(self) -> int:
        u = self.uid
        self.uid += 1
        return u

    def codegen(self, *args, **kwargs) -> str:
        raise NotImplementedError

    def gen_ast(self, ast: "barg.AstNode"):
        if isinstance(ast, barg.AstStruct):
            self.gen_struct(ast)
        elif isinstance(ast, barg.AstEnum):
            self.gen_enum(ast)
        elif isinstance(ast, barg.AstString):
            self.gen_string(ast)
        elif isinstance(ast, barg.AstTransform):
            self.gen_transform(ast)
        elif isinstance(ast, barg.AstTextString):
            self.gen_text_string(ast)
        elif isinstance(ast, barg.AstAssignment):
            self.gen_assignment(ast)
        elif isinstance(ast, barg.AstVariable):
            self.gen_variable(ast)
        elif isinstance(ast, barg.AstList):
            self.gen_list(ast)
        elif isinstance(ast, barg.AstToplevel):
            self.gen_toplevel(ast)
        else:
            raise TypeError(ast)

    def gen_struct(self, ast: "barg.AstStruct"):
        raise NotImplementedError

    def gen_enum(self, ast: "barg.AstEnum"):
        raise NotImplementedError

    def gen_string(self, ast: "barg.AstString"):
        raise NotImplementedError

    def gen_transform(self, ast: "barg.AstTransform"):
        raise NotImplementedError

    def gen_text_string(self, ast: "barg.AstTextString"):
        raise NotImplementedError

    def gen_assignment(self, ast: "barg.AstAssignment"):
        raise NotImplementedError

    def gen_variable(self, ast: "barg.AstVariable"):
        raise NotImplementedError

    def gen_list(self, ast: "barg.AstList"):
        raise NotImplementedError

    def gen_toplevel(self, ast: "barg.AstToplevel"):
        raise NotImplementedError


class PyCGInternalGenSymbol:
    """
    A class representing module level functions or classes (global symbols) generated as part of the parser that are internal (ie. not *directly* exposed)
    """

    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code


def unique_codes(defns) -> List[str]:
    used = set()
    out = []
    for defn in defns:
        if id(defn) in used:
            continue
        used.add(id(defn))
        out.append(defn.code)
    return out


class PythonCodeGenerator(CodeGenerator):
    """
    Python codegen target. Generated code structure:
    For Strings:
    ```py
    def _match0_(text):
        # return generator
        ...  # all regex matches for string for example

    def _match1_(text):
        return ...  # match and return a 'Function'

    class Function:
        def parse(text: str) -> "Function":
            return _match1_(text)
    ```
    """

    def __init__(self, ast: "barg.AstToplevel", mod: "barg.ModuleInfo"):
        super().__init__(ast, mod)
        self.match_functions: Dict["barg.AstNode", PyCGInternalGenSymbol] = {}
        self.class_defs: Dict["barg.AstNode", PyCGInternalGenSymbol] = {}
        self.glob_assigns: Dict["barg.AstNode", PyCGInternalGenSymbol] = {}
        self.gen_ast(ast)

    def codegen(self, head: Optional[str] = None) -> str:
        """
        The codegen method generates the python parser.
        Args:
            head: code to be inserted after the imports that contains transform definitions etc
        """
        head = (
            """\
import regex
from enum import Enum as _Enum_
from typing import Any as _Any_, Dict as _Dict_, Callable as _Callable_

_TRANSFORMS_ = {}


def _wrap_in_parsable_type_(func):
    class Ty:
        @staticmethod
        def parse(text: str):
            return next(func(text))[0]

    return Ty


class _GenTyKind_(_Enum_):
    STRUCT = 0
    ENUM = 1


class _TextString_:
    def __init__(self, value: str):
        self.value = value


class _BadGrammarError_(Exception):
    def __init__(self, msg: str, line: _Optional_[int] = None):
        super().__init__(line, msg)


# It is strongly recommended to pass `None` as the value for parameter `line`.
class _InternalError_(Exception):
    def __init__(self, msg: str, line: _Optional_[int] = None):
        super().__init__(line, msg)


def _get_transform_(transforms: _Dict_[str, _Any_], full_name: str) -> _Callable_:
    path = full_name.split(".")
    transform = transforms
    for name in path:
        if name not in transform:
            raise _BadGrammarError_(f"usage of unknown transform '{full_name}'")
        transform = transform[name]
    if not callable(transform):
        raise _InternalError_(f"transform {full_name} is a namespace, not a function")
    return transform
"""
            if head is None
            else head
        )

        funcs = "\n\n".join(unique_codes(self.match_functions.values()))
        classes = "\n\n".join(unique_codes(self.class_defs.values()))
        glob_assigns = "\n".join(unique_codes(self.glob_assigns.values()))
        return "\n\n".join((head, funcs, classes, glob_assigns))

    def gen_string(self, ast: "barg.AstString"):
        if ast in self.match_functions:
            return

        u = self.next_uid()

        code = f"""\
# generated from barg grammar line {ast.line}
# regex matcher
def _match{u}_(text: str):
    for m in _pat{u}_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)
"""
        self.match_functions[ast] = PyCGInternalGenSymbol(f"_match{u}_", code)
        content = self.preprocess_pattern(ast.value).replace('"', '\\"')
        self.glob_assigns[ast] = PyCGInternalGenSymbol(
            f"_pat{u}_", f'_pat{u}_ = _regex_.compile(r"""{content}""")'
        )

    def gen_list(self, ast: "barg.AstList"):
        if ast in self.match_functions:
            return

        u = self.next_uid()

        self.match_functions[ast] = PyCGInternalGenSymbol(
            f"_match{u}_",
            None,
        )

        if ast.expression not in self.match_functions:
            self.gen_ast(ast.expression)

        ast_matcher = self.match_functions[ast.expression]
        end_cond = (
            f"""\
    if len(matched_exprs) >= {ast.range_end}:
        return"""
            if ast.range_end is not None
            else ""
        )

        if ast.mode == "lazy":
            code = f"""\
# generated from barg grammar line {ast.line}
# lazy list matcher
def _match{u}_(text: str, matched_exprs=None):
    if matched_exprs is None:
        matched_exprs = []
{end_cond}
    if {ast.range_start} <= len(matched_exprs):
        yield matched_exprs, 0

    for local_m, local_ncons in {ast_matcher.name}(text):
        for m, ncons in _match{u}_(
            text[local_ncons:], matched_exprs + [local_m]
        ):
            yield m, local_ncons + ncons
"""
        else:
            code = f"""\
# generated from barg grammar line {ast.line}
# greedy list matcher
def _match{u}_(text: str, matched_exprs=None):
    if matched_exprs is None:
        matched_exprs = []
{end_cond}
    for local_m, local_ncons in {ast_matcher.name}(text):
        for m, ncons in _match{u}_(
            text[local_ncons:], matched_exprs + [local_m]
        ):
            yield m, local_ncons + ncons

    if {ast.range_start} <= len(matched_exprs):
        yield matched_exprs, 0

"""
        self.match_functions[ast].code = code

    def gen_variable(self, ast: "barg.AstVariable"):
        if ast in self.match_functions:
            return

        if ast.name not in self.mod.definitions:
            raise barg.BadGrammarError(f"use of undefined name '{ast.name}'")

        self.gen_ast(self.mod.definitions[ast.name])
        self.match_functions[ast] = self.match_functions[self.mod.definitions[ast.name]]

    def gen_assignment(self, ast: "barg.AstAssignment"):
        if ast in self.glob_assigns:
            return

        self.gen_ast(ast.expression)

        if isinstance(ast.expression, (barg.AstStruct, barg.AstEnum)):
            self.glob_assigns[ast] = PyCGInternalGenSymbol(
                ast.identifier,
                f"{ast.identifier} = {self.class_defs[ast.expression].name}",
            )
        elif isinstance(ast.expression, barg.AstTextString):
            self.glob_assigns[ast] = PyCGInternalGenSymbol(
                ast.identifier,
                f"{ast.identifier} = {self.glob_assigns[ast.expression].name}",
            )
        else:
            self.glob_assigns[ast] = PyCGInternalGenSymbol(
                ast.identifier,
                f"{ast.identifier} = _wrap_in_parsable_type_({self.match_functions[ast.expression].name})",
            )

    def gen_text_string(self, ast: "barg.AstTextString"):
        if ast in self.glob_assigns:
            return

        u = self.next_uid()
        content = ast.value.replace('"', '\\"')
        self.glob_assigns[ast] = PyCGInternalGenSymbol(
            f"_text{u}_", f'_text{u}_ = _TextString_(r"""{content}""")'
        )

    def gen_transform(self, ast: "barg.AstTransform"):
        if ast in self.match_functions:
            return

        u = self.next_uid()

        self.match_functions[ast] = PyCGInternalGenSymbol(
            f"_match{u}_",
            None,
        )

        if ast.pattern_arg not in self.match_functions:
            self.gen_ast(ast.pattern_arg)

        matcher = self.match_functions[ast.pattern_arg]
        args_str = []
        for arg in ast.args:
            if isinstance(arg, int):
                args_str.append(str(arg))
            elif isinstance(arg, str):
                args_str.append(f'r"""{arg}"""')
            elif isinstance(arg, barg.AstTextString):
                content = arg.value.replace('"', '\\"')
                args_str.append(f'_TextString_(r"""{content}""")')
            else:
                raise barg.InternalError(
                    "invalid type of transform arg encountered (should have failed earlier with BadGrammarError but didn't)"
                )

        self.match_functions[
            ast
        ].code = f"""\
# generated from barg grammar line {ast.line}
# transform matcher
def _match{u}_(text: str):
    transform = _get_transform_(_TRANSFORMS_, r"{ast.name}")
    for m, ncons in {matcher.name}(text):
        yield transform(text, ncons, m, {', '.join(args_str)})
"""

    def gen_enum(self, ast: "barg.AstEnum"):
        if ast in self.class_defs or ast in self.match_functions:
            assert ast in self.class_defs and ast in self.match_functions
            return

        u = self.next_uid()

        self.match_functions[ast] = PyCGInternalGenSymbol(
            f"_match{u}_",
            None,
        )

        # generate type
        self.class_defs[ast] = PyCGInternalGenSymbol(
            f"_Ty{u}_",
            f"""\
# generated from barg grammar line {ast.line}
# enum type
class _Ty{u}_:
    def __init__(self, tag: str, value):
        self.type_ = _GenTyKind_.ENUM
        self.tag = tag
        self.value = value

    @staticmethod
    def parse(text: str):
        return next(_match{u}_(text))[0]
""",
        )

        # generate matching function
        loops = []
        for tag, expr in ast.variants:
            if expr not in self.match_functions:
                self.gen_ast(expr)
            body = indent(f"yield _Ty{u}_('{tag}', m), ncons")
            loops.append(
                f"for m, ncons in {self.match_functions[expr].name}(text):\n{body}"
            )
        loops = "\n".join(loops)
        self.match_functions[
            ast
        ].code = f"""\
# generated from barg grammar line {ast.line}
# enum matcher
def _match{u}_(text: str):
{indent(loops)}
"""

    def gen_struct(self, ast: "barg.AstStruct"):
        if ast in self.class_defs or ast in self.match_functions:
            assert ast in self.class_defs and ast in self.match_functions
            return

        u = self.next_uid()

        self.match_functions[ast] = PyCGInternalGenSymbol(
            f"_match{u}_",
            None,
        )

        # generate the type definition
        field_names = list(map(lambda p: p[0], ast.fields))
        field_args = ", ".join(field_names)
        field_assigns = ("\n" + " " * 8).join(
            map(lambda name: f"self.{name} = {name}", field_names)
        )
        self.class_defs[ast] = PyCGInternalGenSymbol(
            f"_Ty{u}_",
            f"""\
# generated from barg grammar line {ast.line}
# struct type
class _Ty{u}_:
    def __init__(self, {field_args}):
        self.type_ = _GenTyKind_.STRUCT
        {field_assigns}

    @staticmethod
    def parse(text: str):
        return next(_match{u}_(text))[0]
""",
        )

        # generate the matching function
        def get_local_ncons_up_to(n):
            return " + ".join("local_ncons" + str(i) for i in range(n))

        nested_fors = f"yield _Ty{u}_({', '.join('local_m' + str(i) for i in range(len(ast.fields)))}), {get_local_ncons_up_to(len(ast.fields))}"
        for i, (_, expr) in reversed(list(enumerate(ast.fields))):
            if expr not in self.match_functions:
                self.gen_ast(expr)
            nested_fors = f"for local_m{i}, local_ncons{i} in {self.match_functions[expr].name}(text{('[' + get_local_ncons_up_to(i) + ':]') if i > 0 else ''}):\n{indent(nested_fors)}"

        self.match_functions[
            ast
        ].code = f"""\
# generated from barg grammar line {ast.line}
# struct matcher
def _match{u}_(text: str):
{indent(nested_fors)}
"""

    def gen_toplevel(self, ast: "barg.AstToplevel"):
        for defn in ast.assignments:
            self.gen_assignment(defn)

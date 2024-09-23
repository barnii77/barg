import barg
from typing import Dict


def indent(text: str) -> str:
    return '\n'.join(' ' * 4 + line for line in text.splitlines())


class CodeGenerator:
    """
    Abstract codegen backend for different codegen targets
    """

    def __init__(self, mod: "barg.ModuleInfo"):
        self.mod = mod

    def codegen(self) -> str:
        raise NotImplementedError

    def gen_ast(self, ast: "barg.AstNode"):
        raise NotImplementedError

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


class PyCGFunc:
    def __init__(self, name: str, code: str):
        self.name = name
        self.code = code


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

    def __init__(self, mod: "barg.ModuleInfo"):
        super().__init__(mod)
        self.match_functions: Dict["barg.AstNode", PyCGFunc] = {}
        self.uid = 0

    def next_uid(self) -> int:
        u = self.uid
        self.uid += 1
        return u

    def gen_string(self, ast: "barg.AstString"):
        u = self.next_uid()
        code = f"""\
_pat{u}_ = {ast.value}
def _match{u}_(text: str):
    for m in _pat{u}_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)
"""
        self.match_functions[ast] = PyCGFunc(f"_match{u}_", code)

    def gen_list(self, ast: "barg.AstList"):
        u = self.next_uid()
        if ast not in self.match_functions:
            self.gen_ast(ast)
        ast_matcher = self.match_functions.get(ast)
        if ast.mode == "greedy":
            code = f"""\
def _match{u}_(text: str, matched_exprs=None):
    if matched_exprs is None:
        matched_exprs = []

    if {ast.range_end} is not None and len(matched_exprs) >= self.range_end:
        return

    if self.range_start <= len(matched_exprs):
        yield matched_exprs, 0

    for local_m, local_ncons in {ast_matcher.name}(string, module):
        for m, ncons in _match{u}_(
            string[local_ncons:], module, matched_exprs + [local_m]
        ):
            yield m, local_ncons + ncons
"""
        else:
            code = """\
def _match{u}_(text: str, matched_exprs=None):
    if matched_exprs is None:
        matched_exprs = []

    if self.range_end is not None and len(matched_exprs) >= self.range_end:
        return

    for local_m, local_ncons in self.expression.match(string, module):
        for m, ncons in self._match_greedy(
            string[local_ncons:], module, matched_exprs + [local_m]
        ):
            yield m, local_ncons + ncons

    if self.range_start <= len(matched_exprs):
        yield matched_exprs, 0

"""
        self.match_functions[ast] = PyCGFunc(f"_match{u}_", code)

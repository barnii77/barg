import barg


"""
Abstract codegen backend for different codegen targets
"""
class CodeGenerator:
    def gen_struct(self, ast: "barg.AstStruct"):
        raise NotImplementedError

    def gen_enum(self, ast: "barg.AstEnum"):
        raise NotImplementedError

    def gen_string(self, ast: "barg.AstString"):


    def gen_transform(self, ast: "barg.AstTransform"):
        raise NotImplementedError

    def gen_text_string(self, ast: "barg.AstTextString"):
        raise NotImplementedError

    # TODO


"""
Python codegen target. Generated code structure:
For Strings:
```py
def match_string(text: str, pat: str):
    ...
```
"""
class PythonCodeGenerator(CodeGenerator):
    def __init__(self):
        super().__init__()

import barg


class Target:
    def __init__(self):
        raise NotImplementedError()

    def gen_ast_node(self, ast: "barg.AstNode"):
        dispatch_map = {
            barg.AstStruct: self.gen_ast_struct,
            barg.AstEnum: self.gen_ast_enum,
            barg.AstList: self.gen_ast_list,
            barg.AstString: self.gen_ast_string,
            barg.AstVariable: self.gen_ast_variable,
            barg.AstTransform: self.gen_ast_transform,
            barg.AstAssignment: self.gen_ast_assignment,
            barg.AstToplevel: self.gen_ast_toplevel,
        }
        for ty, func in dispatch_map.items():
            if isinstance(ast, ty):
                return func(ast)
        raise TypeError(
            f"Parameter ast has invalid type, must be a derived class of abstract class AstNode but seems to not be. Type of ast_node: {type(ast)}"
        )

    def gen_ast_struct(self, ast: "barg.AstStruct"):
        raise NotImplementedError()

    def gen_ast_enum(self, ast: "barg.AstEnum"):
        raise NotImplementedError()

    def gen_ast_list(self, ast: "barg.AstList"):
        raise NotImplementedError()

    def gen_ast_string(self, ast: "barg.AstString"):
        raise NotImplementedError()

    def gen_ast_variable(self, ast: "barg.AstVariable"):
        raise NotImplementedError()

    def gen_ast_transform(self, ast: "barg.AstTransform"):
        raise NotImplementedError()

    def gen_ast_assignment(self, ast: "barg.AstAssignment"):
        raise NotImplementedError()

    def gen_ast_toplevel(self, ast: "barg.AstToplevel"):
        raise NotImplementedError()


class PythonTarget(Target):
    def __init__(self):
        pass

    def gen_ast_struct(self, ast: "barg.AstStruct"):
        raise NotImplementedError()

    def gen_ast_enum(self, ast: "barg.AstEnum"):
        raise NotImplementedError()

    def gen_ast_list(self, ast: "barg.AstList"):
        raise NotImplementedError()

    def gen_ast_string(self, ast: "barg.AstString"):
        raise NotImplementedError()

    def gen_ast_variable(self, ast: "barg.AstVariable"):
        raise NotImplementedError()

    def gen_ast_transform(self, ast: "barg.AstTransform"):
        raise NotImplementedError()

    def gen_ast_assignment(self, ast: "barg.AstAssignment"):
        raise NotImplementedError()

    def gen_ast_toplevel(self, ast: "barg.AstToplevel"):
        raise NotImplementedError()

import barg
from typing import Optional, Any, Dict, Callable


# NOTE: '|Any ' in field so it can be called in non-type-safe way from other places
def builtin_take(module, m, field: Optional[str] | Any = None):
    if field is not None and not isinstance(field, str):
        raise barg.BadGrammarError(
            f"the field parameter of the take builtin must be an identifier or unprovided, not {type(field)}",
        )
    if not hasattr(m, "type_"):
        raise barg.InternalError(
            "can only apply barg_take builtin to struct or enum type"
        )
    if m.type_ == barg.GenTyKind.STRUCT:
        if not field:
            raise barg.BadGrammarError(
                "if take is applied to a struct, it takes a field parameter in the form $take(expr, fieldname123) where fieldname123 (without quotes) is the fieldname",
            )
        return getattr(m, field)
    elif m.type_ == barg.GenTyKind.ENUM:
        return getattr(m, "value")
    else:
        raise barg.InternalError("invalid value of 'type_' encountered in take")


def builtin_int(module, m):
    if not isinstance(m, str):
        raise barg.BadGrammarError(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}",
        )
    return int(m)


def builtin_float(module, m):
    if not isinstance(m, str):
        raise barg.BadGrammarError(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}",
        )
    return float(m)


def builtin_delete(module, m, field: Optional[str] | Any = None):
    if field is not None and not isinstance(field, str):
        raise barg.BadGrammarError(
            f"the field parameter of the delete builtin must be an identifier or unprovided, not {type(field)}",
        )
    if not hasattr(m, "type_"):
        raise barg.BadGrammarError(
            "can only apply barg_take builtin to struct or enum type"
        )
    if m.type_ == barg.GenTyKind.STRUCT and field:
        setattr(m, field, None)
    elif m.type_ == barg.GenTyKind.ENUM:
        if field and m.tag == field or not field:
            m.value = None
    else:
        raise barg.InternalError("invalid value of 'type_' encountered in delete")
    return m


def builtin_mark(module, m, mark: str):
    if not mark or not isinstance(mark, str):
        raise barg.BadGrammarError(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    setattr(m, f"mark_{mark}_", None)
    return m


def builtin_filter(module, m, mark: str):
    if not mark or not isinstance(mark, str):
        raise barg.BadGrammarError(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    if not isinstance(m, list):
        raise barg.BadGrammarError(f"filter builtin applied to non-list object {m}")
    return list(filter(lambda item: hasattr(item, f"mark_{mark}_"), m))


def builtin_pyexpr(module, m, pyexpr: "barg.AstTextString | str | Any", *args):
    if not pyexpr or not isinstance(pyexpr, (barg.AstTextString, str)):
        raise barg.BadGrammarError(
            f"pyexpr '{pyexpr}' is invalid, pyexpr must be a non-empty text string or variable"
        )
    if isinstance(pyexpr, barg.AstTextString):
        code = pyexpr.value
    else:
        if pyexpr not in module.definitions:
            raise barg.BadGrammarError(f"variable '{pyexpr}' is not defined")
        defn = module.definitions[pyexpr]
        if not isinstance(defn, barg.AstTextString):
            raise barg.BadGrammarError(
                f"variable '{pyexpr}' does not refer to a text string (but has to)"
            )
        code = defn.value
    return eval(code, {"module": module, "x": m, "args": args, "barg": barg})


def builtin_pyscript(module, m, pyscript: "barg.AstTextString | str | Any", *args):
    if not pyscript or not isinstance(pyscript, (barg.AstTextString, str)):
        raise barg.BadGrammarError(
            f"pyscript '{pyscript}' is invalid, pyscript must be a non-empty text string or variable"
        )
    if isinstance(pyscript, barg.AstTextString):
        code = pyscript.value
    else:
        if pyscript not in module.definitions:
            raise barg.BadGrammarError(f"variable '{pyscript}' is not defined")
        defn = module.definitions[pyscript]
        if not isinstance(defn, barg.AstTextString):
            raise barg.BadGrammarError(
                f"variable '{pyscript}' does not refer to a text string (but has to)"
            )
        code = defn.value
    globs = {"module": module, "x": m, "args": args, "barg": barg}
    exec(code, globs)
    return globs["x"]


# currently not possible because there is no fixed ordering to the fields of a struct, so you cannot reconstruct the original string that was matched.
# since this is only a convenience function anyway (to avoid repetition), it's not a big problem at the moment.
# def builtin_join(module, m):
#     if hasattr(m, "type_"):
#         if m.type_ == barg.GenTyKind.STRUCT:
#             return "".join(
#                 builtin_join(module, getattr(m, field))
#                 for field in dir(m)
#                 if not (
#                     field[0] == "_"
#                     and field[1:].isdigit()
#                     or field[-1] == "_"
#                 )
#             )
#         elif m.type_ == barg.GenTyKind.ENUM:
#             return builtin_join(module, m.value)
#         else:
#             raise barg.InternalError(
#                 "invalid value of 'type_' encountered in join builtin"
#             )
#     elif isinstance(m, list):
#         return "".join(builtin_join(module, item) for item in m)
#     else:
#         try:
#             return str(m)
#         except ValueError:
#             raise barg.BadGrammarError(
#                 f"Cannot join submatch of type '{type(m)}' with value '{m}'"
#             )


def insert_transform(transforms: Dict[str, Any], full_name: str, function: Callable):
    ns = transforms
    path = full_name.split(".")
    for name in path[:-1]:
        ns = ns.setdefault(name, {})
    ns[path[-1]] = function


def get_transform(transforms: Dict[str, Any], full_name: str) -> Callable:
    path = full_name.split(".")
    transform = transforms
    for name in path:
        if name not in transform:
            raise barg.BadGrammarError(f"usage of unknown transform '{full_name}'")
        transform = transform[name]
    if not callable(transform):
        raise barg.InternalError(
            f"transform {full_name} is a namespace, not a function"
        )
    return transform


def insert_all_builtins(transforms):
    insert_transform(transforms, TAKE_BUILTIN_NAME, builtin_take)
    insert_transform(transforms, "builtin.int", builtin_int)
    insert_transform(transforms, "builtin.float", builtin_float)
    insert_transform(transforms, "builtin.delete", builtin_delete)
    insert_transform(transforms, "builtin.mark", builtin_mark)
    insert_transform(transforms, "builtin.filter", builtin_filter)
    insert_transform(transforms, "builtin.pyexpr", builtin_pyexpr)
    insert_transform(transforms, "builtin.pyscript", builtin_pyscript)
    # insert_transform(transforms, "builtin.join", builtin_join)


TAKE_BUILTIN_NAME = "builtin.take"
BARG_EXEC_BUILTINS = {}
insert_all_builtins(BARG_EXEC_BUILTINS)

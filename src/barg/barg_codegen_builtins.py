# NOTE: this code will be C-header-style inserted into the generated parsers. "Unused" imports aren't actually unused.
import regex
from enum import Enum
from typing import Optional, Any, Dict, Callable

_TRANSFORMS_ = {}


def _wrap_in_parsable_type_(func):
    class Ty:
        @staticmethod
        def parse(text: str):
            return next(func(text))

    return Ty


class _TextString_:
    def __init__(self, value: str):
        self.value = value


class BadGrammarError(Exception):
    def __init__(self, msg: str, line: Optional[int] = None):
        super().__init__(line, msg)


# It is strongly recommended to pass `None` as the value for parameter `line`.
class InternalError(Exception):
    def __init__(self, msg: str, line: Optional[int] = None):
        super().__init__(line, msg)


class GenTyKind(Enum):
    STRUCT = 0
    ENUM = 1


# NOTE: '|Any ' in field so it can be called in non-type-safe way from other places
def _builtin_take_(m, field: Optional[str] | Any = None):
    if field is not None and not isinstance(field, str):
        raise BadGrammarError(
            f"the field parameter of the take builtin must be an identifier or unprovided, not {type(field)}",
        )
    if not hasattr(m, "type_"):
        raise InternalError("can only apply barg_take builtin to struct or enum type")
    if m.type_ == GenTyKind.STRUCT:
        if not field:
            raise BadGrammarError(
                "if take is applied to a struct, it takes a field parameter in the form $take(expr, fieldname123) where fieldname123 (without quotes) is the fieldname",
            )
        return getattr(m, field)
    elif m.type_ == GenTyKind.ENUM:
        return getattr(m, "value")
    else:
        raise InternalError("invalid value of 'type_' encountered in take")


def _builtin_int_(m):
    if not isinstance(m, str):
        raise BadGrammarError(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}",
        )
    return int(m)


def _builtin_float_(m):
    if not isinstance(m, str):
        raise BadGrammarError(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}",
        )
    return float(m)


def _builtin_delete_(m, field: Optional[str] | Any = None):
    if field is not None and not isinstance(field, str):
        raise BadGrammarError(
            f"the field parameter of the delete builtin must be an identifier or unprovided, not {type(field)}",
        )
    if not hasattr(m, "type_"):
        raise BadGrammarError("can only apply barg_take builtin to struct or enum type")
    if m.type_ == GenTyKind.STRUCT and field:
        setattr(m, field, None)
    elif m.type_ == GenTyKind.ENUM:
        if field and m.tag == field or not field:
            m.value = None
    else:
        raise InternalError("invalid value of 'type_' encountered in delete")
    return m


def _builtin_mark_(m, mark: str):
    if not mark or not isinstance(mark, str):
        raise BadGrammarError(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    setattr(m, f"mark_{mark}_", None)
    return m


def _builtin_filter_(m, mark: str):
    if not mark or not isinstance(mark, str):
        raise BadGrammarError(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    if not isinstance(m, list):
        raise BadGrammarError(f"filter builtin applied to non-list object {m}")
    return list(filter(lambda item: hasattr(item, f"mark_{mark}_"), m))


def _builtin_pyexpr_(m, pyexpr: "_TextString_ | str | Any", *args):
    if not pyexpr or not isinstance(pyexpr, (_TextString_, str)):
        raise BadGrammarError(
            f"pyexpr '{pyexpr}' is invalid, pyexpr must be a non-empty text string or variable"
        )
    if isinstance(pyexpr, _TextString_):
        code = pyexpr.value
    else:
        if pyexpr not in globals():
            raise BadGrammarError(f"variable '{pyexpr}' is not defined")
        defn = globals()[pyexpr]
        if not isinstance(defn, _TextString_):
            raise BadGrammarError(
                f"variable '{pyexpr}' does not refer to a text string (but has to)"
            )
        code = defn.value
    return eval(code, {"x": m, "args": args})


def _builtin_pyscript_(m, pyscript: "_TextString_ | str | Any", *args):
    if not pyscript or not isinstance(pyscript, (_TextString_, str)):
        raise BadGrammarError(
            f"pyscript '{pyscript}' is invalid, pyscript must be a non-empty text string or variable"
        )
    if isinstance(pyscript, _TextString_):
        code = pyscript.value
    else:
        if pyscript not in globals():
            raise BadGrammarError(f"variable '{pyscript}' is not defined")
        defn = globals()[pyscript]
        if not isinstance(defn, _TextString_):
            raise BadGrammarError(
                f"variable '{pyscript}' does not refer to a text string (but has to)"
            )
        code = defn.value
    globs = {"x": m, "args": args}
    exec(code, globs)
    return globs["x"]


def _insert_transform_(transforms: Dict[str, Any], full_name: str, function: Callable):
    ns = transforms
    path = full_name.split(".")
    for name in path[:-1]:
        ns = ns.setdefault(name, {})
    ns[path[-1]] = function


def _get_transform_(transforms: Dict[str, Any], full_name: str) -> Callable:
    path = full_name.split(".")
    transform = transforms
    for name in path:
        if name not in transform:
            raise BadGrammarError(f"usage of unknown transform '{full_name}'")
        transform = transform[name]
    if not callable(transform):
        raise InternalError(f"transform {full_name} is a namespace, not a function")
    return transform


def _insert_all_builtins_(transforms):
    _insert_transform_(transforms, "builtin.take", _builtin_take_)
    _insert_transform_(transforms, "builtin.int", _builtin_int_)
    _insert_transform_(transforms, "builtin.float", _builtin_float_)
    _insert_transform_(transforms, "builtin.delete", _builtin_delete_)
    _insert_transform_(transforms, "builtin.mark", _builtin_mark_)
    _insert_transform_(transforms, "builtin.filter", _builtin_filter_)
    _insert_transform_(transforms, "builtin.pyexpr", _builtin_pyexpr_)
    _insert_transform_(transforms, "builtin.pyscript", _builtin_pyscript_)


_insert_all_builtins_(_TRANSFORMS_)

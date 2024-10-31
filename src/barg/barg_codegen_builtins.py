# NOTE: this code will be C-header-style inserted into the generated parsers. "Unused" imports aren't actually unused.
import regex as _regex_
from enum import Enum as _Enum_
from typing import (
    Optional as _Optional_,
    Any as _Any_,
    Dict as _Dict_,
    Callable as _Callable_,
)

_TRANSFORMS_ = {}


def _wrap_in_parsable_type_(func):
    class Ty:
        @staticmethod
        def parse(text: str):
            return next(func(text))[0]

    return Ty


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


class _GenTyKind_(_Enum_):
    STRUCT = 0
    ENUM = 1


# NOTE: '|Any ' in field so it can be called in non-type-safe way from other places
def _builtin_take_(text: str, ncons: int, m, field: _Optional_[str] | _Any_ = None):
    if field is not None and not isinstance(field, str):
        raise _BadGrammarError_(
            f"the field parameter of the take builtin must be an identifier or unprovided, not {type(field)}",
        )
    if not hasattr(m, "type_"):
        raise _InternalError_("can only apply barg_take builtin to struct or enum type")
    if m.type_ == _GenTyKind_.STRUCT:
        if not field:
            raise _BadGrammarError_(
                "if take is applied to a struct, it takes a field parameter in the form $take(expr, fieldname123) where fieldname123 (without quotes) is the fieldname",
            )
        return getattr(m, field), ncons
    elif m.type_ == _GenTyKind_.ENUM:
        return getattr(m, "value"), ncons
    else:
        raise _InternalError_("invalid value of 'type_' encountered in take")


def _builtin_int_(text: str, ncons: int, m):
    if not isinstance(m, str):
        raise _BadGrammarError_(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}",
        )
    return int(m), ncons


def _builtin_float_(text: str, ncons: int, m):
    if not isinstance(m, str):
        raise _BadGrammarError_(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}",
        )
    return float(m), ncons


def _builtin_delete_(text: str, ncons: int, m, field: _Optional_[str] | _Any_ = None):
    if field is not None and not isinstance(field, str):
        raise _BadGrammarError_(
            f"the field parameter of the delete builtin must be an identifier or unprovided, not {type(field)}",
        )
    if not hasattr(m, "type_"):
        raise _BadGrammarError_(
            "can only apply barg_take builtin to struct or enum type"
        )
    if m.type_ == _GenTyKind_.STRUCT and field:
        setattr(m, field, None)
    elif m.type_ == _GenTyKind_.ENUM:
        if field and m.tag == field or not field:
            m.value = None
    else:
        raise _InternalError_("invalid value of 'type_' encountered in delete")
    return m, ncons


def _builtin_mark_(text: str, ncons: int, m, mark: str):
    if not mark or not isinstance(mark, str):
        raise _BadGrammarError_(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    setattr(m, f"mark_{mark}_", None)
    return m, ncons


def _builtin_filter_(text: str, ncons: int, m, mark: str):
    if not mark or not isinstance(mark, str):
        raise _BadGrammarError_(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    if not isinstance(m, list):
        raise _BadGrammarError_(f"filter builtin applied to non-list object {m}")
    return list(filter(lambda item: hasattr(item, f"mark_{mark}_"), m)), ncons


def _builtin_pyexpr_(
    text: str, ncons: int, m, pyexpr: "_TextString_ | str | _Any_", *args
):
    if not pyexpr or not isinstance(pyexpr, (_TextString_, str)):
        raise _BadGrammarError_(
            f"pyexpr '{pyexpr}' is invalid, pyexpr must be a non-empty text string or variable"
        )
    if isinstance(pyexpr, _TextString_):
        code = pyexpr.value
    else:
        if pyexpr not in globals():
            raise _BadGrammarError_(f"variable '{pyexpr}' is not defined")
        defn = globals()[pyexpr]
        if not isinstance(defn, _TextString_):
            raise _BadGrammarError_(
                f"variable '{pyexpr}' does not refer to a text string (but has to)"
            )
        code = defn.value
    globs = {"x": m, "args": args, "ncons": ncons, "text": text}
    return eval(code, globs), globs["ncons"]


def _builtin_pyscript_(
    text: str, ncons: int, m, pyscript: "_TextString_ | str | _Any_", *args
):
    if not pyscript or not isinstance(pyscript, (_TextString_, str)):
        raise _BadGrammarError_(
            f"pyscript '{pyscript}' is invalid, pyscript must be a non-empty text string or variable"
        )
    if isinstance(pyscript, _TextString_):
        code = pyscript.value
    else:
        if pyscript not in globals():
            raise _BadGrammarError_(f"variable '{pyscript}' is not defined")
        defn = globals()[pyscript]
        if not isinstance(defn, _TextString_):
            raise _BadGrammarError_(
                f"variable '{pyscript}' does not refer to a text string (but has to)"
            )
        code = defn.value
    globs = {"x": m, "args": args, "ncons": ncons, "text": text}
    exec(code, globs)
    return globs["x"], globs["ncons"]


def _insert_transform_(
    transforms: _Dict_[str, _Any_], full_name: str, function: _Callable_
):
    ns = transforms
    path = full_name.split(".")
    for name in path[:-1]:
        ns = ns.setdefault(name, {})
    ns[path[-1]] = function


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

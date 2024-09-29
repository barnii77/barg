# NOTE: this code will be C-header-style inserted into the generated parsers. "Unused" imports aren't actually unused.
import regex as _regex_
from enum import Enum as _Enum_
from typing import Optional as _Optional_, Any as _Any_, Dict as _Dict_, Callable as _Callable_

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
def _builtin_take_(m, field: _Optional_[str] | _Any_ = None):
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
        return getattr(m, field)
    elif m.type_ == _GenTyKind_.ENUM:
        return getattr(m, "value")
    else:
        raise _InternalError_("invalid value of 'type_' encountered in take")


def _builtin_int_(m):
    if not isinstance(m, str):
        raise _BadGrammarError_(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}",
        )
    return int(m)


def _builtin_float_(m):
    if not isinstance(m, str):
        raise _BadGrammarError_(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}",
        )
    return float(m)


def _builtin_delete_(m, field: _Optional_[str] | _Any_ = None):
    if field is not None and not isinstance(field, str):
        raise _BadGrammarError_(
            f"the field parameter of the delete builtin must be an identifier or unprovided, not {type(field)}",
        )
    if not hasattr(m, "type_"):
        raise _BadGrammarError_("can only apply barg_take builtin to struct or enum type")
    if m.type_ == _GenTyKind_.STRUCT and field:
        setattr(m, field, None)
    elif m.type_ == _GenTyKind_.ENUM:
        if field and m.tag == field or not field:
            m.value = None
    else:
        raise _InternalError_("invalid value of 'type_' encountered in delete")
    return m


def _builtin_mark_(m, mark: str):
    if not mark or not isinstance(mark, str):
        raise _BadGrammarError_(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    setattr(m, f"mark_{mark}_", None)
    return m


def _builtin_filter_(m, mark: str):
    if not mark or not isinstance(mark, str):
        raise _BadGrammarError_(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    if not isinstance(m, list):
        raise _BadGrammarError_(f"filter builtin applied to non-list object {m}")
    return list(filter(lambda item: hasattr(item, f"mark_{mark}_"), m))


def _builtin_pyexpr_(m, pyexpr: "_TextString_ | str | _Any_", *args):
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
    return eval(code, {"x": m, "args": args})


def _builtin_pyscript_(m, pyscript: "_TextString_ | str | _Any_", *args):
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
    globs = {"x": m, "args": args}
    exec(code, globs)
    return globs["x"]


def _insert_transform_(transforms: _Dict_[str, _Any_], full_name: str, function: _Callable_):
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


# generated from barg grammar line 8
# struct matcher
def _match0_(text: str):
    for local_m0, local_ncons0 in _match1_(text):
        yield _Ty0_(local_m0), local_ncons0


# generated from barg grammar line 9
# transform matcher
def _match1_(text: str):
    transform = _get_transform_(_TRANSFORMS_, r"builtin.int")
    for m, ncons in _match2_(text):
        yield transform(m, ), ncons


# generated from barg grammar line 9
# regex matcher
def _match2_(text: str):
    for m in _pat2_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 12
# struct matcher
def _match3_(text: str):
    for local_m0, local_ncons0 in _match4_(text):
        yield _Ty3_(local_m0), local_ncons0


# generated from barg grammar line 13
# regex matcher
def _match4_(text: str):
    for m in _pat4_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 16
# transform matcher
def _match5_(text: str):
    transform = _get_transform_(_TRANSFORMS_, r"builtin.take")
    for m, ncons in _match6_(text):
        yield transform(m, ), ncons


# generated from barg grammar line 16
# enum matcher
def _match6_(text: str):
    for m, ncons in _match0_(text):
        yield _Ty6_('_0', m), ncons
    for m, ncons in _match3_(text):
        yield _Ty6_('_1', m), ncons
    for m, ncons in _match7_(text):
        yield _Ty6_('_2', m), ncons


# generated from barg grammar line 16
# struct matcher
def _match7_(text: str):
    for local_m0, local_ncons0 in _match34_(text):
        for local_m1, local_ncons1 in _match9_(text[local_ncons0:]):
            for local_m2, local_ncons2 in _match8_(text[local_ncons0 + local_ncons1:]):
                yield _Ty7_(local_m0, local_m1, local_m2), local_ncons0 + local_ncons1 + local_ncons2


# generated from barg grammar line 16
# regex matcher
def _match8_(text: str):
    for m in _pat8_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 67
# struct matcher
def _match9_(text: str):
    for local_m0, local_ncons0 in _match31_(text):
        for local_m1, local_ncons1 in _match10_(text[local_ncons0:]):
            yield _Ty9_(local_m0, local_m1), local_ncons0 + local_ncons1


# generated from barg grammar line 65
# transform matcher
def _match10_(text: str):
    transform = _get_transform_(_TRANSFORMS_, r"builtin.take")
    for m, ncons in _match11_(text):
        yield transform(m, ), ncons


# generated from barg grammar line 65
# enum matcher
def _match11_(text: str):
    for m, ncons in _match12_(text):
        yield _Ty11_('_0', m), ncons
    for m, ncons in _match23_(text):
        yield _Ty11_('_1', m), ncons
    for m, ncons in _match5_(text):
        yield _Ty11_('_2', m), ncons


# generated from barg grammar line 61
# transform matcher
def _match12_(text: str):
    transform = _get_transform_(_TRANSFORMS_, r"builtin.take")
    for m, ncons in _match13_(text):
        yield transform(m, ), ncons


# generated from barg grammar line 61
# enum matcher
def _match13_(text: str):
    for m, ncons in _match14_(text):
        yield _Ty13_('_0', m), ncons
    for m, ncons in _match19_(text):
        yield _Ty13_('_1', m), ncons
    for m, ncons in _match21_(text):
        yield _Ty13_('_2', m), ncons


# generated from barg grammar line 37
# struct matcher
def _match14_(text: str):
    for local_m0, local_ncons0 in _match5_(text):
        for local_m1, local_ncons1 in _match17_(text[local_ncons0:]):
            for local_m2, local_ncons2 in _match18_(text[local_ncons0 + local_ncons1:]):
                for local_m3, local_ncons3 in _match17_(text[local_ncons0 + local_ncons1 + local_ncons2:]):
                    for local_m4, local_ncons4 in _match15_(text[local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3:]):
                        yield _Ty14_(local_m0, local_m1, local_m2, local_m3, local_m4), local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3 + local_ncons4


# generated from barg grammar line 43
# transform matcher
def _match15_(text: str):
    transform = _get_transform_(_TRANSFORMS_, r"builtin.take")
    for m, ncons in _match16_(text):
        yield transform(m, ), ncons


# generated from barg grammar line 43
# enum matcher
def _match16_(text: str):
    for m, ncons in _match5_(text):
        yield _Ty16_('_0', m), ncons
    for m, ncons in _match12_(text):
        yield _Ty16_('_1', m), ncons


# generated from barg grammar line 41
# regex matcher
def _match17_(text: str):
    for m in _pat17_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 40
# regex matcher
def _match18_(text: str):
    for m in _pat18_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 45
# struct matcher
def _match19_(text: str):
    for local_m0, local_ncons0 in _match5_(text):
        for local_m1, local_ncons1 in _match17_(text[local_ncons0:]):
            for local_m2, local_ncons2 in _match20_(text[local_ncons0 + local_ncons1:]):
                for local_m3, local_ncons3 in _match17_(text[local_ncons0 + local_ncons1 + local_ncons2:]):
                    for local_m4, local_ncons4 in _match15_(text[local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3:]):
                        yield _Ty19_(local_m0, local_m1, local_m2, local_m3, local_m4), local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3 + local_ncons4


# generated from barg grammar line 48
# regex matcher
def _match20_(text: str):
    for m in _pat20_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 53
# struct matcher
def _match21_(text: str):
    for local_m0, local_ncons0 in _match5_(text):
        for local_m1, local_ncons1 in _match17_(text[local_ncons0:]):
            for local_m2, local_ncons2 in _match22_(text[local_ncons0 + local_ncons1:]):
                for local_m3, local_ncons3 in _match17_(text[local_ncons0 + local_ncons1 + local_ncons2:]):
                    for local_m4, local_ncons4 in _match15_(text[local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3:]):
                        yield _Ty21_(local_m0, local_m1, local_m2, local_m3, local_m4), local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3 + local_ncons4


# generated from barg grammar line 56
# regex matcher
def _match22_(text: str):
    for m in _pat22_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 63
# transform matcher
def _match23_(text: str):
    transform = _get_transform_(_TRANSFORMS_, r"builtin.take")
    for m, ncons in _match24_(text):
        yield transform(m, ), ncons


# generated from barg grammar line 63
# enum matcher
def _match24_(text: str):
    for m, ncons in _match25_(text):
        yield _Ty24_('_0', m), ncons
    for m, ncons in _match29_(text):
        yield _Ty24_('_1', m), ncons


# generated from barg grammar line 21
# struct matcher
def _match25_(text: str):
    for local_m0, local_ncons0 in _match27_(text):
        for local_m1, local_ncons1 in _match17_(text[local_ncons0:]):
            for local_m2, local_ncons2 in _match26_(text[local_ncons0 + local_ncons1:]):
                for local_m3, local_ncons3 in _match17_(text[local_ncons0 + local_ncons1 + local_ncons2:]):
                    for local_m4, local_ncons4 in _match10_(text[local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3:]):
                        yield _Ty25_(local_m0, local_m1, local_m2, local_m3, local_m4), local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3 + local_ncons4


# generated from barg grammar line 24
# regex matcher
def _match26_(text: str):
    for m in _pat26_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 19
# transform matcher
def _match27_(text: str):
    transform = _get_transform_(_TRANSFORMS_, r"builtin.take")
    for m, ncons in _match28_(text):
        yield transform(m, ), ncons


# generated from barg grammar line 19
# enum matcher
def _match28_(text: str):
    for m, ncons in _match5_(text):
        yield _Ty28_('_0', m), ncons
    for m, ncons in _match12_(text):
        yield _Ty28_('_1', m), ncons


# generated from barg grammar line 29
# struct matcher
def _match29_(text: str):
    for local_m0, local_ncons0 in _match27_(text):
        for local_m1, local_ncons1 in _match17_(text[local_ncons0:]):
            for local_m2, local_ncons2 in _match30_(text[local_ncons0 + local_ncons1:]):
                for local_m3, local_ncons3 in _match17_(text[local_ncons0 + local_ncons1 + local_ncons2:]):
                    for local_m4, local_ncons4 in _match10_(text[local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3:]):
                        yield _Ty29_(local_m0, local_m1, local_m2, local_m3, local_m4), local_ncons0 + local_ncons1 + local_ncons2 + local_ncons3 + local_ncons4


# generated from barg grammar line 32
# regex matcher
def _match30_(text: str):
    for m in _pat30_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 67
# greedy list matcher
def _match31_(text: str, matched_exprs=None):
    if matched_exprs is None:
        matched_exprs = []
    if len(matched_exprs) >= 2:
        return
    for local_m, local_ncons in _match32_(text):
        for m, ncons in _match31_(
            text[local_ncons:], matched_exprs + [local_m]
        ):
            yield m, local_ncons + ncons

    if 0 <= len(matched_exprs):
        yield matched_exprs, 0



# generated from barg grammar line 67
# struct matcher
def _match32_(text: str):
    for local_m0, local_ncons0 in _match3_(text):
        for local_m1, local_ncons1 in _match33_(text[local_ncons0:]):
            yield _Ty32_(local_m0, local_m1), local_ncons0 + local_ncons1


# generated from barg grammar line 67
# regex matcher
def _match33_(text: str):
    for m in _pat33_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 16
# regex matcher
def _match34_(text: str):
    for m in _pat34_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 69
# struct matcher
def _match35_(text: str):
    for local_m0, local_ncons0 in _match9_(text):
        for local_m1, local_ncons1 in _match36_(text[local_ncons0:]):
            yield _Ty35_(local_m0, local_m1), local_ncons0 + local_ncons1


# generated from barg grammar line 69
# regex matcher
def _match36_(text: str):
    for m in _pat36_.finditer(text, overlapped=True):
        yield m.group(0), m.end(0)


# generated from barg grammar line 70
# greedy list matcher
def _match37_(text: str, matched_exprs=None):
    if matched_exprs is None:
        matched_exprs = []

    for local_m, local_ncons in _match35_(text):
        for m, ncons in _match37_(
            text[local_ncons:], matched_exprs + [local_m]
        ):
            yield m, local_ncons + ncons

    if 0 <= len(matched_exprs):
        yield matched_exprs, 0



# generated from barg grammar line 8
# struct type
class _Ty0_:
    def __init__(self, value):
        self.type_ = _GenTyKind_.STRUCT
        self.value = value

    @staticmethod
    def parse(text: str):
        return next(_match0_(text))[0]


# generated from barg grammar line 12
# struct type
class _Ty3_:
    def __init__(self, name):
        self.type_ = _GenTyKind_.STRUCT
        self.name = name

    @staticmethod
    def parse(text: str):
        return next(_match3_(text))[0]


# generated from barg grammar line 16
# enum type
class _Ty6_:
    def __init__(self, tag: str, value):
        self.type_ = _GenTyKind_.ENUM
        self.tag = tag
        self.value = value

    @staticmethod
    def parse(text: str):
        return next(_match6_(text))[0]


# generated from barg grammar line 16
# struct type
class _Ty7_:
    def __init__(self, _0, _1, _2):
        self.type_ = _GenTyKind_.STRUCT
        self._0 = _0
        self._1 = _1
        self._2 = _2

    @staticmethod
    def parse(text: str):
        return next(_match7_(text))[0]


# generated from barg grammar line 67
# struct type
class _Ty9_:
    def __init__(self, _0, _1):
        self.type_ = _GenTyKind_.STRUCT
        self._0 = _0
        self._1 = _1

    @staticmethod
    def parse(text: str):
        return next(_match9_(text))[0]


# generated from barg grammar line 65
# enum type
class _Ty11_:
    def __init__(self, tag: str, value):
        self.type_ = _GenTyKind_.ENUM
        self.tag = tag
        self.value = value

    @staticmethod
    def parse(text: str):
        return next(_match11_(text))[0]


# generated from barg grammar line 61
# enum type
class _Ty13_:
    def __init__(self, tag: str, value):
        self.type_ = _GenTyKind_.ENUM
        self.tag = tag
        self.value = value

    @staticmethod
    def parse(text: str):
        return next(_match13_(text))[0]


# generated from barg grammar line 37
# struct type
class _Ty14_:
    def __init__(self, a, _0, op, _1, b):
        self.type_ = _GenTyKind_.STRUCT
        self.a = a
        self._0 = _0
        self.op = op
        self._1 = _1
        self.b = b

    @staticmethod
    def parse(text: str):
        return next(_match14_(text))[0]


# generated from barg grammar line 43
# enum type
class _Ty16_:
    def __init__(self, tag: str, value):
        self.type_ = _GenTyKind_.ENUM
        self.tag = tag
        self.value = value

    @staticmethod
    def parse(text: str):
        return next(_match16_(text))[0]


# generated from barg grammar line 45
# struct type
class _Ty19_:
    def __init__(self, a, _0, op, _1, b):
        self.type_ = _GenTyKind_.STRUCT
        self.a = a
        self._0 = _0
        self.op = op
        self._1 = _1
        self.b = b

    @staticmethod
    def parse(text: str):
        return next(_match19_(text))[0]


# generated from barg grammar line 53
# struct type
class _Ty21_:
    def __init__(self, a, _0, op, _1, b):
        self.type_ = _GenTyKind_.STRUCT
        self.a = a
        self._0 = _0
        self.op = op
        self._1 = _1
        self.b = b

    @staticmethod
    def parse(text: str):
        return next(_match21_(text))[0]


# generated from barg grammar line 63
# enum type
class _Ty24_:
    def __init__(self, tag: str, value):
        self.type_ = _GenTyKind_.ENUM
        self.tag = tag
        self.value = value

    @staticmethod
    def parse(text: str):
        return next(_match24_(text))[0]


# generated from barg grammar line 21
# struct type
class _Ty25_:
    def __init__(self, a, _0, op, _1, b):
        self.type_ = _GenTyKind_.STRUCT
        self.a = a
        self._0 = _0
        self.op = op
        self._1 = _1
        self.b = b

    @staticmethod
    def parse(text: str):
        return next(_match25_(text))[0]


# generated from barg grammar line 19
# enum type
class _Ty28_:
    def __init__(self, tag: str, value):
        self.type_ = _GenTyKind_.ENUM
        self.tag = tag
        self.value = value

    @staticmethod
    def parse(text: str):
        return next(_match28_(text))[0]


# generated from barg grammar line 29
# struct type
class _Ty29_:
    def __init__(self, a, _0, op, _1, b):
        self.type_ = _GenTyKind_.STRUCT
        self.a = a
        self._0 = _0
        self.op = op
        self._1 = _1
        self.b = b

    @staticmethod
    def parse(text: str):
        return next(_match29_(text))[0]


# generated from barg grammar line 67
# struct type
class _Ty32_:
    def __init__(self, _0, _1):
        self.type_ = _GenTyKind_.STRUCT
        self._0 = _0
        self._1 = _1

    @staticmethod
    def parse(text: str):
        return next(_match32_(text))[0]


# generated from barg grammar line 69
# struct type
class _Ty35_:
    def __init__(self, _0, _1):
        self.type_ = _GenTyKind_.STRUCT
        self._0 = _0
        self._1 = _1

    @staticmethod
    def parse(text: str):
        return next(_match35_(text))[0]


_pat2_ = _regex_.compile(r"""^\d+""")
Int = _Ty0_
_pat4_ = _regex_.compile(r"""^[a-zA-Z_][a-zA-Z_0-9]*""")
Var = _Ty3_
_pat8_ = _regex_.compile(r"""^\)""")
_pat17_ = _regex_.compile(r"""^\s*""")
_pat18_ = _regex_.compile(r"""^\*""")
_pat20_ = _regex_.compile(r"""^/""")
_pat22_ = _regex_.compile(r"""^%""")
_pat26_ = _regex_.compile(r"""^\+""")
_pat30_ = _regex_.compile(r"""^-""")
_pat33_ = _regex_.compile(r"""^\s*:=\s*""")
_pat34_ = _regex_.compile(r"""^\(""")
Term = _wrap_in_parsable_type_(_match5_)
PointOpTerm = _wrap_in_parsable_type_(_match5_)
LineOpTerm = _wrap_in_parsable_type_(_match27_)
AddOp = _Ty25_
SubOp = _Ty29_
MulOp = _Ty14_
DivOp = _Ty19_
ModOp = _Ty21_
PointOp = _wrap_in_parsable_type_(_match12_)
LineOp = _wrap_in_parsable_type_(_match23_)
Expr = _wrap_in_parsable_type_(_match10_)
AssignableExpr = _Ty9_
_pat36_ = _regex_.compile(r"""^\s*\n\s*""")
Statement = _Ty35_
Toplevel = _wrap_in_parsable_type_(_match37_)
TEXT = """\
a := 4
x := 2 * 3 + 4
y := (z := x * 4 + 5) / x * a
"""
parsed = Toplevel.parse(TEXT)
input()

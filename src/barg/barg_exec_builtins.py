import barg
from typing import Optional, Any, Dict, Callable


# NOTE: '|Any ' in field so it can be called in non-type-safe way from other places
def builtin_take(module, m, field: Optional[str] | Any = None):
    if field is not None and not isinstance(field, str):
        raise barg.BadGrammarError(
            f"the field parameter of the take builtin must be an identifier or unprovided, not {type(field)}"
        )
    if not hasattr(m, "type_"):
        raise barg.InternalError(
            "can only apply barg_take builtin to struct or enum type"
        )
    if m.type_ == barg.GenTyKind.STRUCT:
        if not field:
            raise barg.BadGrammarError(
                "if take is applied to a struct, it takes a field parameter in the form $take(expr, fieldname123) where fieldname123 (without quotes) is the fieldname"
            )
        return getattr(m, field)
    elif m.type_ == barg.GenTyKind.ENUM:
        return getattr(m, "value")
    else:
        raise barg.InternalError("invalid value of 'type_' encountered in take")


def builtin_int(module, m):
    if not isinstance(m, str):
        raise barg.BadGrammarError(
            f"the match parameter of the int builtin must be a string match, not type {type(m)}"
        )
    return int(m)


def builtin_delete(module, m, field: Optional[str] | Any = None):
    if field is not None and not isinstance(field, str):
        raise barg.BadGrammarError(
            f"the field parameter of the delete builtin must be an identifier or unprovided, not {type(field)}"
        )
    if not hasattr(m, "type_"):
        raise barg.InternalError(
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
    setattr(m, f"_mark_{mark}", None)
    return m


def builtin_filter(module, m, mark: str):
    if not mark or not isinstance(mark, str):
        raise barg.BadGrammarError(
            f"mark '{mark}' is invalid, mark must be a non-empty string"
        )
    if not isinstance(m, list):
        raise barg.BadGrammarError(f"filter builtin applied to non-list object {m}")
    return list(filter(lambda item: hasattr(item, f"_mark_{mark}"), m))


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
    insert_transform(transforms, "builtin.delete", builtin_delete)
    insert_transform(transforms, "builtin.mark", builtin_mark)
    insert_transform(transforms, "builtin.filter", builtin_filter)


TAKE_BUILTIN_NAME = "builtin.take"
BARG_EXEC_BUILTINS = {}
insert_all_builtins(BARG_EXEC_BUILTINS)

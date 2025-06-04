"""
This module provides a decorator and a function for automatically adding property getters and setters that implement
value expiration. This makes it possible to define attributes whose values expire at a given `timedelta` after being
set. Accessing an attribute whose value has expired returns the sentinel value `Expired`. Here is an example:

    import time

    from aggregator.model.lifetimes import lifetimes, expires, Expired

    @lifetimes
    class VehicleState:
        position: tuple[float, float] | Expired = expires(minutes=1)

    vs = VehicleState()
    vs.position = (0, 0)  # this value will expire one minute from now
    print(vs.position)    # prints (0, 0)
    time.sleep(60)
    print(vs.position)    # prints Expired
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import time
import types
from typing import Any, cast


class _ExpiredType(type):
    def __repr__(self) -> str:
        return "Expired"

    def __str__(self) -> str:
        return "Expired"


class Expired(metaclass=_ExpiredType):
    """
    Sentinel value returned when a property's value has expired.
    """


def lifetimes(cls: type) -> type:
    """
    A decorator that adds property getters and setters that implement expiration of properties' values.
    """
    # Add a class attribute to store the field definitions.
    cls.__lifetimes_fields__ = {}

    # Find all fields that are marked as expiring, validate them, and set up getters and setters.
    for name, default in list(cls.__dict__.items()):
        # We're only interested in class variables whose default values were set by `expires`.
        if not isinstance(default, _Field):
            continue

        # Verify the field is annotated and its annotation is ... | Expired.
        type_ann = cls.__annotations__[name]
        if isinstance(type_ann, types.UnionType):
            if Expired not in type_ann.__args__:
                raise TypeError(f"field {name} must be a union that includes Expired")
        elif type_ann == Expired:
            raise TypeError(f"field {name} is annotated `Expired` but no other types, making it useless")
        else:
            raise TypeError(f"field {name} must be a union that includes Expired")

        # Store the field definition and install a getter and a setter.
        cls.__lifetimes_fields__[name] = default
        setattr(cls, name, property(_getter(name), _setter(name)))

    return cls


def expires[T](days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0) -> T:  # type: ignore
    """
    This function is used to set the `timedelta` after which a property's value expires. It accepts the same arguments
    as `timedelta`.
    """
    lifetime = _Field(timedelta(days, seconds, microseconds, milliseconds, minutes, hours, weeks))
    # This cast is a lie, but it's necessary to keep the type checker from complaining that a _Field is being assigned
    # to a <some other type> | Expired.
    return cast(T, lifetime)


_FIELDS = "__lifetimes_fields__"
_VALUE = "__lifetimes_value__"
_EXPIRATIONS = "__lifetimes_expirations__"


@dataclass
class _Field:
    """
    Stores a field's definition.
    """

    expires: timedelta


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _expirations(obj: object) -> dict[str, datetime]:
    """
    Retrieves an object's dictionary of expiration times. If the dictionary doesn't exist yet, it is created with all
    values expired.
    """
    try:
        return getattr(obj, _EXPIRATIONS)
    except AttributeError:
        value = dict((name, datetime.min) for name in getattr(obj, _FIELDS).keys())
        setattr(obj, _EXPIRATIONS, value)
        return value


def _getter(name: str) -> Callable[[object], object | Expired]:
    """
    Creates a getter for a property named `name` that returns the property's value if it hasn't expired, or `Expired`
    if it has.
    """

    def get(obj: object) -> object | None:
        if _now() > _expirations(obj)[name]:
            return Expired
        try:
            return getattr(obj, _VALUE + name)
        except AttributeError:
            return None  # TODO: we should make it impossible to get here

    return get


def _setter(name: str) -> Callable[[object, Any], None]:
    """
    Creates a setter for a property named `name` that sets the property's value and refreshes its expiration time.
    """

    def set(obj: object, value: Any) -> None:
        _expirations(obj)[name] = _now() + getattr(obj, _FIELDS)[name].expires
        setattr(obj, _VALUE + name, value)

    return set


@lifetimes
class Foo:
    boo: float
    narf: str | Expired = expires(seconds=1)
    blat: int | Expired = expires(hours=6)


def main():
    foo = Foo()
    foo.narf = "narf!"
    foo.blat = 0
    print(f"{type(foo)} {foo}")
    print(f"{type(foo.narf)} {foo.narf}")
    print(f"{type(foo.blat)} {foo.blat}")
    time.sleep(2)
    print(f"{type(foo.narf)} {foo.narf}")
    print(f"{type(foo.blat)} {foo.blat}")


if __name__ == "__main__":
    main()

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

The use of `Expired` to signal value expiration prevents overloading the meaning of `None` for properties where `None`
is a legitimate value. However, sometimes you don't care about the difference between an expired value and a missing
one. In this case you can use the `sentinel` keyword argument:

    @lifetimes
    class C:
        foo: str | None = expires(seconds=10, sentinel=None)

    c = C()
    c.foo = "hello world"  # this value will expire ten seconds from now
    print(c.foo)           # prints hello world
    time.sleep(10)
    print(c.foo)           # prints None
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import types
from typing import Any, cast


class _ExpiredType(type):
    def __repr__(cls) -> str:
        return "Expired"

    def __str__(cls) -> str:
        return "Expired"


class Expired(metaclass=_ExpiredType):
    """
    Default sentinel value returned when a property's value has expired.
    """


def lifetimes(cls: type) -> type:
    """
    A decorator that adds property getters and setters that implement expiration of properties' values.
    """
    # Add a class attribute to store the field definitions.
    cls.__lifetimes_fields__ = cast(dict[str, _Field], {})

    # Find all fields that are marked as expiring, validate them, and set up getters and setters.
    for name, default in list(cls.__dict__.items()):
        # We're only interested in class variables whose default values were set by `expires`.
        if not isinstance(default, _Field):
            continue

        # Verify the field is annotated and its annotation is a union type that includes the sentinel value.
        type_ann = cls.__annotations__[name]
        sentinel_type = default.sentinel if isinstance(default.sentinel, type) else type(default.sentinel)
        if isinstance(type_ann, types.UnionType):
            if sentinel_type not in type_ann.__args__:
                raise TypeError(f"field {name!r} must have a union type that includes {sentinel_type}")
        elif type_ann == sentinel_type:
            raise TypeError(f"field {name!r} is annotated with the sentinel but no other types, rendering it useless")
        else:
            raise TypeError(f"field {name!r} must have a union type that includes {sentinel_type}")

        # Store the field definition and install a getter and a setter.
        cls.__lifetimes_fields__[name] = default
        setattr(cls, name, property(_make_getter(name, default.sentinel), _make_setter(name)))

    return cls


# pylint: disable=too-many-arguments
def expires[T](
    *,
    days: int | float = 0,
    seconds: int | float = 0,
    microseconds: int | float = 0,
    milliseconds: int | float = 0,
    minutes: int | float = 0,
    hours: int | float = 0,
    weeks: int | float = 0,
    sentinel: Any = Expired,
) -> T:  # type: ignore
    """
    This function is used to configure a field for expiration. It sets the `timedelta` after which the property's value
    expires, accepting the same arguments as `timedelta`. You can also choose a different sentinel value, like `None`
    if you don't care about the difference between an expired value and a missing one.
    """
    lifetime = _Field(timedelta(days, seconds, microseconds, milliseconds, minutes, hours, weeks), sentinel)
    # This cast is a filthy lie, but it's necessary to keep the type checker from complaining that a _Field is being
    # assigned to a <some other type> | <sentinel type>.
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
    sentinel: Any


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


def _make_getter[T](name: str, sentinel: T) -> Callable[[object], object | T]:
    """
    Creates a getter for a property named `name` that returns the property's value if it hasn't expired, or the
    expiration sentinel if it has.
    """

    def getter(obj: object) -> object | None:
        if _now() > _expirations(obj)[name]:
            return sentinel
        try:
            return getattr(obj, _VALUE + name)
        except AttributeError:
            return None  # TODO: we should make it impossible to get here

    return getter


def _make_setter(name: str) -> Callable[[object, Any], None]:
    """
    Creates a setter for a property named `name` that sets the property's value and refreshes its expiration time.
    """

    def setter(obj: object, value: Any) -> None:
        _expirations(obj)[name] = _now() + getattr(obj, _FIELDS)[name].expires
        setattr(obj, _VALUE + name, value)

    return setter

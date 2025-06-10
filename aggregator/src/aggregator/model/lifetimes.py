"""
This module provides an extension to `@dataclass` that makes it possible to define fields whose values expire at a
certain time after being set. Accessing an attribute whose value has expired returns `None`.

    import time

    from aggregator.model.lifetimes import ephemeral_field

    @dataclass
    class VehicleState:
        position: tuple[float, float] | None = ephemeral_field(minutes=1)

    vs = VehicleState()
    vs.position = (0, 0)  # this value will expire one minute from now
    print(vs.position)    # prints (0, 0)
    time.sleep(60)
    print(vs.position)    # prints None

The default value of an ephemeral field is `None`.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, cast


def ephemeral_field[T](  # pylint: disable=too-many-arguments
    *,
    days: int | float = 0,
    seconds: int | float = 0,
    microseconds: int | float = 0,
    milliseconds: int | float = 0,
    minutes: int | float = 0,
    hours: int | float = 0,
    weeks: int | float = 0,
) -> T:  # type: ignore
    return cast(
        T,
        _EphemeralValueDescriptor(
            timedelta(
                days=days,
                seconds=seconds,
                microseconds=microseconds,
                milliseconds=milliseconds,
                minutes=minutes,
                hours=hours,
                weeks=weeks,
            )
        ),
    )


class _EphemeralValueDescriptor:
    def __init__(self, lifetime: timedelta) -> None:
        self._lifetime = lifetime

    # pylint: disable=attribute-defined-outside-init
    def __set_name__(self, _, name: str) -> None:
        self._name = "_" + name
        self._expiration_name = f"_{name}_expiration"

    def __get__(self, obj: object, _):
        if obj is None:
            return None
        expiration = getattr(obj, self._expiration_name, None)
        if expiration is None:
            return None
        if datetime.now(timezone.utc) > expiration:
            setattr(obj, self._expiration_name, None)
            return None
        return getattr(obj, self._name, None)

    def __set__(self, obj: object, value: Any) -> None:
        setattr(obj, self._expiration_name, datetime.now(timezone.utc) + self._lifetime)
        setattr(obj, self._name, value)

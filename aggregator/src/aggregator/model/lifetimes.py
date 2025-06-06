"""
This module provides an extension to `@dataclass` that makes it possible to define fields whose values expire at a
certain time after being set. Accessing an attribute whose value has expired returns `None`. Here is an example:

    import time

    from aggregator.model.lifetimes import lifetimes, expires

    @dataclass
    class VehicleState:
        position: tuple[float, float] | None = limited_lifetime_field(minutes=1)

    vs = VehicleState()
    vs.position = (0, 0)  # this value will expire one minute from now
    print(vs.position)    # prints (0, 0)
    time.sleep(60)
    print(vs.position)    # prints None

The default value of a limited-lifetime field is `None`.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, cast


def limited_lifetime_field[T](
    *, days=0, seconds=0, microseconds=0, milliseconds=0, minutes=0, hours=0, weeks=0
) -> T:  # type: ignore
    return cast(
        T,
        _LimitedLifetimeDescriptor(
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


class _LimitedLifetimeDescriptor:
    def __init__(self, lifetime: timedelta) -> None:
        self._lifetime = lifetime
        self._expiration = None

    def __set_name__(self, _, name: str) -> None:
        self._name = "_" + name

    def __get__(self, obj: object, _):
        if obj is None:
            return None
        if self._expiration is None:
            return None
        if datetime.now(timezone.utc) > self._expiration:
            self._expiration = None
            return None
        return getattr(obj, self._name, None)

    def __set__(self, obj: object, value: Any) -> None:
        self._expiration = datetime.now(timezone.utc) + self._lifetime
        setattr(obj, self._name, value)

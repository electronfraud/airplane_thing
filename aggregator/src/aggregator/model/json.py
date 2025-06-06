"""
Utilities for serializing aggregator data model objects into JSON.
"""

from collections.abc import Callable
import dataclasses
import functools
import json
from typing import Any

from aggregator.model.aircraft import Aircraft
from aggregator.model.icao_address import ICAOAddress
from aggregator.model.position import Position


def _default(obj: Any) -> Any:
    if isinstance(obj, Aircraft):
        return {k: v for k, v in dataclasses.asdict(obj).items() if v is not None}
    if isinstance(obj, ICAOAddress):
        return str(obj)
    if isinstance(obj, Position):
        return {"longitude": obj.longitude, "latitude": obj.latitude}
    raise TypeError(f"object of type {type(obj).__name__!r} is not JSON serializable")


dumps: Callable[[Any], str] = functools.partial(json.dumps, default=_default, allow_nan=False, separators=(",", ":"))

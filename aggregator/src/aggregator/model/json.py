"""
Utilities for serializing aggregator data model objects into JSON. Example:

    aircraft = model.Aircraft(...)
    model.json.dumps([aircraft, ...])

This is equivalent to:

    aircraft = model.Aircraft(...)
    json.dumps([aircraft, ...], default=<private serialization function>, allow_nan=False, separators=(",", ":"))
"""

import dataclasses
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


def dumps(obj: Any) -> str:
    return json.dumps(obj, default=_default, allow_nan=False, separators=(",", ":"))

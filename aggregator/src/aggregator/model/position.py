from dataclasses import dataclass
from typing import Self


@dataclass
class Position:
    """
    A location on the surface of Earth. Technically no datum is specified by this class, but Mode S position data is
    referenced to WGS 84, and that is maintained throughout this entire system.
    """

    longitude: float
    latitude: float

    @classmethod
    def from_lat_lon(cls, position: tuple[float, float]) -> Self:
        return cls(position[1], position[0])

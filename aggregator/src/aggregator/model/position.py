from dataclasses import dataclass
from typing import Self


@dataclass
class Position:
    """
    A location on the surface of Earth, referenced to WGS 84.
    """

    longitude: float
    latitude: float

    @classmethod
    def from_lat_lon(cls, position: tuple[float, float]) -> Self:
        return cls(position[1], position[0])

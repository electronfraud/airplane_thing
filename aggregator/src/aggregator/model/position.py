from dataclasses import dataclass


@dataclass
class Position:
    """
    A location on the surface of Earth, referenced to WGS 84.
    """

    longitude: float
    latitude: float

from dataclasses import dataclass

from aggregator.model.flight import Flight
from aggregator.model.icao_address import ICAOAddress
from aggregator.model.lifetimes import limited_lifetime_field
from aggregator.model.position import Position


@dataclass
class Aircraft:
    """
    Represents an operating aircraft, which may be in flight or on the surface. Each Aircraft object is the result of
    merging data from multiple Mode S/ADS-B messages and (optionally) FAA SWIM flight messages.

    An Aircraft object's properties can change during the life of the object. The correlator retains references to
    Aircraft objects that it manages and updates their properties as new messages arrive. Each property also has an
    expiration policy and will revert to `None` if enough time has passed without new data arriving. Position and
    velocity data expires the fastest, followed by transponder codes (squawks), then callsigns, and lastly ICAO
    addresses, which never expire.
    """

    # fmt:off
    icao_address:   ICAOAddress
    callsign:       str      | None = limited_lifetime_field(hours=1)
    squawk:         str      | None = limited_lifetime_field(minutes=30)

    altitude:       int      | None = limited_lifetime_field(seconds=10)
    position:       Position | None = limited_lifetime_field(seconds=10)
    ground_speed:   int      | None = limited_lifetime_field(seconds=10)
    track:          float    | None = limited_lifetime_field(seconds=10)
    vertical_speed: int      | None = limited_lifetime_field(seconds=10)

    flight:         Flight   | None = None
    # fmt:on

    def __post_init__(self) -> None:
        if self.callsign is None and self.flight is not None:
            self.callsign = self.flight.callsign

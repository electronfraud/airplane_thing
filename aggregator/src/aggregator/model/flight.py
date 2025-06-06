from dataclasses import dataclass

from aggregator.model.icao_address import ICAOAddress


@dataclass
class Flight:
    """
    Represents a flight, i.e. a specific operation being carried out by an aircraft. These are produced by SWIMIngester
    and correspond to flight messages received from the FAA. In contrast to Aircraft objects, Flight objects are
    produced from a single message and their properties do not expire; when a new message arrives with updated
    information, the correlator discards the old Flight object.
    """

    icao_address: ICAOAddress | None
    callsign: str | None
    registration: str | None

    icao_type: str
    wake_category: str | None

    cid: str

    departure: str
    route: str
    arrival: str
    assigned_cruise_altitude: int | None

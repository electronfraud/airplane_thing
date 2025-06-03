"""
This module contains the application's data model. The primary classes are Aircraft and Flight; all other model classes
support one or both of these.

All model objects can be serialized to JSON by the JSONEncoder class. A convenience method calls into the `json`
package with this encoder:

    from aggregator import model
    model.json.dumps(model.Aircraft(...))
    
This is equivalent to:

    import json
    from aggregator import model
    json.dumps(model.Aircraft(...), cls=model.JSONEncoder)
"""

from . import aircraft, flight, icao_address, json

Aircraft = aircraft.Aircraft
Flight = flight.Flight

ICAOAddress = icao_address.ICAOAddress

JSONEncoder = json.JSONEncoder

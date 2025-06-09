"""
This module contains the application's data model. The primary classes are Aircraft and Flight; all other model classes
support one or both of these.

All model objects can be serialized to JSON by a convenience method that calls into the `json` package with a special
default serializer (and sets a few other serialization options as well). Example:

    aircraft = model.Aircraft(...)
    model.json.dumps([aircraft, ...])

This is equivalent to:

    aircraft = model.Aircraft(...)
    json.dumps([aircraft, ...], default=<private serialization function>, allow_nan=False, separators=(",", ":"))
"""

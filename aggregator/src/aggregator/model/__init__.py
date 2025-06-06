"""
This module contains the application's data model. The primary classes are Aircraft and Flight; all other model classes
support one or both of these.

All model objects can be serialized to JSON by a convenience method that calls into the `json` package (and sets a few
other serialization options as well):

    model.json.dumps(model.Aircraft(...))

This is equivalent to:

    json.dumps(model.Aircraft(...), default=<private serialization function>, allow_nan=False, separators=(",", ":"))
"""

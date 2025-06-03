import functools
import json
import typing


class JSONEncoder(json.JSONEncoder):
    """
    A json.JSONEncoder that can serialize aggregator.model objects.
    """

    def default(self, o: typing.Any) -> typing.Any:
        if isinstance(o, aggregator.model.ICAOAddress):
            return str(o)
        return super().default(o)


dumps = functools.partial(json.dumps, cls=JSONEncoder)

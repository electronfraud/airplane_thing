import inspect
import os
from typing import Any

from aggregator.util import maybe


_src_root = ""  # pylint: disable=invalid-name


def set_src_root(path: str) -> None:
    """
    Set the directory prefix to strip from filenames in log message context.
    """
    global _src_root
    _src_root = os.path.abspath(path)
    if not _src_root.endswith("/"):
        _src_root += "/"


def log(*args: object, **kwargs: Any) -> None:
    """
    Log a message to the console prefixed with caller context. The arguments to this function are passed directly to
    print() after the context is printed.
    """
    # fmt: off
    frame    = maybe(lambda: inspect.stack()[3].frame                )
    caller   = maybe(lambda: inspect.getframeinfo(frame)             ) if frame  else None
    filename = maybe(lambda: caller.filename.removeprefix(_src_root) ) if caller else None
    lineno   = maybe(lambda: caller.lineno                           ) if caller else None
    qualname = maybe(lambda: frame.f_code.co_qualname                ) if frame  else None
    # fmt: on

    has_file_context = bool(filename and lineno is not None)
    has_fn_context = bool(qualname)

    if has_file_context:
        print(f"{filename}:{lineno}:", end="")
    if has_fn_context:
        print(f"{qualname}:", end="")

    if has_file_context or has_fn_context:
        print(" ", end="")

    print(*args, **kwargs)

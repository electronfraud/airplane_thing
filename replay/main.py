"""
This is a developer utility that plays back raw Mode S data from an archive. It was written to enable development
without a live radio.

To find data to play back, the script looks for a file named archive.csv in the current working directory. This CSV
file should have two columns: a timestamp in seconds since midnight on January 1, 1970 UTC, and a hexadecimal string
with the raw Mode S transmission. The timestamp may be a rational number with subsecond precision. Messages are printed
to stdout with delays computed from the timestamps so that the replay runs at the same rate as the original messages.

When the end of the archive is reached, the replay starts over at the beginning. Thus the replay runs indefinitely on
a loop.

To use this script as a "radio" for the aggregator, you can pipe it into `nc`:

    python3 main.py | nc -l 30002

Then configure the aggregator to connect to your simulated radio service by starting up the system like so:

    RADIO_HOST=host.docker.internal ./start.sh --dev

Archived raw Mode S messages can be downloaded from https://opensky-network.org/datasets/#raw/.
"""

import sys
import time


ARCHIVE_PATH = "archive.csv"

while True:
    f = open(ARCHIVE_PATH, "rt")
    first_timestamp = None
    lineno = 1
    t0 = time.time()
    while True:
        line = f.readline().strip()
        if not line:
            break

        timestamp, message = line.split(",")
        try:
            timestamp = float(timestamp)
        except ValueError as exc:
            print(f"{ARCHIVE_PATH}:{lineno}: {exc}", file=sys.stderr)
            continue
        finally:
            lineno += 1

        if first_timestamp is None:
            first_timestamp = timestamp
        else:
            t1 = time.time()
            real_elapsed = t1 - t0
            sim_elapsed = timestamp - first_timestamp
            sleep_needed = sim_elapsed - real_elapsed
            if sleep_needed > 0:
                time.sleep(sleep_needed)

        print(f"*{message};")

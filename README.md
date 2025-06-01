# airplane_thing

A complete software stack for tracking and mapping aircraft via Mode S and ADS-B.

## Requirements

- A Linux system
- A software-defined radio compatible with dump1090
- An antenna suitable for receiving on 1090 MHz

I run airplane_thing on a Raspberry Pi 4 Model B with an RTL-SDR V3 kit that included a dipole.

## Installation

1. Install Docker:
```
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```
2. Log out and log back in.
3. Install git:
```
sudo apt install git
```
4. Clone this repo _with submodules_ (--recursive):
```
git clone --recursive https://github.com/electronfraud/airplane_thing.git
cd airplane_thing
```
5. Configure the Mapbox access token:
    1. Sign up for a Mapbox account at https://www.mapbox.com/
    2. Go to https://console.mapbox.com/account/access-tokens/ and copy your token.
    3. Back in your copy of this repo, create a file in `frontend/src` called `token.ts` with the following contents:
```
export const MapboxToken = "paste-your-token-here";
```
6. Build the Docker images:
```
make images
```
7. Start it up (this will start the Docker images in the background and return you to a shell prompt):
```
./start.sh
```
8. In a browser, go to http://your-hostname-here:8080/

## What is all this nonsense?

The display is loosely based on real Air Traffic Control radar displays. Targets (aircraft) are depicted by symbols
that vary depending on what kinds of information the system has received about them:

"squawk" | "alt-no-squawk" | "no-alt-no-squawk" | "vfr";
- `\`: Target has a transponder code other than 1200, 1201, or 1202. These aircraft are in contact with ATC and are
  receiving radar services.
- `/`: Target has altitude information but no transponder code information.
- `V`: Target is squawking 1200, 1201, or 1202. These aircraft are "squawking VFR," meaning they are operating
  under Visual Flight Rules and are not in contact with an ATC radar facility.
- `+`: Target has neither altitude nor transponder code information.

If a target has velocity information (ground speed and course), there will be a line extending out from the target. The
tip of the line is where the aircraft will be in one minute if it maintains its present ground speed and course.

Additional information, when available, is depicted in a data block next to each target. Here is an example of a
complete data block:

```
AAL404
=390
400
```

The first line is the flight number, callsign, or aircraft registration number. In the example, this is AAL404, i.e.
American Airlines flight 404. The second line has two elements: vertical tendency and altitude. Altitude is in hundreds
of feet, so the example aircraft is at 39,000 feet (technically "flight level" 390, or FL390). Vertical tendency shows
whether the aircraft is climbing, level, or descending. The example aircraft is level, so it has an equal sign.
Climbing and descending aircraft will have an up or down arrow in this position. Finally, the third line shows ground
speed in knots. The example aircraft is moving at 400 knots (460 mph, 741 km/h).

If an aircraft is squawking one of the special emergency transponder codes, it will be displayed in red, and a code
will appear on the last line of the data block:

- `ADIZ`: Aircraft is penetrating the Air Defense Identification Zone but is unable to establish contact with ATC.
- `LLNK`: Unmanned aircraft has lost its control link.
- `HIJK`: Unlawful interference.
- `RDOF`: Aircraft's voice radio(s) have malfunctioned and are inoperative.
- `EMRG`: Unspecified emergency.
- `AFIO`: Military aircraft operating without ATC clearance.

Note that the symbology communicates what kinds of information have been _received_, not necessarily the truth about
the flights themselves. For example, if airplane_thing hasn't received a transponder code for an aircraft, it doesn't
necessarily mean the aircraft isn't squawking a code; it just means airplane_thing hasn't received and decoded a
message containing a transponder code from that aircraft recently. This can happen for any number of reasons, most of
which have to do with receiver performance.

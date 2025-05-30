## Installation

1. Install Docker:
```
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```
2. Log out and log back in.
3. Install git (if you haven't already):
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
6. Build the images:
```
docker compose build
```
7. Run:
```
docker compose up
```
8. In a browser, go to http://your-hostname-here:8080/

## What is all this nonsense?

The display is loosely based on Air Traffic Control radar displays. Each square is an aircraft. If the square has a
line coming out of it, the aircraft will be at the tip of the line in one minute (at current speed and course). If
speed and course data haven't arrived recently, no line will be drawn.

Aircraft also have data blocks next to them. Not all information will be available at all times--it all depends on
which data has been received and how recently--but a full data block will look like this:

```
AAL404
3274
390=40
```

The first line is the flight number, callsign, or aircraft registration number. In the example, this is AAL404, i.e.
American Airlines flight 404. The second line is the aircraft's current transponder code, or "squawk," which is
assigned by Air Traffic Control to help identify the aircraft on radar. Squawks can change as aircraft cross into new
ATC sectors, and some squawks have special meanings: 1200 is used by aircraft who aren't under ATC control, 7600 is
used to indicate that the aircraft's radio is inoperative, and 7700 signifies an emergency.

The third line has three elements: altitude, vertical tendency, and ground speed. Altitude is in hundreds of feet, so
the example is at 39,000 feet. Vertical tendency indicates whether the aircraft is climbing, level, or descending. The
example aircraft is level, so it has an equal sign. Climbing and descending aircraft will have an up or down arrow in
this position. Finally, ground speed is in tens of knots. The example aircraft is moving at 400 knots (460 mph,
741 km/h).

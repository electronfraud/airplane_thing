import "./main.css";

import "mapbox-gl/dist/mapbox-gl.css";
import mapboxgl from "mapbox-gl";

import { AircraftLayer, addAircraftSymbol } from "./aircraft_layer";
import { MapboxToken } from "./token";

interface IAircraftReport {
    icao_address: string;
    position: [number, number];
    callsign?: string;
    altitude?: number;
    track?: number;
    ground_speed?: number;
    vertical_speed?: number;
    squawk?: string;
}

function dataBlock(aircraft: IAircraftReport): string {
    let result = "";
    if (typeof aircraft.callsign === "string") {
        result += aircraft.callsign;
    }
    if (typeof aircraft.squawk === "string") {
        if (result.length > 0) {
            result += "\n";
        }
        result += aircraft.squawk;
    }
    if (typeof aircraft.altitude === "number") {
        if (result.length > 0) {
            result += "\n";
        }
        result += Math.round(aircraft.altitude / 100).toLocaleString(undefined, {
            minimumIntegerDigits: 3
        });

        if (typeof aircraft.vertical_speed === "number") {
            if (aircraft.vertical_speed <= -100) {
                result += "↓";
            } else if (aircraft.vertical_speed >= 100) {
                result += "↑";
            } else {
                result += "=";
            }
        }

        if (typeof aircraft.ground_speed === "number") {
            if (typeof aircraft.vertical_speed !== "number") {
                result += " ";
            }
            result += Math.round(aircraft.ground_speed / 10).toLocaleString(undefined, {
                minimumIntegerDigits: 2
            });
        }
    }
    return result;
}

function updateURLAnchor(map: mapboxgl.Map): void {
    const url = new URL(window.location.toString());
    const center = map.getCenter();
    url.hash = [center.lng, center.lat, map.getZoom(), map.getBearing()].map((x) => x.toString()).join(",");
    history.replaceState(null, "", url);
}

async function main() {
    // extract location, zoom, and bearing from URL hash
    let centerLon = 0;
    let centerLat = 0;
    let zoom = 11;
    let bearing = 0;

    const hashParts = window.location.hash.replace("#", "").split(",");
    if (hashParts.length == 4) {
        centerLon = Number(hashParts[0]);
        centerLat = Number(hashParts[1]);
        zoom = Number(hashParts[2]);
        bearing = Number(hashParts[3]);
    }

    // create the map
    mapboxgl.accessToken = MapboxToken;
    const map = new mapboxgl.Map({
        container: "map",
        center: [centerLon, centerLat],
        zoom: zoom,
        bearing: bearing,
        style: "mapbox://styles/mapbox/dark-v11",
        maxPitch: 0,
        minPitch: 0
    });

    map.addControl(new mapboxgl.FullscreenControl());
    map.addControl(new mapboxgl.NavigationControl());
    map.addControl(new mapboxgl.ScaleControl({ unit: "nautical" }));

    map.on("zoomend", (_) => {
        updateURLAnchor(map);
    });
    map.on("moveend", (_) => {
        updateURLAnchor(map);
    });
    map.on("rotateend", (_) => {
        updateURLAnchor(map);
    });

    // add the aircraft layer
    await addAircraftSymbol(map);
    const aircraftLayer = new AircraftLayer("aircraft", map);

    // subscribe to updates
    const ws = new WebSocket("/aggregator");
    ws.addEventListener("open", (_) => {
        // connected = true;
    });
    ws.addEventListener("close", (_) => {
        // connected = false;
    });
    ws.addEventListener("message", (e) => {
        const payload = JSON.parse(e.data as string) as IAircraftReport[];
        aircraftLayer.features = payload.map((aircraft) => {
            return {
                x: aircraft.position[1],
                y: aircraft.position[0],
                groundSpeed: aircraft.ground_speed,
                course: aircraft.track,
                dataBlock: dataBlock(aircraft)
            };
        });
        aircraftLayer.update();
    });
}

await main();

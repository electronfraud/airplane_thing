import "./main.css";

import "mapbox-gl/dist/mapbox-gl.css";
import mapboxgl from "mapbox-gl";

import { AircraftLayer, addAircraftSymbol } from "./aircraft_layer";
import "./stale_indicator";
import { MapboxToken } from "./token";
import AggregatorClient from "./aggregator_client";
import StaleIndicator from "./stale_indicator";

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
    new AggregatorClient(aircraftLayer, document.getElementById("staleness") as StaleIndicator);
}

await main();

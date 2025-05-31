import "./main.css";

import "mapbox-gl/dist/mapbox-gl.css";
import mapboxgl from "mapbox-gl";

import { AircraftLayer, addAircraftSymbols } from "./aircraft_layer";
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

class ZoomToFitControl {
    map?: mapboxgl.Map;
    aircraftLayer?: AircraftLayer;

    onAdd(map: mapboxgl.Map): HTMLElement {
        this.map = map;

        const container = document.createElement("div");
        container.className = "mapboxgl-ctrl mapboxgl-ctrl-group";

        const button = document.createElement("button");
        button.onclick = this.#zoom.bind(this);
        button.className = "custom-ctrl-zoom-to-fit";
        button.ariaLabel = "Zoom to fit all aircraft";
        container.appendChild(button);

        const icon = document.createElement("span");
        icon.className = "mapboxgl-ctrl-icon";
        button.appendChild(icon);

        return container;
    }

    onRemove() {
        this.map = undefined;
    }

    #zoom() {
        const features = this.aircraftLayer?.features ?? [];
        if (features.length == 0) {
            return;
        }

        let minX = 180;
        let minY = 90;
        let maxX = -180;
        let maxY = -90;
        for (const feature of this.aircraftLayer?.features ?? []) {
            if (feature.x < minX) minX = feature.x;
            if (feature.y < minY) minY = feature.y;
            if (feature.x > maxX) maxX = feature.x;
            if (feature.y > maxY) maxY = feature.y;
        }

        this.map?.fitBounds(
            [
                [minX, minY],
                [maxX, maxY]
            ],
            { padding: 100 }
        );
    }
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

    map.addControl(new mapboxgl.FullscreenControl(), "top-right");
    map.addControl(new mapboxgl.NavigationControl({ showCompass: false }), "bottom-right");
    map.addControl(new mapboxgl.NavigationControl({ showZoom: false }), "bottom-right");
    map.addControl(new mapboxgl.GeolocateControl({ trackUserLocation: false }), "bottom-right");
    const zoomToFitControl = new ZoomToFitControl();
    map.addControl(zoomToFitControl, "bottom-right");
    map.addControl(new mapboxgl.ScaleControl({ unit: "nautical" }), "bottom-left");

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
    await addAircraftSymbols(map);
    const aircraftLayer = new AircraftLayer("aircraft", map);
    zoomToFitControl.aircraftLayer = aircraftLayer;

    // subscribe to updates
    new AggregatorClient(aircraftLayer, document.getElementById("staleness") as StaleIndicator);
}

await main();

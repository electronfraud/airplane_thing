import { GeoJSONSource } from "mapbox-gl";
import { Feature } from "geojson";
import { cos, sin } from "./util";

export interface IAircraftFeature {
    x: number;
    y: number;
    course?: number;
    groundSpeed?: number;
    dataBlock?: string;
}

export async function addAircraftSymbol(map: mapboxgl.Map) {
    const canvas = document.createElement("canvas");
    canvas.width = 18;
    canvas.height = 18;
    const ctx = canvas.getContext("2d")!;
    ctx.strokeStyle = "white";
    ctx.strokeRect(0.5, 0.5, 17, 17);
    const symbol = await createImageBitmap(canvas);
    map.addImage("aircraft-symbol", symbol);
}

export class AircraftLayer {
    features: IAircraftFeature[] = [];

    private map: mapboxgl.Map;
    private pointSourceId: string;
    private vectorSourceId: string;

    constructor(id: string, map: mapboxgl.Map) {
        this.map = map;
        this.pointSourceId = `${id}-points-source`;
        this.vectorSourceId = `${id}-vectors-source`;

        const that = this;
        this.map.on("styleimagemissing", (e) => {
            console.log(e.id);
        });
        this.map.on("load", () => {
            that.map.addSource(that.pointSourceId, {
                type: "geojson",
                data: {
                    type: "FeatureCollection",
                    features: []
                }
            });
            that.map.addLayer({
                id: id,
                type: "symbol",
                source: that.pointSourceId,
                layout: {
                    "icon-image": "aircraft-symbol",
                    "icon-allow-overlap": true,
                    "text-field": ["get", "dataBlock"],
                    "text-anchor": "bottom-left",
                    "text-offset": [0.75, -0.5],
                    "text-justify": "left",
                    "text-font": ["Roboto Mono Regular", "Arial Unicode MS Regular"],
                    "text-allow-overlap": true
                },
                paint: {
                    "text-color": "white"
                }
            });

            that.map.addSource(that.vectorSourceId, {
                type: "geojson",
                data: {
                    type: "FeatureCollection",
                    features: []
                }
            });
            that.map.addLayer({
                id: `${id}-vectors`,
                type: "line",
                source: that.vectorSourceId,
                paint: {
                    "line-color": "white"
                }
            });
        });
    }

    update() {
        // generate a point feature for each aircraft
        const points = this.map.getSource(this.pointSourceId) as GeoJSONSource | null;
        if (!points) {
            return;
        }
        points.setData({
            type: "FeatureCollection",
            features: this.features.map((feature) => {
                return {
                    type: "Feature",
                    properties: { dataBlock: feature.dataBlock },
                    geometry: {
                        type: "Point",
                        coordinates: [feature.x, feature.y]
                    }
                };
            })
        });

        // generate a line feature depicting one-minute DR position for each aircraft
        const vectors = this.map.getSource(this.vectorSourceId) as GeoJSONSource | null;
        if (!vectors) {
            return;
        }
        const vectorFeatures = new Array<Feature>();
        for (const feature of this.features) {
            if (typeof feature.groundSpeed !== "number" || typeof feature.course !== "number") {
                continue;
            }
            const distance = feature.groundSpeed / 60; // = distance covered in one minute (nautical miles)
            const dx = (distance * sin(feature.course)) / (60 * cos(feature.y)); // degrees longitude
            const dy = (distance * cos(feature.course)) / 60; // degrees latitude
            vectorFeatures.push({
                type: "Feature",
                properties: { dataBlock: feature.dataBlock },
                geometry: {
                    type: "LineString",
                    coordinates: [
                        [feature.x, feature.y],
                        [feature.x + dx, feature.y + dy]
                    ]
                }
            });
        }
        vectors.setData({
            type: "FeatureCollection",
            features: vectorFeatures
        });
    }
}

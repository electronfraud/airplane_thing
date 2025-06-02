import { GeoJSONSource } from "mapbox-gl";
import GeoJSON from "geojson";
import { cos, sin } from "./util";
import Declutterer, { TextAnchor } from "./declutter";

const ConsoleGreen = "#55ff99";
const ConsoleGreenDim = "#33995c";
const ConsoleRed = "#ff6644";

export type TargetType = "squawk" | "alt-no-squawk" | "no-alt-no-squawk" | "vfr";

export interface IAircraftFeature {
    icaoAddress: string;
    x: number;
    y: number;
    course?: number;
    groundSpeed?: number;
    dataBlock?: string;
    dataBlockAnchor?: TextAnchor;
    targetType: TargetType;
    isEmergency: boolean;
    hasFlightPlan: boolean;
}

function drawFlightPlanSymbol(ctx: CanvasRenderingContext2D) {
    ctx.moveTo(9, 3);
    ctx.lineTo(15, 9);
    ctx.lineTo(9, 15);
    ctx.lineTo(3, 9);
    ctx.lineTo(9, 3);
}

export async function addAircraftSymbols(map: mapboxgl.Map) {
    const canvas = document.createElement("canvas");
    canvas.width = 18;
    canvas.height = 18;
    const ctx = canvas.getContext("2d")!;
    ctx.lineWidth = 2;

    const variations = [
        ["", ConsoleGreen],
        ["emergency-", ConsoleRed]
    ];
    for (const hasFlightPlan of [false, true]) {
        const flightPlan = hasFlightPlan ? "flight-plan-" : "";
        for (const variation of variations) {
            ctx.strokeStyle = variation[1];

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.beginPath();
            ctx.moveTo(4, 0.5);
            ctx.lineTo(14, 17.5);
            if (hasFlightPlan) drawFlightPlanSymbol(ctx);
            ctx.stroke();
            let symbol = await createImageBitmap(canvas);
            map.addImage(`squawk-${flightPlan}${variation[0]}symbol`, symbol);

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.beginPath();
            ctx.moveTo(14, 0.5);
            ctx.lineTo(4, 17.5);
            if (hasFlightPlan) drawFlightPlanSymbol(ctx);
            ctx.stroke();
            symbol = await createImageBitmap(canvas);
            map.addImage(`alt-no-squawk-${flightPlan}${variation[0]}symbol`, symbol);

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.beginPath();
            ctx.moveTo(9, 2.5);
            ctx.lineTo(9, 15.5);
            ctx.moveTo(4, 9);
            ctx.lineTo(14, 9);
            if (hasFlightPlan) drawFlightPlanSymbol(ctx);
            ctx.stroke();
            symbol = await createImageBitmap(canvas);
            map.addImage(`no-alt-no-squawk-${flightPlan}${variation[0]}symbol`, symbol);

            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.beginPath();
            ctx.moveTo(3.5, 2);
            ctx.lineTo(9, 16);
            ctx.lineTo(14.5, 2);
            if (hasFlightPlan) drawFlightPlanSymbol(ctx);
            ctx.stroke();
            symbol = await createImageBitmap(canvas);
            map.addImage(`vfr-${flightPlan}${variation[0]}symbol`, symbol);
        }
    }
}

export class AircraftLayer {
    features: IAircraftFeature[] = [];

    private map: mapboxgl.Map;
    private pointSourceId: string;
    private vectorSourceId: string;

    private declutterer: Declutterer;

    constructor(id: string, map: mapboxgl.Map) {
        this.map = map;
        this.pointSourceId = `${id}-points-source`;
        this.vectorSourceId = `${id}-vectors-source`;

        this.declutterer = new Declutterer(map);

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
                    "icon-image": [
                        "concat",
                        ["get", "targetType"],
                        ["case", ["get", "hasFlightPlan"], "-flight-plan", ""],
                        ["case", ["get", "isEmergency"], "-emergency", ""],
                        "-symbol"
                    ],
                    "icon-allow-overlap": true,
                    "text-field": ["get", "dataBlock"],
                    "text-anchor": ["get", "dataBlockAnchor"],
                    // prettier-ignore
                    "text-offset": [
                        "match", ["get", "dataBlockAnchor"],
                        "bottom-right", [-0.1, -0.6],
                        "top-left",     [ 0.1,  0.6],
                        "top-right",    [-0.1,  0.6],
                        /* default */   [ 0.1, -0.6]
                    ],
                    // prettier-ignore
                    "text-justify": [
                        "match", ["get", "dataBlockAnchor"],
                        "bottom-right", "right",
                        "top-left",     "left",
                        "top-right",    "right",
                        /* default */   "left"
                    ],
                    "text-font": ["Roboto Mono Medium", "Arial Unicode MS Bold"],
                    "text-allow-overlap": true
                },
                paint: {
                    "text-color": ["case", ["get", "isEmergency"], ConsoleRed, ConsoleGreenDim]
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
                    "line-color": ["case", ["get", "isEmergency"], ConsoleRed, ConsoleGreen]
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
        const pointFeatures: GeoJSON.Feature<GeoJSON.Point, IAircraftFeature>[] = this.features.map((feature) => {
            return {
                type: "Feature",
                properties: feature,
                geometry: {
                    type: "Point",
                    coordinates: [feature.x, feature.y]
                }
            };
        });

        // generate a line feature depicting one-minute DR position for each aircraft
        const vectors = this.map.getSource(this.vectorSourceId) as GeoJSONSource | null;
        if (!vectors) {
            return;
        }
        const vectorFeatures = new Array<GeoJSON.Feature<GeoJSON.LineString, IAircraftFeature>>();
        for (const feature of this.features) {
            if (typeof feature.groundSpeed !== "number" || typeof feature.course !== "number") {
                continue;
            }

            const knockoutDistance = 2 ** -this.map.getZoom() * 400;
            const vectorDistance = feature.groundSpeed / 60; // = distance covered in one minute (nautical miles)
            if (knockoutDistance >= vectorDistance) {
                continue;
            }
            const kox = (knockoutDistance * sin(feature.course)) / (60 * cos(feature.y)); // degrees longitude
            const koy = (knockoutDistance * cos(feature.course)) / 60; // degrees latitude
            const vx = (vectorDistance * sin(feature.course)) / (60 * cos(feature.y)); // degrees longitude
            const vy = (vectorDistance * cos(feature.course)) / 60; // degrees latitude

            vectorFeatures.push({
                type: "Feature",
                properties: feature,
                geometry: {
                    type: "LineString",
                    coordinates: [
                        [feature.x + kox, feature.y + koy],
                        [feature.x + vx, feature.y + vy]
                    ]
                }
            });
        }

        // declutter labels
        this.declutterer.setFeatures(pointFeatures, vectorFeatures);
        this.declutterer.declutterLabels();
        this.declutterer.declutterLabels();

        // eslint-disable-next-line @typescript-eslint/non-nullable-type-assertion-style
        (this.map.getSource(this.pointSourceId) as GeoJSONSource).setData({
            type: "FeatureCollection",
            features: this.declutterer.aircraftPositions
        });
        // eslint-disable-next-line @typescript-eslint/non-nullable-type-assertion-style
        (this.map.getSource(this.vectorSourceId) as GeoJSONSource).setData({
            type: "FeatureCollection",
            features: this.declutterer.velocityVectors
        });
    }
}

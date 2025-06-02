import GeoJSON from "geojson";
import { IAircraftFeature } from "./aircraft_layer";
import { longest } from "./util";
import { LngLatLike } from "mapbox-gl";

export const MaxHitBoxPriority = 0;

export type HitBoxType = "icon" | "data-block" | "velocity-vector";
export type TextAnchor = "bottom-left" | "top-left" | "top-right" | "bottom-right";

export class HitBox {
    priority: number;
    icaoAddress: string;
    type: HitBoxType;

    readonly top: number;
    readonly left: number;
    readonly height: number;
    readonly width: number;

    readonly right: number;
    readonly bottom: number;

    constructor(
        priority: number,
        icaoAddress: string,
        type: HitBoxType,
        top: number,
        left: number,
        height: number,
        width: number
    ) {
        this.priority = priority;
        this.icaoAddress = icaoAddress;
        this.type = type;

        this.top = top;
        this.left = left;
        this.height = height;
        this.width = width;

        this.right = this.left + this.width;
        this.bottom = this.top + this.height;
    }

    // Find hit boxes that overlap with this one.
    //
    // Some combinations of hit boxes are never considered to be overlapping even if their coordinates technically do.
    // A data block is never considered to be overlapping its associated icon.
    findOverlaps(others: HitBox[]): HitBox[] {
        const result: HitBox[] = [];
        for (const other of others) {
            if (this === other) {
                continue;
            }
            if (
                this.icaoAddress === other.icaoAddress &&
                ((this.type === "data-block" && other.type === "icon") ||
                    (this.type === "icon" && other.type === "data-block"))
            ) {
                continue;
            }
            if (
                this.left <= other.right &&
                this.right >= other.left &&
                this.top <= other.bottom &&
                this.bottom >= other.top
            ) {
                result.push(other);
            }
        }
        return result;
    }

    // Create a hit box for a data block.
    static forDataBlock(
        icaoAddress: string,
        dataBlock: string,
        anchor: mapboxgl.Point,
        anchorType: TextAnchor
    ): HitBox {
        const textLines = dataBlock.split("\n");
        const height = textLines.length * 20;
        const width = longest(textLines)!.length * 10;

        let top = anchor.y;
        let left = anchor.x;
        // prettier-ignore
        switch (anchorType) {
            case "top-left"    : top +=          8; left +=         9; break;
            case "top-right"   : top +=          8; left -= width + 9; break;
            case "bottom-right": top -= height + 8; left -= width + 9; break;
            default            : top -= height + 8; left +=         9; break;
        }

        return new HitBox(MaxHitBoxPriority - 1, icaoAddress, "data-block", top, left, height, width);
    }
}

const ICAOAddressRE = /^[\dA-F]{6}$/;

export default class Declutterer {
    private map: mapboxgl.Map;

    // maps ICAO addresses to their preferred `text-anchor` value
    private preferredAnchors: Record<string, TextAnchor> = {};

    // these are parallel arrays
    private length = 0;
    aircraftPositions: GeoJSON.Feature<GeoJSON.Point, IAircraftFeature>[] = [];
    velocityVectors: GeoJSON.Feature<GeoJSON.LineString, IAircraftFeature>[] = [];
    private projectedPositions: mapboxgl.Point[] = [];
    private iconHitBoxes: HitBox[] = [];
    private dataBlockHitBoxes: (HitBox | undefined)[] = [];
    private allHitBoxes: HitBox[] = [];

    constructor(map: mapboxgl.Map) {
        this.map = map;
        this.setFeatures([], []);
    }

    // Set the map features to be decluttered. Do not modify the features after calling this method.
    setFeatures(
        aircraftPositions: GeoJSON.Feature<GeoJSON.Point, IAircraftFeature>[],
        velocityVectors: GeoJSON.Feature<GeoJSON.LineString, IAircraftFeature>[]
    ) {
        this.length = this.aircraftPositions.length;
        this.aircraftPositions = aircraftPositions;
        this.velocityVectors = velocityVectors;

        // Cache projections, generate hit boxes, and remove preferred anchors for features that aren't on the map.
        this.projectedPositions = [];
        this.iconHitBoxes = [];
        this.dataBlockHitBoxes = [];

        const icaoAddresses: string[] = [];

        for (const feature of aircraftPositions) {
            const icaoAddress = feature.properties.icaoAddress;
            const projected = this.map.project(feature.geometry.coordinates as LngLatLike);

            icaoAddresses.push(icaoAddress);

            this.projectedPositions.push(projected);
            this.iconHitBoxes.push(
                new HitBox(MaxHitBoxPriority, icaoAddress, "icon", projected.y - 9, projected.x - 9, 18, 18)
            );

            const dataBlock = feature.properties.dataBlock;
            feature.properties.dataBlockAnchor = this.preferredAnchor(feature.properties);
            if (typeof dataBlock === "string") {
                this.dataBlockHitBoxes.push(
                    HitBox.forDataBlock(icaoAddress, dataBlock, projected, feature.properties.dataBlockAnchor)
                );
            } else {
                this.dataBlockHitBoxes.push(undefined);
            }
        }

        this.allHitBoxes = this.iconHitBoxes.concat(this.dataBlockHitBoxes.filter((value) => !!value));

        for (const key of Object.keys(this.preferredAnchors)) {
            if (ICAOAddressRE.test(key) && !icaoAddresses.includes(key)) {
                // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
                delete this.preferredAnchors[key];
            }
        }
    }

    // Adjust the text anchoring of data blocks to prevent overlap.
    declutterLabels() {
        for (let i = 0; i < this.length; i++) {
            const dataBlockHitBox = this.dataBlockHitBoxes[i];
            if (!dataBlockHitBox) {
                continue;
            }
            const overlaps = dataBlockHitBox.findOverlaps(this.allHitBoxes);
            if (overlaps.length === 0) {
                continue;
            }

            const anchorCandidates: TextAnchor[] = ["bottom-left", "top-left", "top-right", "bottom-right"];
            let bestAnchor: TextAnchor = "bottom-left";
            let bestHitBox: HitBox = dataBlockHitBox;
            let minOverlapPriority = MaxHitBoxPriority;
            for (const candidateAnchor of anchorCandidates) {
                const candidateHitBox = HitBox.forDataBlock(
                    dataBlockHitBox.icaoAddress,
                    this.aircraftPositions[i].properties.dataBlock!,
                    this.projectedPositions[i],
                    candidateAnchor
                );
                const overlaps = candidateHitBox.findOverlaps(this.allHitBoxes);
                if (overlaps.length === 0) {
                    bestAnchor = candidateAnchor;
                    bestHitBox = candidateHitBox;
                    break;
                }
                if (overlaps[0].priority < minOverlapPriority) {
                    bestAnchor = candidateAnchor;
                    bestHitBox = candidateHitBox;
                    minOverlapPriority = overlaps[0].priority;
                }
            }

            console.log(`changing ${dataBlockHitBox.icaoAddress} data block anchor to ${bestAnchor}`);
            this.aircraftPositions[i].properties.dataBlockAnchor = bestAnchor;
            this.preferredAnchors[dataBlockHitBox.icaoAddress] = bestAnchor;
            this.dataBlockHitBoxes[i] = bestHitBox;
        }
    }

    private preferredAnchor(feature: IAircraftFeature): TextAnchor {
        let result = this.preferredAnchors[feature.icaoAddress] ?? "bottom-left";
        if (typeof feature.course === "number") {
            // prettier-ignore
            switch (result) {
                case "bottom-left" : if (feature.course >  10 && feature.course <  80) result = "top-left"    ; break;
                case "top-left"    : if (feature.course > 100 && feature.course < 170) result = "bottom-left" ; break;
                case "top-right"   : if (feature.course > 190 && feature.course < 260) result = "bottom-left" ; break;
                case "bottom-right": if (feature.course > 280 && feature.course < 350) result = "bottom-left" ; break;
            }
        }
        return result;
    }
}

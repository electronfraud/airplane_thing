import { AircraftLayer, TargetType } from "./aircraft_layer";
import StaleIndicator from "./stale_indicator";

interface IFlight {
    icao_address?: string;
    callsign?: string;
    registration?: string;
    icao_type: string;
    wake_category?: string;
    cid: string;
    departure: string;
    route: string;
    arrival: string;
    assigned_cruise_altitude?: number;
}

interface IPosition {
    longitude: number;
    latitude: number;
}

interface IAircraftReport {
    icao_address: string;
    position?: IPosition;
    callsign?: string;
    altitude?: number;
    track?: number;
    ground_speed?: number;
    vertical_speed?: number;
    squawk?: string;
    flight?: IFlight;
}

interface IUpdate {
    aircraft: IAircraftReport[];
    breadcrumbs: IPosition[];
}

function specialSquawkIndicator(squawk?: string): string {
    // prettier-ignore
    switch (squawk) {
        case "1200":
        case "1201":
        case "1202": return "VFR";  break;
        case "1276": return "ADIZ"; break;
        case "7400": return "LLNK"; break;
        case "7500": return "HIJK"; break;
        case "7600": return "RDOF"; break;
        case "7700": return "EMRG"; break;
        case "7777": return "AFIO"; break;
        default:
            return "";
    }
}

function verticalTrendString(verticalSpeed?: number): string {
    if (typeof verticalSpeed === "number") {
        if (verticalSpeed > 100) return "↑";
        if (verticalSpeed < -100) return "↓";
        return "=";
    }
    return "";
}

function altitudeString(numeric?: number): string {
    if (typeof numeric === "number") {
        return Math.round(numeric / 100).toLocaleString(undefined, { minimumIntegerDigits: 3 });
    }
    return "";
}

function groundSpeedString(numeric?: number): string {
    if (typeof numeric === "number") {
        return Math.round(numeric / 10).toLocaleString(undefined, { minimumIntegerDigits: 2 });
    }
    return "";
}

function dataBlock(aircraft: IAircraftReport): string {
    return `
        ${specialSquawkIndicator(aircraft.squawk)}
        ${aircraft.callsign ?? ""} ${aircraft.flight?.icao_type ?? ""}
        ${altitudeString(aircraft.altitude)}${verticalTrendString(aircraft.vertical_speed)} ${groundSpeedString(
        aircraft.ground_speed
    )}
        ${aircraft.flight?.departure ?? ""} ${aircraft.flight?.arrival ?? ""}
    `
        .replaceAll(/  +/g, " ")
        .trim();
}

function targetType(aircraft: IAircraftReport): TargetType {
    if (typeof aircraft.squawk === "undefined") {
        if (typeof aircraft.altitude === "undefined") {
            return "no-alt-no-squawk";
        }
        return "alt-no-squawk";
    }
    if (aircraft.squawk === "1200" || aircraft.squawk === "1201" || aircraft.squawk === "1202") {
        return "vfr";
    }
    return "squawk";
}

function isEmergency(aircraft: IAircraftReport): boolean {
    return (
        aircraft.squawk === "1276" ||
        aircraft.squawk === "7400" ||
        aircraft.squawk === "7500" ||
        aircraft.squawk === "7600" ||
        aircraft.squawk === "7700" ||
        aircraft.squawk === "7777"
    );
}

export default class AggregatorClient {
    aircraftLayer: AircraftLayer;
    staleIndicator: StaleIndicator;
    interval?: NodeJS.Timeout;
    lastUpdate?: number;

    constructor(aircraftLayer: AircraftLayer, staleIndicator: StaleIndicator) {
        this.aircraftLayer = aircraftLayer;
        this.staleIndicator = staleIndicator;
        this.#connect();
    }

    #interval() {
        if (typeof this.lastUpdate !== "number") {
            return;
        }
        const elapsed = Math.floor((Date.now() - this.lastUpdate) / 1000);
        if (elapsed >= 3600) {
            const hours = Math.floor(elapsed / 3600);
            const minutes = Math.floor(elapsed / 60) % 60;
            this.staleIndicator.howLong = `${hours.toString()}h ${minutes.toString()}m`;
        } else if (elapsed >= 60) {
            const minutes = Math.floor(elapsed / 60);
            const seconds = elapsed % 60;
            this.staleIndicator.howLong = `${minutes.toString()}m ${seconds.toString()}s`;
        } else {
            this.staleIndicator.howLong = elapsed.toString() + "s";
        }
    }

    #connect(): void {
        const ws = new WebSocket("/aggregator");
        ws.addEventListener("open", (_) => {
            this.staleIndicator.status = "ok";
            if (this.interval !== undefined) {
                clearInterval(this.interval);
                this.interval = undefined;
            }
        });
        ws.addEventListener("close", (_) => {
            this.staleIndicator.status = "stale";
            if (this.interval === undefined) {
                this.lastUpdate = Date.now();
                this.interval = setInterval(this.#interval.bind(this), 1000);
            }
            this.#connect();
        });
        ws.addEventListener("message", (e) => {
            const payload = JSON.parse(e.data as string) as IUpdate;
            this.aircraftLayer.aircraftFeatures = payload.aircraft
                .filter((aircraft) => {
                    return !!aircraft.position;
                })
                .map((aircraft) => {
                    return {
                        icaoAddress: aircraft.icao_address,
                        x: aircraft.position!.longitude,
                        y: aircraft.position!.latitude,
                        groundSpeed: aircraft.ground_speed,
                        course: aircraft.track,
                        dataBlock: dataBlock(aircraft),
                        targetType: targetType(aircraft),
                        isEmergency: isEmergency(aircraft),
                        hasFlightPlan: !!aircraft.flight
                    };
                });
            this.aircraftLayer.breadcrumbFeatures = payload.breadcrumbs.map((crumb) => {
                return {
                    x: crumb.longitude,
                    y: crumb.latitude
                };
            });
            this.aircraftLayer.update();
        });
    }
}

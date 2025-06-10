import { AircraftLayer, TargetType } from "./aircraft_layer";
import StaleIndicator from "./stale_indicator";

interface IFlightPlan {
    icao_address?: string;
    callsign?: string;
    registration?: string;
    icao_type: string;
    wake_category?: string;
    cid: string;
    departure: string;
    route: string;
    arrival: string;
    assigned_altitude?: number;
}

interface IPosition {
    longitude: number;
    latitude: number;
}

interface IAircraftReport {
    icao_address: string;
    position: IPosition;
    callsign?: string;
    altitude?: number;
    track?: number;
    ground_speed?: number;
    vertical_speed?: number;
    squawk?: string;
    flight_plan?: IFlightPlan;
}

function dataBlock(aircraft: IAircraftReport): string {
    let result = "";
    if (typeof aircraft.callsign === "string") {
        result += aircraft.callsign + "\n";
    }

    const altitude =
        typeof aircraft.altitude === "number"
            ? Math.round(aircraft.altitude / 100).toLocaleString(undefined, { minimumIntegerDigits: 3 })
            : undefined;

    if (aircraft.flight_plan && typeof aircraft.flight_plan.assigned_altitude === "number") {
        const assignedAltitude = Math.round(aircraft.flight_plan.assigned_altitude / 100).toLocaleString(undefined, {
            minimumIntegerDigits: 3
        });
        if (typeof aircraft.altitude === "number" && typeof altitude === "string") {
            if (altitude === assignedAltitude) {
                result += `${assignedAltitude}C\n`;
            } else if (aircraft.altitude < aircraft.flight_plan.assigned_altitude) {
                if (typeof aircraft.vertical_speed === "number") {
                    if (aircraft.vertical_speed > 0) {
                        result += `${assignedAltitude}↑${altitude}\n`;
                    } else {
                        result += `${assignedAltitude}-${altitude}\n`;
                    }
                } else {
                    result += `${assignedAltitude} ${altitude}\n`;
                }
            } else {
                if (typeof aircraft.vertical_speed === "number") {
                    if (aircraft.vertical_speed < 0) {
                        result += `${assignedAltitude}↓${altitude}\n`;
                    } else {
                        result += `${assignedAltitude}+${altitude}\n`;
                    }
                } else {
                    result += `${assignedAltitude} ${altitude}\n`;
                }
            }
        } else {
            result += `${assignedAltitude}XXXX\n`;
        }
    } else if (
        aircraft.squawk &&
        (aircraft.squawk === "1200" || aircraft.squawk === "1201" || aircraft.squawk === "1202")
    ) {
        if (typeof altitude === "string") {
            result += `VFR/${altitude}\n`;
        } else {
            result += "VFRXXXX\n";
        }
    } else {
        if (typeof altitude === "string") {
            result += `${altitude}\n`;
        }
    }

    if (aircraft.flight_plan) {
        result += aircraft.flight_plan.cid;
    }
    // prettier-ignore
    switch (aircraft.squawk) {
        case "1276": result += "ADIZ\n"; break;
        case "7400": result += "LLNK\n"; break;
        case "7500": result += "HIJK\n"; break;
        case "7600": result += "RDOF\n"; break;
        case "7700": result += "EMRG\n"; break;
        case "7777": result += "AFIO\n"; break;
        default:
            if (typeof aircraft.ground_speed === "number") {
                result += " ";
                result += Math.round(aircraft.ground_speed).toString();
            }
            result += "\n";
    }

    if (aircraft.flight_plan) {
        result += aircraft.flight_plan.arrival;
        result += "\n";
    }

    return result.trimEnd();
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
            const payload = JSON.parse(e.data as string) as IAircraftReport[];
            this.aircraftLayer.features = payload.map((aircraft) => {
                return {
                    icaoAddress: aircraft.icao_address,
                    x: aircraft.position.longitude,
                    y: aircraft.position.latitude,
                    groundSpeed: aircraft.ground_speed,
                    course: aircraft.track,
                    dataBlock: dataBlock(aircraft),
                    targetType: targetType(aircraft),
                    isEmergency: isEmergency(aircraft),
                    hasFlightPlan: !!aircraft.flight_plan
                };
            });
            this.aircraftLayer.update();
        });
    }
}

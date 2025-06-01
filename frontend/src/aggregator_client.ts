import { AircraftLayer, TargetType } from "./aircraft_layer";
import StaleIndicator from "./stale_indicator";

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
        result += aircraft.callsign + "\n";
    }
    if (typeof aircraft.altitude === "number") {
        if (typeof aircraft.vertical_speed === "number") {
            if (aircraft.vertical_speed <= -100) {
                result += "↓";
            } else if (aircraft.vertical_speed >= 100) {
                result += "↑";
            } else {
                result += "=";
            }
        }
        result += Math.round(aircraft.altitude / 100).toLocaleString(undefined, {
            minimumIntegerDigits: 3
        });
        result += "\n";
    }
    if (typeof aircraft.ground_speed === "number") {
        result += Math.round(aircraft.ground_speed).toString();
    }
    // prettier-ignore
    switch (aircraft.squawk) {
        case "1276": result += " ADIZ"; break;
        case "7400": result += " LLNK"; break;
        case "7500": result += " HIJK"; break;
        case "7600": result += " RDOF"; break;
        case "7700": result += " EMRG"; break;
        case "7777": result += " AFIO"; break;
    }
    return result;
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
                    x: aircraft.position[1],
                    y: aircraft.position[0],
                    groundSpeed: aircraft.ground_speed,
                    course: aircraft.track,
                    dataBlock: dataBlock(aircraft),
                    targetType: targetType(aircraft),
                    emergency: isEmergency(aircraft)
                };
            });
            this.aircraftLayer.update();
        });
    }
}

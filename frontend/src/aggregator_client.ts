import { AircraftLayer } from "./aircraft_layer";
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
                    dataBlock: dataBlock(aircraft)
                };
            });
            this.aircraftLayer.update();
        });
    }
}

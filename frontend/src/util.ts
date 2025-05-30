export function radians(degrees: number): number {
    return (degrees / 180) * Math.PI;
}

export function cos(degrees: number): number {
    return Math.cos(radians(degrees));
}

export function sin(degrees: number): number {
    return Math.sin(radians(degrees));
}

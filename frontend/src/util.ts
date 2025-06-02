export function radians(degrees: number): number {
    return (degrees / 180) * Math.PI;
}

export function cos(degrees: number): number {
    return Math.cos(radians(degrees));
}

export function sin(degrees: number): number {
    return Math.sin(radians(degrees));
}

export function longest(strings: string[]): string | undefined {
    let maxIndex = -1;
    let maxLength = -1;
    for (let i = 0; i < strings.length; i++) {
        const length = strings[i].length;
        if (length > maxLength) {
            maxIndex = i;
            maxLength = length;
        }
    }
    if (maxIndex === -1) {
        return undefined;
    }
    return strings[maxIndex];
}

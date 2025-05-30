FROM debian:bookworm-slim AS build

RUN apt update
RUN apt install -y \
    make           \
    gcc            \
    pkg-config     \
    librtlsdr-dev

WORKDIR /build
COPY dump1090 .
RUN make

FROM debian:bookworm-slim

RUN apt update
RUN apt install -y \
    librtlsdr0

WORKDIR /app
COPY --from=build /build/dump1090 .
COPY entrypoint.sh .
CMD ["./entrypoint.sh"]

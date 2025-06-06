#!/bin/bash -ex

compose_files="-f compose.yml"

if [ "x$1" == "x--expose-radio" ]; then
    compose_files+=" -f compose.expose-radio.yml"
fi

if [ "x$1" == "x--dev" ]; then
    compose_files+=" -f compose.dev.yml"
    profiles=""
    up_flags="--build --force-recreate"

    pushd frontend
    npm install
    npm run build
    popd
else
    profiles="--profile radio"
    up_flags="-d"
fi

docker compose ${compose_files} ${profiles} up ${up_flags}

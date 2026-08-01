#!/bin/bash -ex

compose_files=(-f compose.yml)
profiles=()
up_flags=(-d)

export RADIO_HOST="${RADIO_HOST-host.docker.internal}"

while (($# > 0)); do
    case "$1" in
        --start-radio)
            unset RADIO_HOST
            profiles+=(--profile radio)
            ;;

        --expose-radio)
            unset RADIO_HOST
            profiles+=(--profile radio)
            compose_files+=(-f compose.expose-radio.yml)
            ;;

        --no-swim)
            export SWIM_QUEUE=
            ;;

        --dev)
            compose_files+=(-f compose.dev.yml)
            up_flags=(--build --force-recreate)  # note: also removes -d from up_flags

            pushd frontend
            npm install
            npm run build
            popd
            ;;

        -h|--help)
            set +x
            echo "SYNOPSIS"
            echo
            echo "    $0 [--start-radio] [--expose-radio] [--no-swim] [--dev]"
            echo
            echo "    Start airplane_thing, and make the web frontend accessible on port 8080."
            echo
            echo "    With no arguments or special environment variables, airplane_thing will:"
            echo "    - run in daemon mode"
            echo "    - connect to host.docker.internal:30002 to get ADS-B data (i.e. it will use"
            echo "      whichever dump1090 process is already running instead of starting its own)"
            echo
            echo "    To run in the foreground, use the --dev option. (Note: this has a few other"
            echo "    effects. See --dev below.)"
            echo
            echo "    To connect to a different radio host or port, set RADIO_HOST or RADIO_PORT."
            echo
            echo "    To start a dump1090 process alongside airplane_thing, use --start-radio."
            echo
            echo "OPTIONS"
            echo
            echo "    --start-radio     Start a dump1090 process alongside airplane_thing, instead of"
            echo "                      connecting to an existing dump1090 process."
            echo
            echo "    --expose-radio    (Implies --start-radio.) Make airplane_thing's dump1090"
            echo "                      process accessible on port 30002 on all network interfaces."
            echo
            echo "    --no-swim         Don't connect to SWIM. Use this if your SWIM access has been"
            echo "                      disabled, otherwise airplane_thing won't work at all."
            echo
            echo "    --dev             Development mode. Run an npm install and build, rebuild"
            echo "                      Docker images, force the containers to be recreated, run in"
            echo "                      the foreground, and reload code from disk instead of freezing"
            echo "                      it inside the containers."
            echo
            echo "ENVIRONMENT VARIABLES"
            echo
            echo "    RADIO_HOST        Host running dump1090. Default: host.docker.internal"
            echo "    RADIO_PORT        TCP port to connect to on \$RADIO_HOST. Default: 30002"
            echo
            echo "    SWIM variables are stored in aggregator/.env but can be overridden if necessary."
            echo "    See the SWIFT portal to get the correct values for these variables."
            echo
            echo "    SWIM_URL"
            echo "    SWIM_QUEUE"
            echo "    SWIM_USER"
            echo "    SWIM_PASSWORD"
            echo "    SWIM_VPN"
            exit
            ;;
    esac

    shift
done

docker compose "${compose_files[@]}" "${profiles[@]}" up "${up_flags[@]}"

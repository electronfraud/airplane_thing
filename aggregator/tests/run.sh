#!/bin/bash

failures=()

stage() {
    local output="$($2 2>&1)"
    if [ $? -eq 0 ]; then
        echo -n -e "\e[0;32m"
    else
        echo -n -e "\e[0;31m"
        failures+=("$1")
    fi
    echo -e "===================================================================================================="
    echo -e "--- ${1}"
    echo -e "====================================================================================================\e[0m"
    echo "${output}"
}

cd -- "$(dirname -- $(dirname -- "${BASH_SOURCE[0]}"))"

stage BLACK "black --verbose --check ."
stage PYLINT "pylint ."
stage PYRIGHT pyright
stage PYRIGHT-VERIFYTYPES "pyright --verifytypes aggregator --ignoreexternal"
stage PYTEST pytest

if [ ${#failures[@]} -eq 0 ]; then
    echo -e "\e[0;32mAll stages completed successfully\e[0m"
else
    echo -e "\e[0;31mFailed stages: ${failures[@]}\e[0m"
fi

exit $exit_status

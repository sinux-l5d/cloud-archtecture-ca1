#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

# Check if AWS SAM CLI is installed
if ! command -v sam &> /dev/null
then
    echo "AWS SAM CLI could not be found"
    exit 1
fi

sam delete --no-prompts
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

USE_CONTAINER=""
# Check python is version 3.9 with python3 -V
if ! python3 -V | grep -q "Python 3.9"
then
    echo "Python 3.9 is required to build this project"
    echo "AWS Lambda only supports Python ≤3.9 at the time of writing"
    # Try with docker as fallback
    if command -v docker &> /dev/null
    then
        echo -n "Docker is installed on your system, would you like to use it as a fallback to build the project? [y/N] "
        read -r docker
        if [ "$docker" = "y" ]
        then
            USE_CONTAINER="--use-container"
        else
            echo "Exiting"
            exit 1
        fi
    else
        exit 1
    fi
fi

CA1_BUILD_COMMAND="sam build $USE_CONTAINER"

# Build
echo
echo "== Building project =========="
$CA1_BUILD_COMMAND > /dev/null
echo "=============================="

echo "Build completed"
echo
echo "The current samconfig.toml is:"
echo "=============================="
cat samconfig.toml
echo "=============================="
echo
echo -n "Would you like to deploy with the (d)efault values or go through the (g)uided install? [d/g] "

read -r deploy

if [[ $deploy =~ ^[Gg]$ ]]
then
    sam deploy --guided
elif [[ $deploy =~ ^[Dd]$ ]]
then
    sam deploy
else 
    echo "Invalid option, deploy manually with 'sam deploy'"
    exit 1
fi

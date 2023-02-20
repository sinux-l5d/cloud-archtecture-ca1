#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

manuel_test() {
    STACK_NAME=$1
    QURL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --query 'Stacks[0].Outputs[?OutputKey==`InputQueueUrl`].OutputValue' --output text)
    # Check if jq is installed
    if ! command -v jq &> /dev/null
    then
        echo "jq could not be found"
        exit 1
    fi
    # for range
    LENGTH=$(($(jq length tests/integration/orders.json) - 1 ))
    for i in $( seq 0 $LENGTH )
    do
        ORDER=$(jq ".[$i]" tests/integration/orders.json)
        echo "Order to be sent :"
        echo "=============================="
        echo $ORDER
        echo "=============================="
        echo -n "Hit enter to send the order"
        read -r
        aws sqs send-message --queue-url $QURL --message-body "$ORDER" > /dev/null
        echo
    done
    echo "No more message"
}

automated_test() {
    # check if pytest python module is installed
    if ! python3 -m pytest --version &> /dev/null
    then
        echo "pytest module for python could not be found"
        exit 1
    fi

    AWS_SAM_STACK_NAME=$1 python3 -m pytest tests/integration
}

cat << EOF
You will have to choose between manually testing and automatically testing.

Manually:
- You can see order that will be send
- You get control when message get send
- Use tests/integration/orders.json
Useful if you use order_processor.py in parallel to see the result

Automatically:
- Use pytest
- Send orders to the input queue, test if it arrives in the store queue
- Clean-up the queue before starting
- Delete message in the store queue at the end
- Use tests/integration/orders.json
- NEED good internet connection
Useful if you want to see everything is working without verifying yourself

EOF

echo -n "Would you like to run the tests (m)anually or (a)utomatically? (M/a) "
read -r which_test

echo -n "Enter the name of the DEPLOYED stack you want to test: "
read -r AWS_SAM_STACK_NAME
echo

# exit if empty
if [ -z "$AWS_SAM_STACK_NAME" ]
then
    echo "Stack name cannot be empty"
    exit 1
fi

if [[ $which_test =~ ^[Mm]$ ]]
then
    manuel_test $AWS_SAM_STACK_NAME
elif [[ $which_test =~ ^[Aa]$ ]]
then
    automated_test $AWS_SAM_STACK_NAME
else
    echo "Invalid option"
    exit 1
fi
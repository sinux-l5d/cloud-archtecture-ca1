#!/usr/bin/env python3

from argparse import ArgumentParser
import os
import json
import boto3


def get_args():
    """Parse command line arguments"""
    parser = ArgumentParser(description="Process orders from store's queue")
    parser.add_argument(
        "STACK_NAME", help="CloudFormation stack name to pull information from", type=str)
    parser.add_argument("STORE_NUMBER",
                        help="Store number to process", type=int)
    return parser.parse_args()


def get_stack(stack_name):
    """ Get CloudFormation stack information 
    :param stack_name: CloudFormation stack name
    :return: CloudFormation stack information
    """
    return boto3.client("cloudformation").describe_stacks(StackName=stack_name)["Stacks"][0]


def cf_output(key, stack):
    """
    Get an output value from CloudFormation stack
    :param key: Output key
    :return: Output value
    """
    try:
        return next(filter(lambda x: x['OutputKey'] == key, stack['Outputs']))['OutputValue']
    except IndexError:
        return None


def get_orders(queue_url):
    """Generator to get messages from SQS queue. This is unsed in a for loop
    :param queue_url: SQS queue URL
    """
    sqs = boto3.client("sqs")
    while True:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            # AttributeNames=["SentTimestamp"],
            MaxNumberOfMessages=1,
            # MessageAttributeNames=["All"],
            WaitTimeSeconds=5,
        )
        if "Messages" in response:
            for message in response["Messages"]:
                receipt_handle = message["ReceiptHandle"]
                yield json.loads(message["Body"])
                sqs.delete_message(QueueUrl=queue_url,
                                   ReceiptHandle=receipt_handle)


def format_order(order, ack=False):
    """Format order information to be printed
    If order is None, return headers
    :param order: Order information or None
    :return: Formatted order information
    """
    fmt = "| {:^20} | {:^20} | {:^60.60} | {:^20} | {:^20} | {:^20} |"
    if order == None:
        return fmt.format("Order ID", "Customer", "Customer Address", "Item Code", "Item Description", "Quantity")

    rows = []
    for item in order["items"]:
        rows.append(fmt.format(order["id"], order["customer"], ", ".join(
            order["address"]), item["code"], item["description"], item["quantity"]))
        if ack:
            rows[-1] += " (acknowledged)"
    return "\n".join(rows)


if __name__ == "__main__":
    try:
        args = get_args()
        stack = get_stack(args.STACK_NAME)
        queues = json.loads(cf_output("OutputQueuesUrl", stack))
        store_nb = str(args.STORE_NUMBER)

        print(format_order(None))

        LINE_UP = '\033[1A'
        LINE_CLEAR = '\x1b[2K'

        if store_nb in queues:
            for order in get_orders(queues[store_nb]):  # infinite loop
                rows_wo_ack = format_order(order)
                print(rows_wo_ack)
                print(" Acknowledge by pressing enter", end="\r")
                input()  # Wait
                print(LINE_UP, end=LINE_CLEAR)  # delete ack prompt
                # delete order rows
                for _ in rows_wo_ack.splitlines():
                    print(LINE_UP, end=LINE_CLEAR)
                print(format_order(order, True))
        else:
            print("No queue for store {}".format(store_nb))

    except KeyboardInterrupt:
        print("Exiting")

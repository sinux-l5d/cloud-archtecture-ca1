import boto3
import json
import os

cf = boto3.client('cloudformation')
stack = cf.describe_stacks(StackName=os.environ["STACK_NAME"])['Stacks'][0]
sqs = boto3.client('sqs')


def cf_output(key):
    try:
        return next(filter(lambda x: x['OutputKey'] == key, stack['Outputs']))['OutputValue']
    except IndexError:
        return None


def get_stores_queue_url() -> dict:
    return json.loads(cf_output('OutputQueuesUrl'))


def handler(event, context):
    queues = get_stores_queue_url()

    r = {
        "statusCode": 200,
        "body": json.dumps({
            "in_queue": cf_output("InputQueueUrl"),
            "out_queues": [
                *get_stores_queue_url().values()
            ]
        }),
    }

    for record in event['Records']:

        try:
            order = json.loads(record['body'])
            storeId = str(order['store'])

            if storeId in queues:
                print(
                    f"Sending order {order['id']} from {order['customer']} to store {storeId} queue")
                sqs.send_message(
                    QueueUrl=queues[storeId],
                    MessageBody=json.dumps({
                        "id": order['id'],
                        "customer": order['customer'],
                        "items": order['items'],
                    })
                )
            else:
                print(f"Store {storeId} not found")
        finally:

            # delete message from queue
            sqs.delete_message(
                QueueUrl=cf_output("InputQueueUrl"),
                ReceiptHandle=record['receiptHandle'],
            )

    return r

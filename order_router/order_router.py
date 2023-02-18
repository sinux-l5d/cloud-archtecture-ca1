import boto3
import json
import os

cf = boto3.client('cloudformation')
stack = cf.describe_stacks(StackName=os.environ["STACK_NAME"])['Stacks'][0]
sqs = boto3.client('sqs')
db = boto3.client('dynamodb')


def cf_output(key):
    """
    Get an output value from CloudFormation stack
    :param key: Output key
    :return: Output value
    """
    try:
        return next(filter(lambda x: x['OutputKey'] == key, stack['Outputs']))['OutputValue']
    except IndexError:
        return None


def get_stores_queue_url() -> dict:
    """
    Get the SQS queue URL for each store
    :return: Dict with store ID as key and SQS queue URL as value
    """
    return json.loads(cf_output('OutputQueuesUrl'))


def handler(event, context):
    queues = get_stores_queue_url()

    r = {
        "statusCode": 200,
        "body": "",
    }

    for record in event['Records']:

        # routing order to store queue
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
                        "address": order['address'],
                        "items": order['items'],
                    })
                )
            else:
                r['statusCode'] = 404
                print(
                    f"Store {storeId} not found for order {order['id']} from customer {order['customer']}")

        except Exception as e:
            r['statusCode'] = 500
            print(f"Error processing order {order['id']}: {e}")

        finally:

            try:
                # put in dynamodb
                for item in order['items']:
                    # put in dynamodb
                    db.put_item(
                        TableName=cf_output("TableItems"),
                        Item={
                            'orderId': {
                                'N': str(order['id'])
                            },
                            'storeId': {
                                'N': str(order['store'])
                            },
                            'customer': {
                                'S': order['customer']
                            },
                            'itemQuantity': {
                                'N': str(item['quantity'])
                            },
                            'itemCode': {
                                'S': item['code']
                            },
                            'itemDescription': {
                                'S': item['description']
                            },
                            'itemAmount': {
                                'N': str(item['amount'])
                            },
                        }
                    )
            except Exception as e:
                r['statusCode'] = 500
                print(f"Error saving order {order['id']} in dynamodb: {e}")

            # always delete message from queue
            sqs.delete_message(
                QueueUrl=cf_output("InputQueueUrl"),
                ReceiptHandle=record['receiptHandle'],
            )

    return r

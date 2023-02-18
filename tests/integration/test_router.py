import os
import json

import boto3
import botocore
import pytest
import requests

"""
Make sure env variable AWS_SAM_STACK_NAME exists with the name of the stack we are going to test. 
"""


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


class TestRouter:

    @pytest.fixture()
    def stack(self):
        """ Get the Cloudformation Stack """
        stack_name = os.environ.get("AWS_SAM_STACK_NAME")

        if stack_name is None:
            raise ValueError(
                'Please set the AWS_SAM_STACK_NAME environment variable to the name of your stack')

        client = boto3.client("cloudformation")

        try:
            response = client.describe_stacks(StackName=stack_name)
        except Exception as e:
            raise Exception(
                f"Cannot find stack {stack_name} \n" f'Please make sure a stack with the name "{stack_name}" exists'
            ) from e

        stack = response["Stacks"][0]
        return stack

    @pytest.fixture()
    def queues_url(self, stack):
        """ Get the SQS queue URL from Cloudformation Stack outputs """

        input_queue = cf_output("InputQueueUrl", stack)
        store_queues = cf_output("OutputQueuesUrl", stack)

        if not input_queue:
            raise KeyError(f"InputQueueUrl not found in stack {stack_name}")

        if not store_queues:
            raise KeyError(f"OutputQueuesUrl not found in stack {stack_name}")

        return {"input_queue": input_queue, "store_queues": json.loads(store_queues)}

    @pytest.fixture()
    def purge_queues(self, queues_url):
        """ Purge queues before each test """
        sqs = boto3.client("sqs")

        try:
            for queue in [queues_url["input_queue"], *queues_url["store_queues"].values()]:
                sqs.purge_queue(QueueUrl=queue)
        except sqs.exceptions.PurgeQueueInProgress as e:
            print("Last purge was less than 60 seconds ago. Skipping purge.")
            pass

        yield

    @pytest.fixture()
    def orders_sample(self):
        """ Get orders sample from orders.json """
        orders_file = os.path.join(os.path.dirname(__file__), "orders.json")

        with open(orders_file, "r") as f:
            return json.load(f)

    def test_sqs_routing(self, queues_url, orders_sample, purge_queues):

        sqs = boto3.client("sqs")

        for order in orders_sample:

            store = str(order["store"])

            # sending order to input queue
            sqs.send_message(
                QueueUrl=queues_url["input_queue"], MessageBody=json.dumps(order))

            # receiving order from store queue, try 10 times
            MAX_TRY = 10
            t = 0
            res = {}
            while t < MAX_TRY and 'Messages' not in res:
                res = sqs.receive_message(
                    QueueUrl=queues_url["store_queues"][store], MaxNumberOfMessages=1, WaitTimeSeconds=1)
                t += 1
                print(res)

            should_be = order
            del should_be["store"]

            try:
                assert 'Messages' in res
                assert len(res['Messages']) == 1
                assert 'Body' in res['Messages'][0]
                assert json.loads(res['Messages'][0]['Body']) == should_be
            finally:
                sqs.delete_message(
                    QueueUrl=queues_url["store_queues"][store],
                    ReceiptHandle=res['Messages'][0]['ReceiptHandle'])

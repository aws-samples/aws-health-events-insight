import boto3
import json
import cfnresponse
import os
eventbridge_client = boto3.client('events')


def lambda_handler(event, context):
    try:
        event_data = {
            "eventArn": "arn:aws:health:us-east-1::event/WORKSPACES/AWS_WORKSPACES_MAINTENANCE_SCHEDULED/AWS_WORKSPACES_MAINTENANCE_SCHEDULED_TEST",
                        "service": "WORKSPACES",
                        "eventScopeCode": "ACCOUNT_SPECIFIC",
                        "communicationId": "8f7ef91f0c9f2f3e3f68dffd0fa34fe299e56f323f06154df1de185d0e3f49bf",
                        "lastUpdatedTime": "Wed, 3 May 2023 13:30:55 GMT",
                        "eventRegion": "us-east-1",
                        "eventTypeCode": "AWS_WORKSPACES_MAINTENANCE_SCHEDULED",
                        "eventTypeCategory": "scheduledChange",
                        "startTime": "Wed, 3 May 2023 11:00:00 GMT",
                        "endTime": "Wed, 10 May 2023 14:00:00 GMT",
                        "account": "1234567890",
                        "accountName": "TestAccount",
                        "ingestionTime": "2023-05-22T00:07:57Z",
                        "eventSummary": "Test Event Summary",
                        "eventSource": "mocktest",
                        "monthlySpend": "0.0",
                        "statusCode":"closed",
                        "eventDescription": [{
                            "language": "en_US",
                            "latestDescription": "This is a test AWS Health Event AWS_WORKSPACES_MAINTENANCE_SCHEDULED\n"
                        }],
            "affectedEntities": [{
                "entityValue": "test-resource"
            }]
        }
        # Send the event to EventBridge
        eventbridge_client.put_events(
            Entries=[
                {
                    'Source': 'awshealthtest',
                    'DetailType': 'awshealthtest',
                    'Detail': json.dumps(event_data),
                    'EventBusName': os.environ['EventHealthBusName']
                }
            ]
        )
        cfnresponse.send(event, context, cfnresponse.SUCCESS, {}, None)
        return {'statusCode': 200, 'body': 'Success'}
    except Exception as e:
        cfnresponse.send(event, context, cfnresponse.Fail, {}, None)
        return {'statusCode': 500, 'body': 'Fail'}

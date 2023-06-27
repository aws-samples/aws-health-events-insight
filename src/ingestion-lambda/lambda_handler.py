# lambda_handler.py

import json
import boto3
import os
from datetime import datetime
from utils import summarize_event_description, translate_text, get_account_name, validate_event, log_entry_exit

dynamodb = boto3.resource('dynamodb')

@log_entry_exit
def process_event_data(event, event_detail):
    """
    Process the event data and structure it for saving to DynamoDB.
    """
    
    event_data = {
        'eventArn': event_detail.get('eventArn'),
        'service': event_detail.get('service', ''),
        'eventScopeCode': event_detail.get('eventScopeCode', ''),
        'eventRegion': event_detail.get('eventRegion', ''),
        'eventTypeCode': event_detail.get('eventTypeCode', ''),
        'eventTypeCategory': event_detail.get('eventTypeCategory', ''),
        'startTime': datetime.strptime(event_detail.get('startTime', ''), '%a, %d %b %Y %H:%M:%S %Z').strftime('%d/%m/%Y %H:%M:%S') if event_detail.get('startTime') else '',
        'eventDescription': event_detail.get('eventDescription', [{'latestDescription': None}])[0]['latestDescription'],
        'affectedEntities': ', '.join([entity['entityValue'] for entity in event_detail.get('affectedEntities', [])])
    }

    if event_detail.get('account'):
        event_data['account'] = event_detail.get('account')
    else:
        event_data['account'] = event.get('account')

    event_data['eventSource'] = event.get('source')
    event_data['ingestionTime'] = datetime.strptime(
        event.get('time'), '%Y-%m-%dT%H:%M:%SZ').strftime('%d/%m/%Y %H:%M:%S')

    if event_detail.get('endTime'):
        event_data['endTime'] = datetime.strptime(
            event_detail['endTime'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%d/%m/%Y %H:%M:%S')

    if event_detail.get('lastUpdatedTime'):
        event_data['lastUpdatedTime'] = datetime.strptime(
            event_detail['lastUpdatedTime'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%d/%m/%Y %H:%M:%S')
    else:
        event_data['lastUpdatedTime'] = datetime.strptime(
            event_detail['startTime'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%d/%m/%Y %H:%M:%S')

    return event_data

@log_entry_exit
def save_event_data(table, event_data):
    """
    Save the processed event data to the DynamoDB table.
    """
    table.put_item(Item=event_data)


@log_entry_exit
# Handler function for Lambda
def aws_health(event, context):
    """
    The main Lambda function handler.
    """
    if validate_event(event):
        event_detail = event['detail']
        table = dynamodb.Table(os.environ['DynamoDBName'])
        event_data = process_event_data(event, event_detail)

        get_account_name(event, event_data)

        sagemaker_endpoint = os.environ.get('SageMakerEndpoint')
        if sagemaker_endpoint:
            summarize_event_description(event_data, sagemaker_endpoint)
        else:
            event_data['eventSummary'] = "No LLM Supplied"

        target_lang = os.environ.get('targetLang')
        if target_lang:
            translate_text(event_data, target_lang)

        save_event_data(table, event_data)

        return {'statusCode': 200, 'body': json.dumps('Successfully inserted item into DynamoDB')}
    else:
        return {'statusCode': 500, 'body': json.dumps('Invalid Event Object')}

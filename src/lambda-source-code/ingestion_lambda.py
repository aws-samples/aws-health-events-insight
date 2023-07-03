# lambda_handler.py

import json
import boto3
import os
from datetime import datetime
from utils import summarize_event_description, translate_text, get_account_name, log_entry_exit
from get_cost_impact import get_cost_impact

dynamodb = boto3.resource('dynamodb')

@log_entry_exit
def process_event_data(event, event_detail):
    """
    Process fields.
    """
    event_data = {
        'account': event_detail.get('account') or event.get('account'),
        'eventSource': event.get('source'),
        'startTime': datetime.strptime(event_detail.get('startTime', ''), '%a, %d %b %Y %H:%M:%S %Z').strftime('%d/%m/%Y %H:%M:%S') if event_detail.get('startTime') else '',
        'ingestionTime': datetime.strptime(event.get('time'), '%Y-%m-%dT%H:%M:%SZ').strftime('%d/%m/%Y %H:%M:%S'),
        'lastUpdatedTime': datetime.strptime(event_detail.get('lastUpdatedTime', event_detail['startTime']), '%a, %d %b %Y %H:%M:%S %Z').strftime('%d/%m/%Y %H:%M:%S'),
        'eventDescription': event_detail.get('eventDescription', [{'latestDescription': None}])[0]['latestDescription'],
        'affectedEntities': ', '.join(entity['entityValue'] for entity in event_detail.get('affectedEntities', []))
    }
    if 'endTime' in event_detail:
        event_data['endTime'] = datetime.strptime(event_detail['endTime'], '%a, %d %b %Y %H:%M:%S %Z').strftime('%d/%m/%Y %H:%M:%S')
    """
    Get all other fields as is.
    """
    event_data.update((key, value) for key, value in event_detail.items() if key not in event_data)
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
    
    costSelected = os.environ.get('costSelected')
    if costSelected == "yes":
        get_cost_impact(event, event_data)

    save_event_data(table, event_data)

    return {'statusCode': 200, 'body': json.dumps('Successfully inserted item into DynamoDB')}
    
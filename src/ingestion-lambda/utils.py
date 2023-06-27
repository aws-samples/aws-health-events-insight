# utils.py

import boto3
import json
import logging
import functools
import datetime



sagemaker_runtime = boto3.client('sagemaker-runtime')
translate = boto3.client('translate')
org_client = boto3.client('organizations')
log_level = logging.DEBUG

#####################################
# Logger for entry and exit
#####################################
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')
def log_entry_exit(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Log method entry with parameter values
        logging.debug(f"Entering {func.__name__} with parameters: args={args}, kwargs={kwargs}")
        
        # Call the original method
        result = func(*args, **kwargs)
        
        # Log method exit
        logging.debug(f"Exiting {func.__name__}")
        
        return result
    return wrapper

@log_entry_exit
def summarize_event_description(event_data, sagemaker_endpoint):
    """
    Summarize the event description using a SageMaker endpoint.
    """
    try:
        sagemaker_endpoint_name = sagemaker_endpoint.split('/')[-1]  # Extract the name from the ARN
        sagemaker_endpoint_region = sagemaker_endpoint.split(':')[3]
        model_max_length = 1000  # Adjust the desired maximum length
        summary_text = sagemaker_runtime.invoke_endpoint(
            EndpointName=sagemaker_endpoint_name,
            Body=bytes(event_data['eventDescription'][:model_max_length], 'utf-8'),
            ContentType='application/x-text'
        )['Body'].read().decode('utf-8')
        event_data['eventSummary'] = json.loads(summary_text)["summary_text"]
    except Exception as e:
        event_data['eventSummary'] = "LLM Supplied but not reachable, Failing Summarizations Silently"

@log_entry_exit
def translate_text(event_data, target_lang):
    """
    Translate the event description and summary to the target language.
    """
    try:
        event_description = translate.translate_text(
            Text=event_data['eventDescription'],
            SourceLanguageCode='en',
            TargetLanguageCode=target_lang
        )
        event_data['eventDescription'] = event_description["TranslatedText"]
        if 'eventSummary' in event_data:
            event_summary = translate.translate_text(
                Text=event_data['eventSummary'],
                SourceLanguageCode='en',
                TargetLanguageCode=target_lang
            )
            event_data['eventSummary'] = event_summary["TranslatedText"]
    except Exception as e:
        print(e)

@log_entry_exit
def get_account_name(event, event_data):
    """
    Get the account name for the given account ID.
    """
    try:
        account_id = event.get('account')
        event_data['accountName'] = org_client.describe_account(AccountId=account_id).get('Account').get('Name')
    except Exception as e:
        event_data['accountName'] = account_id
        print(e)

#####################################
# Validators for the mandatory fields
#####################################

@log_entry_exit
def validate_event(event):
    required_fields = [
        'eventArn',
        'service',
        'eventScopeCode',
        'communicationId',
        'lastUpdatedTime',
        'eventRegion',
        'eventTypeCode',
        'eventTypeCategory',
        'startTime',
        'eventDescription',
        'affectedEntities'
    ]

    logging.info("Starting event validation...")

    if not isinstance(event, dict) or 'detail' not in event:
        logging.error("Invalid event format: event must be a dictionary with 'detail' key")
        return False

    detail = event['detail']

    for field in required_fields:
        if field not in detail or not detail[field]:
            logging.error(f"Missing or empty field: {field}")
            return False

    # Validate date-time fields
    for field in ['lastUpdatedTime', 'startTime']:
        if not is_valid_datetime(detail.get(field)):
            logging.error(f"Invalid datetime format for field: {field}")
            return False
    
    # Validate eventDescription format
    if not isinstance(detail.get('eventDescription'), list):
        logging.error("Invalid eventDescription format: eventDescription must be a list")
        return False
    
    logging.info("Event validation successful")
    return True

@log_entry_exit
def is_valid_datetime(dt_string):
    try:
        datetime.datetime.strptime(dt_string, '%a, %d %b %Y %H:%M:%S %Z')
        return True
    except (ValueError, TypeError):
        return False


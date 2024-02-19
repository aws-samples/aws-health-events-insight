import boto3
import json
from datetime import datetime

health_client = boto3.client('health', 'us-east-1')
eventbridge_client = boto3.client('events')

def get_events():
    events = []
    next_token = None
    try:
        while True:
            kwargs = {}
            if next_token and len(next_token) >= 4:
                kwargs['nextToken'] = next_token
            events_response = health_client.describe_events(filter={}, **kwargs)
            events += events_response['events']
            if 'nextToken' in events_response:
                next_token = events_response['nextToken']
            else:
                break
        return events
    except Exception as e:
        print(e)
        return []

def get_event_data(event_details, event_description):
    event_data = {
        'eventArn': event_details['arn'],
        'eventRegion': event_details.get('region', ''),
        'eventTypeCode': event_details.get('eventTypeCode', ''),
        'startTime': event_details.get('startTime').strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'eventDescription': [{'latestDescription': event_description['latestDescription']}]
    }
    # Check if 'timefield' exists in event_details before including it in event_data
    if 'endTime' in event_details:
        event_data['endTime'] = event_details['endTime'].strftime('%a, %d %b %Y %H:%M:%S GMT')

    if 'lastUpdatedTime' in event_details:
        event_data['lastUpdatedTime'] = event_details['lastUpdatedTime'].strftime('%a, %d %b %Y %H:%M:%S GMT')

    event_data.update((key, value) for key, value in event_details.items() if key not in event_data)
    print(event_data)

    return event_data

def send_event_defaultBus(event_data):
    # Send the event to EventBridge
    eventbridge_client.put_events(
        Entries=[
            {
                'Source': 'heidi.health',
                'DetailType': 'awshealthtest',
                'Detail': json.dumps(event_data),
                'EventBusName': 'default'
            }
        ]
    )

def backfill():
    events = get_events()
    try:
        for awsevent in events:
            event_details_response = health_client.describe_event_details(eventArns=[awsevent['arn']])
            event_affected_response = health_client.describe_affected_entities(filter={'eventArns': [awsevent['arn']]})
            entities = event_affected_response['entities']
            entity_values = ', '.join([entity['entityValue'] for entity in entities])
            successful_set_details = event_details_response.get('successfulSet')
            if not successful_set_details:
                continue
            
            event_details = successful_set_details[0]['event']
            event_details['affectedEntities'] = [{'entityValue':entity_values}]
            event_description = successful_set_details[0]['eventDescription']
            event_data = get_event_data(event_details, event_description)
            send_event_defaultBus(event_data)
    except Exception as e:
        print(e)

backfill()

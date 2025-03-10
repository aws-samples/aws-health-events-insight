import boto3
import json
from datetime import datetime

DataCollectionAccountID = input("Enter DataCollection Account ID: ")
DataCollectionRegion = input("Enter DataCollection region: ")
ResourcePrefix = input("Enter ResourcePrefix, Hit enter to use default (heidi-): ") or "heidi-"

health_client = boto3.client('health', 'us-east-1')
eventbridge_client = boto3.client('events',DataCollectionRegion)
EventBusArnVal = f"arn:aws:events:{DataCollectionRegion}:{DataCollectionAccountID}:event-bus/{ResourcePrefix}DataCollectionBus-{DataCollectionAccountID}"

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

def get_event_data(event_details, event_description,event_metadata):
    event_data = {
        'eventArn': event_details['arn'],
        'eventRegion': event_details.get('region', ''),
        'eventTypeCode': event_details.get('eventTypeCode', ''),
        'startTime': event_details.get('startTime').strftime('%a, %d %b %Y %H:%M:%S GMT'),
        'eventDescription': [{'latestDescription': event_description['latestDescription']}],
        'eventMetadata': event_metadata
        }
    # Check if 'timefield' exists in event_details before including it in event_data
    if 'endTime' in event_details:
        event_data['endTime'] = event_details['endTime'].strftime('%a, %d %b %Y %H:%M:%S GMT')

    if 'lastUpdatedTime' in event_details:
        event_data['lastUpdatedTime'] = event_details['lastUpdatedTime'].strftime('%a, %d %b %Y %H:%M:%S GMT')

    event_data.update((key, value) for key, value in event_details.items() if key not in event_data)
    print(event_data)

    return event_data

def send_event_defaultBus(event_data, EventBusArn):
    # Send the event to EventBridge
    eventbridge_client.put_events(
        Entries=[
            {
                'Source': 'heidi.health',
                'DetailType': 'awshealthtest',
                'Detail': json.dumps(event_data),
                'EventBusName': EventBusArn
            }
        ]
    )

# def backfill():
#     events = get_events()
#     EventBusArn = EventBusArnVal
#     try:
#         for awsevent in events:
#             event_details_response = health_client.describe_event_details(eventArns=[awsevent['arn']])
#             event_affected_response = health_client.describe_affected_entities(filter={'eventArns': [awsevent['arn']]})
#             entities = event_affected_response['entities']
#             affected_entities = []
#             for entity in entities:
#                 entity_values = entity['entityValue']
#                 status_code = entity.get('statusCode', 'UNKNOWN')
#                 affected_entities.append({'entityValue': entity_values, 'status': status_code})
            
#             event_details = event_details_response['successfulSet'][0]['event'] if event_details_response.get('successfulSet') else None
#             if not event_details:
#                 continue
                
#             event_details['affectedEntities'] = affected_entities
                
#             event_description = event_details_response['successfulSet'][0]['eventDescription']
#             event_data = get_event_data(event_details, event_description)
#             send_event_defaultBus(event_data, EventBusArn)
#     except Exception as e:
#         print(e)

def backfill():
    events = get_events()
    EventBusArn = EventBusArnVal

    for awsevent in events:
        try:
            # Fetch event details
            event_details_response = health_client.describe_event_details(eventArns=[awsevent['arn']])
            
            # Pagination setup for affected entities
            affected_entities = []
            next_token = None
            
            while True:
                # Fetch affected entities with optional pagination token
                params = {
                    'filter': {'eventArns': [awsevent['arn']]}
                }
                if next_token:
                    params['nextToken'] = next_token

                event_affected_response = health_client.describe_affected_entities(**params)
                
                # Process entities
                entities = event_affected_response.get('entities', [])
                for entity in entities:
                    entity_value = entity.get('entityValue', 'UNKNOWN')
                    status_code = entity.get('statusCode', 'UNKNOWN')
                    affected_entities.append({'entityValue': entity_value, 'status': status_code})
                
                # Check for pagination token
                next_token = event_affected_response.get('nextToken')
                if not next_token:
                    break  # Exit loop if no more pages

            # Extract event details
            successful_set = event_details_response.get('successfulSet', [])
            if not successful_set:
                continue
            
            event_details = successful_set[0].get('event', {})
            if not event_details:
                continue

            # Append accumulated affected entities
            event_details['affectedEntities'] = affected_entities

            # Extract event description
            event_description = successful_set[0].get('eventDescription', '')

            # Extract event Metadata
            event_metadata = successful_set[0].get('eventMetadata', '')

            # Prepare and send event data
            event_data = get_event_data(event_details, event_description,event_metadata)
            send_event_defaultBus(event_data, EventBusArn)

        except Exception as e:
            print(f"Error occurred: {e}")

backfill()

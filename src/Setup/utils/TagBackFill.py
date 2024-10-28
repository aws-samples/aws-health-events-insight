import os
import json
import boto3

DataCollectionAccountID = input("Enter DataCollection Account ID: ")
DataCollectionRegion = input("Enter DataCollection region: ")
ResourcePrefix = input("Enter ResourcePrefix, Hit enter to use default (Heidi-): ") or "Heidi-"
ResourceExplorerViewArn = input("Enter Resource explorere view ARN: ") or "arn:aws:resource-explorer-2:us-east-1:646279148361:view/index-test/203e04a0-2c88-4823-9291-c7e86f8c1478"

eventbridge_client = boto3.client('events',DataCollectionRegion)
EventBusArnVal = f"arn:aws:events:{DataCollectionRegion}:{DataCollectionAccountID}:event-bus/{ResourcePrefix}DataCollectionBus-{DataCollectionAccountID}"

def resource_explorer():
    try:
        # Get the Resource Explorer ARN and region
        view_arn = ResourceExplorerViewArn
        region = view_arn.split(":")[3]
        
        # Create a Resource Explorer client
        resource_explorer = boto3.client('resource-explorer-2', region)
        
        # Create a paginator for listing resources
        paginator = resource_explorer.get_paginator('list_resources')
        
        # Define pagination configuration
        pagination_config = {
            'MaxItems': 100000,  # Total maximum items to return across all pages
            'PageSize': 1000     # Number of items per page
        }
        
        # Paginate through the resources with filters
        response_iterator = paginator.paginate(
            ViewArn=view_arn,
            PaginationConfig=pagination_config
        )
        
        for page in response_iterator:
            for resource in page.get('Resources', []):
                arn = resource.get('Arn')
                tags = [{'entityKey': item['Key'], 'entityValue': item['Value']} 
                        for prop in resource.get('Properties', []) 
                        for item in prop.get('Data', [])]
                
                tag_data = {'entityArn': arn, 'tags': tags}
                if tags:
                    send_event(tag_data)
                else:
                    pass

    except Exception as e:
        print(f"Error in resource_explorer: {e}")

def send_event(tag_data):
    try:
        
        # Put events to the specified Event Bus
        response = eventbridge_client.put_events(
            Entries=[{
                'Source': 'heidi.taginfo',
                'DetailType': 'Heidi tags from resource explorer',
                'Detail': json.dumps(tag_data),
                'EventBusName': EventBusArnVal
            }]
        )
        print(f"Event sent: {response}")
        
    except Exception as e:
        print(f"Error in send_event: {e}")

# Example usage
if __name__ == "__main__":
    resource_explorer()

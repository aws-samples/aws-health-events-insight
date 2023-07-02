# get_cost_impact

import boto3
import logging
import functools
from datetime import datetime, timedelta

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
def get_cost_impact(event, event_data):
    """
    Get the account ID and update the event data with the monthly spend.
    """
    try:
        service_mapping = {
        'Amplify': 'AWS Amplify',
        'AuditManager': 'AWS Audit Manager',
        'Backup': 'AWS Backup',
        'CertificateManager': 'AWS Certificate Manager',
        'CloudTrail': 'AWS CloudTrail',
        'Config': 'AWS Config',
        'DatabaseMigrationService': 'AWS Database Migration Service',
        'DirectoryService': 'AWS Directory Service',
        'Glue': 'AWS Glue',
        'KMS': 'AWS Key Management Service',
        'Lambda': 'AWS Lambda',
        'ResilienceHub': 'AWS Resilience Hub',
        'SecretsManager': 'AWS Secrets Manager',
        'ServiceCatalog': 'AWS Service Catalog',
        'XRay': 'AWS X-Ray',
        'APIGateway': 'Amazon API Gateway',
        'Athena': 'Amazon Athena',
        'Connect': 'Amazon Connect',
        'ConnectCustomerProfiles': 'Amazon Connect Customer Profiles',
        'Detective': 'Amazon Detective',
        'DevOpsGuru': 'Amazon DevOps Guru',
        'docudb': 'Amazon DocumentDB (with MongoDB compatibility)',
        'DynamoDB': 'Amazon DynamoDB',
        'ECR': 'Amazon EC2 Container Registry (ECR)',
        'EC2': 'Amazon Elastic Compute Cloud - Compute',
        'ECS': 'Amazon Elastic Container Service',
        'EFS': 'Amazon Elastic File System',
        'GuardDuty': 'Amazon GuardDuty',
        'Macie': 'Amazon Macie',
        'Neptune': 'Amazon Neptune',
        'QuickSight': 'Amazon QuickSight',
        'Redshift': 'Amazon Redshift',
        'RDS': 'Amazon Relational Database Service',
        'SageMaker': 'Amazon SageMaker',
        'SES': 'Amazon Simple Email Service',
        'SNS': 'Amazon Simple Notification Service',
        'SQS': 'Amazon Simple Queue Service',
        'S3': 'Amazon Simple Storage Service',
        'Translate': 'Amazon Translate',
        'VPC': 'Amazon Virtual Private Cloud',
        'CloudWatch': 'AmazonCloudWatch',
        'CloudWatchEvents': 'CloudWatch Events',
        'ContactCenterTelecom': 'Contact Center Telecommunications (service sold by AMCS, LLC)'
    }

        # Get the service name
        short_service_name = event_data.get('service')
        lowercase_short_service_name = short_service_name.lower()

        # Find the matching service name (case-insensitive)
        service = next((value for key, value in service_mapping.items() if key.lower() == lowercase_short_service_name), short_service_name)

        account_id = event.get('account')
        region = event_data.get('eventRegion')

        # Initialize the AWS Cost Explorer client
        client = boto3.client('ce')

        # Calculate the start and end dates for the last month
        end_date = datetime.now().replace(day=1) - timedelta(days=1)
        start_date = end_date.replace(day=1)

        # Format the start and end dates as strings
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')

        # Define the query for cost and usage data
        query = {
            'TimePeriod': {
                'Start': start_date_str,
                'End': end_date_str
            },
            'Granularity': 'MONTHLY',
            'Filter': {
                'And': [
                    {
                        'Dimensions': {
                            'Key': 'SERVICE',
                            'Values': [service]
                        }
                    },
                    {
                        'Dimensions': {
                            'Key': 'REGION',
                            'Values': [region]
                        }
                    },
                    {
                        'Dimensions': {
                            'Key': 'LINKED_ACCOUNT',
                            'Values': [account_id]
                        }
                    }
                ]
            },
            'Metrics': ['UnblendedCost'],
            'GroupBy': [
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'
                }
            ]
        }

        # Retrieve the cost and usage data
        response = client.get_cost_and_usage(**query)

        # Extract and update the monthly spend in the event data
        results = response['ResultsByTime']
        for result in results:
            groups = result['Groups']
            if groups:
                for group in groups:
                    keys = group['Keys']
                    monthly_spend = group['Metrics']['UnblendedCost']['Amount']  # Add the spend to the existing value
            else:
                monthly_spend = "0"
        event_data['monthlySpend'] = monthly_spend  # Assign the final value to event_data

    except Exception as e:
        print(e)
        event_data['monthlySpend'] = "errorGettingData"
        print(e)
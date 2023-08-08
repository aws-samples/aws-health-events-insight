import boto3
import subprocess
from botocore.exceptions import ClientError
import re
import zipfile
import os

def get_default_region():
    # Get the default AWS region from the current session
    session = boto3.Session()
    return session.region_name


def get_account_id():
    # Get the AWS account ID for Unique names
    sts_client = boto3.client("sts")
    account_id = sts_client.get_caller_identity().get("Account")
    return account_id

def get_organization_details():
    # Get the ID of the AWS organization for event bus
    org_client = boto3.client('organizations')
    POrgID = org_client.describe_organization()['Organization']['Id']
    return POrgID

def create_or_get_s3_bucket(bucket_name, region):
    #create bucket or upload file if bucket is supplied by user
    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Skip Creating: S3 bucket {bucket_name} already exists")
        supplied_bucket = bucket_name
    except ClientError as e:
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
        s3_client.get_waiter("bucket_exists").wait(Bucket=bucket_name)
        supplied_bucket = bucket_name
        print(f"S3 bucket {bucket_name} has been created")
    return supplied_bucket

def sync_cfnfiles(bucket_name,region):
    create_or_get_s3_bucket(bucket_name, region)
    try:
        aws_sync_command = f"aws s3 sync ../src/ s3://{bucket_name}/DataCollection-metadata"
        subprocess.call(aws_sync_command.split())
    except ClientError as e:
        print("Error while syncing S3. Check if deployer role has required S3 and KMS permissions.")
        exit()


def get_quicksight_user(account_id, qsidregion):
    #get quicksight user. ES user can have multiplenamespaces
    try:
        quicksight_client = boto3.client('quicksight', qsidregion)
        response = quicksight_client.list_namespaces(AwsAccountId=account_id)
        namespaces = [namespace['Name'] for namespace in response['Namespaces']]
        qsusernames = []
    except:
        print("Error while listing namespaces. Check if QuickSight is an enterprise plan.")
        exit()
    try:
        for namespace in namespaces:
            response = quicksight_client.list_users(AwsAccountId=account_id, Namespace=namespace, MaxResults=100)
            qsusernames.extend([user['Arn'] for user in response['UserList']])
    except ClientError as q:
        print("Wrong QuickSight Identity region.")
        print(q)
        exit()

    print("\nAvailable QuickSight Users")
    for i, qsusername in enumerate(qsusernames, 1):
        print("{}. {}".format(i, qsusername))
    print()
    quicksight_number = input("Enter the number corresponding to the QuickSight username from the list: ")
    quicksight_user = qsusernames[int(quicksight_number) - 1] if quicksight_number.isdigit() and 1 <= int(quicksight_number) <= len(qsusernames) else None
    if not quicksight_user:
        print("Invalid input. Exiting script.")
        exit()
    return quicksight_user

def create_or_update_cloudformation_stack(region, stack_name, bucket_name, quicksight_user, quicksight_service_role, AWSHealtheventSelected, BackfillEvents,AllowedIpRange):
    """
    Create or update the CloudFormation stack based on its status.
    """
    cfn_client = boto3.client("cloudformation", region)
    stacks = cfn_client.list_stacks(StackStatusFilter=["CREATE_FAILED", "UPDATE_FAILED", "CREATE_COMPLETE", "UPDATE_COMPLETE"])
    response = None

    for stack in stacks.get("StackSummaries"):
        if stack.get("StackName") == stack_name:
            response = cfn_client.update_stack(
                StackName=stack_name,
                TemplateURL=f"https://{bucket_name}.s3.amazonaws.com/DataCollection-metadata/DataCollectionModule/DataCollectionroot.yaml",
                Parameters=[
                    {"ParameterKey": "DataCollectionBucket", "ParameterValue": bucket_name},
                    {"ParameterKey": "QuickSightUser", "ParameterValue": quicksight_user},
                    {"ParameterKey": "QuicksightServiceRole", "ParameterValue": quicksight_service_role},
                    {"ParameterKey": "POrgID", "ParameterValue": get_organization_details()},
                    {"ParameterKey": "BackfillEvents", "ParameterValue": BackfillEvents},
                    {"ParameterKey": "AWSHealtheventSelected", "ParameterValue": AWSHealtheventSelected},
                    {"ParameterKey": "AllowedIpRange", "ParameterValue": AllowedIpRange},
                ],
                Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
                DisableRollback=True
            )
            print(f"Stack update initiated for {region}: {response.get('StackId')}")
            break

    if response is None:
        response = cfn_client.create_stack(
            StackName=stack_name,
            TemplateURL=f"https://{bucket_name}.s3.amazonaws.com/DataCollection-metadata/DataCollectionModule/DataCollectionroot.yaml",
            Parameters=[
                    {"ParameterKey": "DataCollectionBucket", "ParameterValue": bucket_name},
                    {"ParameterKey": "QuickSightUser", "ParameterValue": quicksight_user},
                    {"ParameterKey": "QuicksightServiceRole", "ParameterValue": quicksight_service_role},
                    {"ParameterKey": "POrgID", "ParameterValue": get_organization_details()},
                    {"ParameterKey": "BackfillEvents", "ParameterValue": BackfillEvents},
                    {"ParameterKey": "AWSHealtheventSelected", "ParameterValue": AWSHealtheventSelected},
                    {"ParameterKey": "AllowedIpRange", "ParameterValue": AllowedIpRange},
            ],
            Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
            DisableRollback=True
        )
        print(f"Stack creation initiated for {region}: {response.get('StackId')}")
#Get account_id for resource names
account_id = get_account_id()

# Get the region or prompt user for a region
default_region = get_default_region()
region = input(f"Enter Primary region name (Hit enter to use default: {default_region}): ") or default_region

# Get the S3 bucket name or prompt user for a bucket name
bucket_name = input(f"Enter S3 bucket name for Primary Region (Hit enter to use default: awseventhealth-{account_id}-{region}): ") or f"awseventhealth-{account_id}-{region}"

# Get the QuickSight service role or use a default value
quicksight_service_role = input("Enter QuickSight Service Role (Hit enter to use default: aws-quicksight-service-role-v0): ") or "aws-quicksight-service-role-v0"

# Get the QuickSight Identity region or use a default value
qsidregion = input("Enter your QuickSight Identity region (Hit enter to use default: us-east-1): ") or "us-east-1"

# Get the QuickSight user
quicksight_user = get_quicksight_user(account_id, qsidregion)

# Get the response if backfill is required.
AWSHealtheventSelected = input("Do you want to deploy AWS Health Events Dashboard (N/Y):") or "Y"
if AWSHealtheventSelected == "Y":
    # Get the response if backfill is required.
    BackfillEvents = input("Do you want to backfill healthevents. The data can only be retrieved for the last 90 days.(N/Y):") or "Y"
    # Prompt user to include eventDetail Url
    eventUrlSelected = input("Do you want setup eventUrl for easy access to event descriptions? (N/Y): ") or "Y"
    if eventUrlSelected != "Y":
        AllowedIpRange = ""
    else:
        AllowedIpRange = input("Provide IP Range which can access these eventUrls, this could be your VPN range (Default 0.0.0.0/0): ") or "0.0.0.0/0"
else:
    AWSHealtheventSelected = "N"
    BackfillEvents = "N"
    AllowedIpRange = "N"




# Create or get the S3 bucket and s
sync_cfnfiles(bucket_name, region)

# Create or update the CloudFormation stack
stack_name = f"HeidiDataCollection-{account_id}-{region}"
create_or_update_cloudformation_stack(region, stack_name, bucket_name, quicksight_user, quicksight_service_role, AWSHealtheventSelected, BackfillEvents, AllowedIpRange)
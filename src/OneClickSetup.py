import boto3
import subprocess
from botocore.exceptions import ClientError
import os

def get_default_region():
    # Get the default AWS region from the current session
    session = boto3.Session()
    region = input(f"Enter region name (Hit enter to use default: {session.region_name}): ") or session.region_name
    return region

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

def create_or_get_s3_bucket(account_id, region):
    #create bucket or upload file if bucket is supplied by user
    bucket_name = input(f"Enter S3 bucket name for Primary Region (Hit enter to use default: awseventhealth-{account_id}-{region}): ") or f"awseventhealth-{account_id}-{region}"
    try:
        s3_client = boto3.client('s3', region_name=region)
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"Skip Creating: S3 bucket {bucket_name} already exists")
    except ClientError as e:
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
        s3_client.get_waiter("bucket_exists").wait(Bucket=bucket_name)
        print(f"S3 bucket {bucket_name} has been created")
    return bucket_name

#Sync cloudformation and metadata files
def sync_cfnfiles(bucket_name):
    try:
        aws_sync_command = f"aws s3 sync ../src/ s3://{bucket_name}/DataCollection-metadata"
        subprocess.call(aws_sync_command.split())
    except ClientError as e:
        print("Error while syncing S3. Check if deployer role has required S3 and KMS permissions.")
        exit()

#get quicksight user. ES user can have multiplenamespaces
def get_quicksight_user(account_id, qsidregion):
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

#Get user choice to get deployment type
def get_user_choice():
    options = {'1': 'CentralAccount', '2': 'MemberAccount', '3': 'ConfigRole'}
    while True:
        print("Select Deployment option:")
        for key, value in options.items():
            print(f"{key}. {value}")
        choice = input("Enter the number of your choice: ")
        if choice in options:
            return options[choice]
        else:
            print("Invalid option. Please choose 1, 2, or 3.")

def deploy_stack(command):
    try:
        subprocess.call(command, shell=True)
    except Exception as e:
        print("An error occurred:", e)

def central_account_setup(region, account_id):
    # Get organization details
    POrgID = get_organization_details()
    
    # Create or get S3 bucket
    bucket_name = create_or_get_s3_bucket(account_id, region)

    # Check if AWS Health Events Dashboard should be deployed
    AWSHealtheventSelected = input("Do you want to deploy AWS Health Events Dashboard (N\Y): ") or "Y"
    if AWSHealtheventSelected == "Y":
        # Configure QuickSight settings
        quicksight_service_role = input("Enter QuickSight Service Role (Hit enter to use default: aws-quicksight-service-role-v0): ") or "aws-quicksight-service-role-v0"
        qsidregion = input("Enter your QuickSight Identity region (Hit enter to use default: us-east-1): ") or "us-east-1"
        quicksight_user = get_quicksight_user(account_id, qsidregion)

        # Check if event enrichment with Tags is required
        EnrichEventSelected = input("(Optional)Do you want to enrich events with Tags? It requires access to AWS Config Aggregator (Y/N): ") or "N"
        if EnrichEventSelected == 'Y':
            # Configure AWS Config Aggregator settings
            ConfigurationAggregatorAccount = input(f"   Enter AWS Config Aggregator AccountID (Account that aggregates data from other Accounts, Default {account_id}): ") or account_id
            ConfigurationAggregatorName = input("   Enter AWS Config Aggregator Name: ") or "PlaceHolder"
            ConfigurationAggregatorRegion = input("   Enter AWS Config Aggregator Region: ") or region
            if ConfigurationAggregatorAccount != account_id:
                ConfigurationAggregatorAccount = "N"
                print("(**NOTE:** Since AWS Config Aggregator is in a different account, You must complete Config Role Setup in that account after this)")
        else:
            ConfigurationAggregatorAccount = "N"
            ConfigurationAggregatorName = "N"
            ConfigurationAggregatorRegion = "N"

        # Check if backfill of healthevents is required
        BackfillEvents = input("(Optional)Do you want to backfill healthevents? The data can only be retrieved for the last 90 days. (Y/N): ") or "N"

        # Check if eventUrl setup is required
        eventUrlSelected = input("(Optional)Do you want to set up eventUrl for easy access to event descriptions? (Y/N): ") or "N"
        if eventUrlSelected == "Y":
            AllowedIpRange = input("   Provide IP Range which can access these eventUrls, this could be your VPN range (Default 0.0.0.0/0): ") or "0.0.0.0/0"
        else:
            AllowedIpRange = "N"
    else:
        # AWS Health Events Dashboard is not selected
        AWSHealtheventSelected = "N"
        BackfillEvents = "N"
        AllowedIpRange = "N"
        EnrichEventSelected = "N"
        quicksight_service_role = "N"
        qsidregion = "N"
        quicksight_user = "N"
        ConfigurationAggregatorAccount = "N"
        ConfigurationAggregatorName = "N"
        ConfigurationAggregatorRegion = "N"

    #sync cfn template files
    sync_cfnfiles(bucket_name)
    
    # Create or update the CloudFormation stack
    stack_name = f"HeidiDataCollection-{account_id}-{region}"

    parameters = f"DataCollectionBucket={bucket_name} \
                QuicksightServiceRole={quicksight_service_role} \
                QuickSightUser={quicksight_user} \
                POrgID={POrgID} \
                AWSHealtheventSelected={AWSHealtheventSelected} \
                BackfillEvents={BackfillEvents} \
                AllowedIpRange={AllowedIpRange}\
                EnrichEventSelected={EnrichEventSelected}\
                ConfigurationAggregatorAccount={ConfigurationAggregatorAccount}\
                ConfigurationAggregatorName={ConfigurationAggregatorName}\
                ConfigurationAggregatorRegion={ConfigurationAggregatorRegion}"

    command= f"sam deploy --stack-name {stack_name} --region {region} --parameter-overrides {parameters}\
        --template-file DataCollectionModule/DataCollectionroot.yaml --capabilities CAPABILITY_IAM --disable-rollback"
    
    #Deploy Stack
    deploy_stack(command)

def member_account_setup(region, account_id):
    DataCollectionBusArn = input("Enter the value for Primary EventHealth Bus: ")
    BackfillEvents = input("Do you want to backfill healthevents. The data can only be retrieved for the last 90 days.(Y/N):") or "N"

    # Create or update the CloudFormation stack
    stack_name = f"HeidiDataCollection-Member-{account_id}-{region}"

    parameters = f"DataCollectionBusArn={DataCollectionBusArn} \
                BackfillEvents={BackfillEvents}"
    
    command= f"sam deploy --stack-name {stack_name} --region {region} --parameter-overrides {parameters}\
        --template-file AWSHealthModule/cfnTemplates/AWSHealthEventMember.yaml --capabilities CAPABILITY_IAM --disable-rollback"
    
    #Deploy Stack
    deploy_stack(command)

def config_role_setup(region, account_id):
    AWSHealthEventEnrichLambdaRoleArn = input("Enter AWSHealthEventEnrichLambdaRole Arn(Output of Stack HeidiDataCollection-<AccountID>-<region>-AWSHealthEventEnrich-<hash>): ")
    # Create or update the CloudFormation stack
    stack_name = f"HeidiDataCollection-ConfigCrossAccount-{account_id}-{region}"
    parameters = f"AWSHealthEventEnrichLambdaRoleArn={AWSHealthEventEnrichLambdaRoleArn}"

    command= f"sam deploy --stack-name {stack_name} --region {region} --parameter-overrides {parameters}\
        --template-file AWSHealthModule/cfnTemplates/AWSHealthEventConfigAccountRole.yaml --capabilities CAPABILITY_NAMED_IAM --disable-rollback"
    
    #Deploy Stack
    deploy_stack(command)
    
def main():
    selected_option = get_user_choice()
    print("You selected:", selected_option)

    region = get_default_region()
    account_id = get_account_id()

    if selected_option == 'CentralAccount':
        central_account_setup(region, account_id)

    elif selected_option == 'MemberAccount':
        member_account_setup(region, account_id)

    elif selected_option == 'ConfigRole':
        config_role_setup(region, account_id)

if __name__ == "__main__":
    main()
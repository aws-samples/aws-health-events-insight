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
        response = s3_client.get_bucket_encryption(Bucket=bucket_name)
        encryption = response['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['SSEAlgorithm']
        if encryption != "AES256":
            try:
                bucketkmsarn = response['ServerSideEncryptionConfiguration']['Rules'][0]['ApplyServerSideEncryptionByDefault']['KMSMasterKeyID']
                print(f"Skip Creating: S3 bucket {bucket_name} exists and encrypted with kms {bucketkmsarn}")
            except KeyError:
                bucketkmsarn = input(f"Enter kms Key Arn for {bucket_name}: ")
        else:
            bucketkmsarn = "N"
            print(f"Skip Creating: S3 bucket {bucket_name} already exists")
    except ClientError as e:
        if region == 'us-east-1':
            s3_client.create_bucket(Bucket=bucket_name)
            bucketkmsarn = "N"
        else:
            location = {'LocationConstraint': region}
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
            bucketkmsarn = "N"
        s3_client.get_waiter("bucket_exists").wait(Bucket=bucket_name)
        print(f"S3 bucket {bucket_name} has been created")
    return bucket_name, bucketkmsarn

def print_boxed_text(text):
    lines = text.strip().split('\n')
    max_length = max(len(line) for line in lines)
    
    print('═' * (max_length + 2))
    for line in lines:
        print(f' {line.ljust(max_length)} ')
    print('═' * (max_length + 2))

def check_config_bucket(bucket_name,account_id,region):
    #check if config bucket is reachable
    print_boxed_text("Note: To use this feature, you need a centralized S3 bucket receiving AWS Config snapshots from all accounts. See enrichEvent.md for more details")
    ConfigAggregatorBucket = input("   Enter AWS Config centralized BucketName: ") or bucket_name
    policy_template = f"""
    {{
        "Sid": "S3 Access policy to read Config snapshots",
        "Effect": "Allow",
        "Principal": {{
           "AWS": ["<Important::: Replace this with QS serviceRole ARN>",
                   "arn:aws:iam::{account_id}:role/GluePartitionUpdateLambda-{account_id}-{region}-Role"]
        }},
        "Action": [
            "s3:GetBucketLocation",
            "s3:GetObject",
            "s3:ListBucket",
            "s3:ListBucketMultipartUploads",
            "s3:ListMultipartUploadParts",
            "s3:AbortMultipartUpload"
        ],
        "Resource": [
            "arn:aws:s3:::{ConfigAggregatorBucket}",
            "arn:aws:s3:::{ConfigAggregatorBucket}/*"
        ]
    }}
        """
    print(f"\nINFO: You must add following policy to {ConfigAggregatorBucket} bucket for QuickSight and Lambda Function(To create Glue partitions) to include Tagging info after this setup")
    print_boxed_text(policy_template)
    print(f"continuing with Setup....\n")
    return ConfigAggregatorBucket

def sync_cfnfiles(bucket_name):
    #Sync cloudformation and metadata files
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
    try:
        for i, qsusername in enumerate(qsusernames, 1):
            print("{}. {}".format(i, qsusername))
        print()
        while True:
            quicksight_number = input("Enter the number corresponding to the QuickSight username from the list: ")
            quicksight_user = qsusernames[int(quicksight_number) - 1] if quicksight_number.isdigit() and 1 <= int(quicksight_number) <= len(qsusernames) else None
            if quicksight_user:
                return quicksight_user
            else: 
                print("Invalid Option") 
    except ClientError as q:
        print("Something went wrong, Check Quicksight settings")

def get_user_choice():
    #Get user choice to get deployment type
    options = {'1': 'CentralAccount', '2': 'MemberAccount'}
    while True:
        print("Select Deployment option:")
        for key, value in options.items():
            print(f"{key}. {value}")
        choice = input("Enter the number of your choice: ")
        if choice in options:
            return options[choice]
        else:
            print("Invalid option. Please choose 1, 2")

def deploy_stack(command):
    #deploy stack
    try:
        subprocess.call(command, shell=True)
    except Exception as e:
        print("An error occurred:", e)

def setup_notification():
    Notification = input("\n(Optional)Do you want to set up notification? (Y/N): ") or "N"
    if Notification == "Y":
        GetChannelChoice = input("   Select client (1 for Slack, 2 for Teams): ") or "1"
        if GetChannelChoice == "1":
            print_boxed_text("If this is first time setup, Slack Workspace setup/OAuth authorization must be done from AWS console.\
                             \n1. Open the AWS Chatbot console at https://console.aws.amazon.com/chatbot/\
                             \n2. Under Configure a chat client, choose Slack, then choose Configure client.\
                             \n3. From the dropdown list at the top right, choose the Slack workspace that you want to use with AWS Chatbot and Choose Allow.\
                             \n4. Note down the Workspace ID from AWS Chatbot Console and Enter below")
            SlackWorkspaceId = input("\nProvide Workspace ID: ") or "N"
            SlackChannelId = input("Provide Slack Channel Id (Note: Slack Channel must be private and you must invite aws@ to the channel): ") or "N"
            TeamId = "N"
            TeamsTenantId = "N"
            TeamsChannelId = "N"
        elif GetChannelChoice == "2":
            print_boxed_text("If this is first time setup, Slack Workspace setup/OAuth authorization must be done from AWS console.\
                    \n1. Open the AWS Chatbot console at https://console.aws.amazon.com/chatbot/.\
                    \n2. Under Configure a chat client, choose Microsoft Teams, then choose Configure client.\
                    \n3. Copy and paste your Microsoft Teams channel URL. Your channel URL contains your tenant, team, and channel IDs.\
                    \n4. Choose Configure and On the Microsoft Teams authorization page, choose Accept.\
                    \n5. From the Microsoft Teams page, choose Configure new channel.")
            SlackChannelId = "N"
            SlackWorkspaceId = "N"
            TeamId = input("      Provide TeamId: ") or "N"
            TeamsTenantId = input("      Provide TeamsTenantId: ") or "N"
            TeamsChannelId = input("      Provide TeamsChannelId: ") or "N"
        else:
            print("Invalid Choice... Continuing without notification setup")
    else:
        Notification = "N"
        SlackChannelId = "N"
        SlackWorkspaceId = "N"
        TeamId = "N"
        TeamsTenantId = "N"
        TeamsChannelId = "N"
    
    return Notification, SlackChannelId, SlackWorkspaceId, TeamId, TeamsTenantId, TeamsChannelId

def central_account_setup(region, account_id):
    # Get organization details
    POrgID = get_organization_details()
    
    # Create or get S3 bucket
    bucket_name, bucketkmsarn = create_or_get_s3_bucket(account_id, region)

    # Configure QuickSight settings
    quicksight_service_role = input("Enter QuickSight Service Role (Hit enter to use default: aws-quicksight-service-role-v0): ") or "aws-quicksight-service-role-v0"
    qsidregion = input("Enter your QuickSight Identity region (Hit enter to use default: us-east-1): ") or "us-east-1"
    quicksight_user = get_quicksight_user(account_id, qsidregion)

    # Check if Notification is required
    Notification, SlackChannelId, SlackWorkspaceId, TeamId, TeamsTenantId, TeamsChannelId = setup_notification()

    # Check if backfill of healthevents is required
    BackfillEvents = input("(Optional)Do you want to backfill healthevents? limited to the past 90 days (Y/N): ") or "N"

    # Check if eventUrl setup is required
    eventUrlSelected = input("(Optional)Do you want to set up eventUrl for easy access to event descriptions? (Y/N): ") or "N"
    if eventUrlSelected == "Y":
        print_boxed_text("Note: EventUrl will be accessible via APIGW with a resource policy resticting with IP range. Add additional authentication to APIGW post-setup as needed.")
        AllowedIpRange = input("   Provide IP Range which can access these eventUrls, this could be your VPN range (Default 0.0.0.0/0): ") or "0.0.0.0/0"
    else:
        AllowedIpRange = "N"

    # Check if event enrichment with Tags is required
    EnrichEventSelected = input("(Optional)Do you want to enrich events with Tags? It requires access to centralized AWS Config S3 Bucket(Y/N): ") or "N"
    if EnrichEventSelected == 'Y':
    # Configure AWS Config Aggregator settings
        ConfigAggregatorBucket = check_config_bucket(bucket_name,account_id,region)
    else:
        ConfigAggregatorBucket = "N"

    #sync cfn template files
    sync_cfnfiles(bucket_name)
    
    # Create or update the CloudFormation stack
    stack_name = f"HeidiDataCollection-{account_id}-{region}"

    parameters = f"DataCollectionBucket={bucket_name} \
                DataCollectionBucketKmsArn={bucketkmsarn}\
                QuicksightServiceRole={quicksight_service_role} \
                QuickSightUser={quicksight_user} \
                POrgID={POrgID} \
                BackfillEvents={BackfillEvents} \
                AllowedIpRange={AllowedIpRange}\
                ConfigAggregatorBucket={ConfigAggregatorBucket}\
                Notification={Notification}\
                SlackChannelId={SlackChannelId}\
                SlackWorkspaceId={SlackWorkspaceId}\
                TeamId={TeamId}\
                TeamsTenantId={TeamsTenantId}\
                TeamsChannelId={TeamsChannelId}"

    command= f"sam deploy --stack-name {stack_name} --region {region} --parameter-overrides {parameters}\
        --template-file DataCollectionModule/DataCollectionroot.yaml --capabilities CAPABILITY_NAMED_IAM --disable-rollback"
    
    #Deploy Stack
    deploy_stack(command)

def member_account_setup(region, account_id):
    #Member Account Setup
    DataCollectionBusArn = input("Enter the value for DataCollection Bus Arn: ")
    BackfillEvents = input("Do you want to backfill healthevents. The data can only be retrieved for the last 90 days.(Y/N):") or "N"

    # Create or update the CloudFormation stack
    stack_name = f"HeidiDataCollection-Member-{account_id}-{region}"

    parameters = f"DataCollectionBusArn={DataCollectionBusArn} \
                BackfillEvents={BackfillEvents}"
    
    command= f"sam deploy --stack-name {stack_name} --region {region} --parameter-overrides {parameters}\
        --template-file AWSHealthModule/cfnTemplates/HealthEventMember.yaml --capabilities CAPABILITY_NAMED_IAM --disable-rollback"
    
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

if __name__ == "__main__":
    main()
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


def get_organization_details():
    # Get the ID of the AWS organization for event bus
    org_client = boto3.client('organizations')
    PrincipalOrgID = org_client.describe_organization()['Organization']['Id']
    return PrincipalOrgID


def get_account_id():
    # Get the AWS account ID for Unique names
    sts_client = boto3.client("sts")
    account_id = sts_client.get_caller_identity().get("Account")
    return account_id

def zip_files(source_dir, output_zip):
    with zipfile.ZipFile(output_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, source_dir)
                zipf.write(file_path, relative_path)


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
        #Added Support for Lambda Build PreSync
        zip_files('../src/lambda-source-code', '../src/lambda-source-code/lambda.zip')
        aws_sync_command = f"aws s3 sync ../src s3://{bucket_name}/"
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


def get_sagemaker_endpoint_arn(include_model):
    #Include LLM model for summarization
    if include_model == "yes":
        # Prompt user to enter the SageMaker endpoint ARN
        print()
        SageMakerEndpoint = input("Enter the SageMaker endpoint ARN: ")
        arn_pattern = r"^arn:aws:sagemaker:[a-z0-9\-]+:\d{12}:endpoint\/[a-zA-Z0-9]([a-zA-Z0-9\-])*[a-zA-Z0-9]$"
        # Match the ARN against the pattern
        if not re.match(arn_pattern, SageMakerEndpoint):
            print("Invalid ARN format")
            exit()
        print("SageMaker ML model included")
    else:
        SageMakerEndpoint = ""
    return SageMakerEndpoint

def translate_text(Include_targetLang):
    if Include_targetLang == "yes":
        # Prompt user to enter the SageMaker endpoint ARN
        print()
        targetLang = input("Enter the language code: Supported Lang (https://docs.aws.amazon.com/translate/latest/dg/what-is-languages.html): ")
    else:
        targetLang = ""
    return targetLang

def create_or_update_cloudformation_stack(region, stack_name, bucket_name, quicksight_user, SageMakerEndpoint, quicksight_service_role, isPrimaryRegion, secondaryRegion,webhookSelected,datalakebucket):
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
                TemplateURL=f"https://{bucket_name}.s3.amazonaws.com/ControlAccountStack/root-stack.yaml",
                Parameters=[
                    {"ParameterKey": "EventHealthBucket", "ParameterValue": bucket_name},
                    {"ParameterKey": "PrincipalOrgID", "ParameterValue": get_organization_details()},
                    {"ParameterKey": "QuickSightUser", "ParameterValue": quicksight_user},
                    {"ParameterKey": "SageMakerEndpoint", "ParameterValue": SageMakerEndpoint},
                    {"ParameterKey": "QuicksightServiceRole", "ParameterValue": quicksight_service_role},
                    {"ParameterKey": "targetLang", "ParameterValue": targetLang},
                    {"ParameterKey": "isPrimaryRegion", "ParameterValue": isPrimaryRegion},
                    {"ParameterKey": "secondaryRegion", "ParameterValue": secondaryRegion},
                    {"ParameterKey": "webhookSelected", "ParameterValue": webhookSelected},
                    {"ParameterKey": "datalakebucket", "ParameterValue": datalakebucket}
                ],
                Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
                DisableRollback=True
            )
            print(f"Stack update initiated for {region}: {response.get('StackId')}")
            break

    if response is None:
        response = cfn_client.create_stack(
            StackName=stack_name,
            TemplateURL=f"https://{bucket_name}.s3.amazonaws.com/ControlAccountStack/root-stack.yaml",
            Parameters=[
                {"ParameterKey": "EventHealthBucket", "ParameterValue": bucket_name},
                {"ParameterKey": "PrincipalOrgID", "ParameterValue": get_organization_details()},
                {"ParameterKey": "QuickSightUser", "ParameterValue": quicksight_user},
                {"ParameterKey": "SageMakerEndpoint", "ParameterValue": SageMakerEndpoint},
                {"ParameterKey": "QuicksightServiceRole", "ParameterValue": quicksight_service_role},
                {"ParameterKey": "targetLang", "ParameterValue": targetLang},
                {"ParameterKey": "isPrimaryRegion", "ParameterValue": isPrimaryRegion},
                {"ParameterKey": "secondaryRegion", "ParameterValue": secondaryRegion},
                {"ParameterKey": "webhookSelected", "ParameterValue": webhookSelected}
            ],
            Capabilities=["CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"],
            DisableRollback=True
        )
        print(f"Stack creation initiated for {region}: {response.get('StackId')}")
#Get account_id for resource names
account_id = get_account_id()
# Get the default region or prompt user for a region
default_region = get_default_region()

# Get input for multiRegion Deployment
multiregion = input(f"Do you want to deploy central accout setup in multiregion (yes/no): ")
region = input(f"Enter Primary region name (Hit enter to use default: {default_region}): ") or default_region

if multiregion == "yes":
    secondaryRegion = input(f"Enter Secondary region name: ")
else:
    secondaryRegion= ""

# Get the S3 bucket name or prompt user for a bucket name
bucket_name = input(f"Enter S3 bucket name for Primary Region (Hit enter to use default: awseventhealth-{account_id}-{region}): ") or f"awseventhealth-{account_id}-{region}"
if multiregion == "yes":
    Secondary_bucket_name = input(f"Enter S3 bucket name for Secondary Region (Hit enter to use default: awseventhealth-{account_id}-{secondaryRegion}): ") or f"awseventhealth-{account_id}-{secondaryRegion}"

# Prompt user to include delivery events to S3 to create datalake
s3selected = input("Do you want to send events to s3 for datalake/future reference? (yes/no): ")
if s3selected == "yes":
    datalakebucket = input(f"Enter S3 bucket name for Primary datalake(Hit enter to use default: awseventhealth-{account_id}-{region}): ") or f"awseventhealth-{account_id}-{region}"
    create_or_get_s3_bucket(datalakebucket, region)
    if multiregion == "yes":
        Secondarydatalakebucket = input(f"Enter S3 bucket name for secondary datalake(Hit enter to use default: awseventhealth-{account_id}-{secondaryRegion}): ") or f"awseventhealth-{account_id}-{secondaryRegion}"
        create_or_get_s3_bucket(Secondarydatalakebucket, region)
else:  
    datalakebucket = ""
    Secondarydatalakebucket=""

# Get the QuickSight service role or use a default value
quicksight_service_role = input("Enter QuickSight Service Role (Hit enter to use default: aws-quicksight-service-role-v0): ") or "aws-quicksight-service-role-v0"

# Get the QuickSight Identity region or use a default value
qsidregion = input("Enter your QuickSight Identity region (Hit enter to use default: us-east-1): ") or "us-east-1"

# Get the QuickSight user
quicksight_user = get_quicksight_user(account_id, qsidregion)

# Prompt user to include SageMaker ML model
include_model = input("Do you want to include a SageMaker ML model? (yes/no): ")
# Get the SageMaker endpoint ARN
SageMakerEndpoint = get_sagemaker_endpoint_arn(include_model)

# Prompt user to include translation
Include_targetLang = input("Do you want to Translate Events in different language? (yes/no): ")
# Get response for translation
targetLang = translate_text(Include_targetLang)

# Prompt user to include webhook for 3rd party event ingestion
webhookSelected = input("Do you want setup webhook for 3rd party event ingestion? (yes/no): ")
if webhookSelected != "yes":
    webhookSelected = ""

# Create or get the S3 bucket and s
sync_cfnfiles(bucket_name, region)
if multiregion == "yes":
    sync_cfnfiles(Secondary_bucket_name, secondaryRegion)


#Zip Up Lambda and write to S3 

# Create or update the CloudFormation stack
stack_name = f"HealthEventDashboardStack{account_id}-{region}"
create_or_update_cloudformation_stack(region, stack_name, bucket_name, quicksight_user, SageMakerEndpoint, quicksight_service_role,'Y',secondaryRegion,webhookSelected,datalakebucket)

if multiregion == "yes":
    stack_name = f"HealthEventDashboardStack{account_id}-{secondaryRegion}"
    create_or_update_cloudformation_stack(secondaryRegion, stack_name, Secondary_bucket_name, quicksight_user, SageMakerEndpoint, quicksight_service_role,'N',secondaryRegion,webhookSelected,Secondarydatalakebucket)

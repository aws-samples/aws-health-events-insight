import boto3
import subprocess
from botocore.exceptions import ClientError

# Get the organization details for the specified AWS account
org_client = boto3.client('organizations')
PrincipalOrgID = org_client.describe_organization()['Organization']['Id']

# Get the username details for the specified AWS account
sts_client = boto3.client("sts")
account_id = sts_client.get_caller_identity().get("Account")

# Get input parameters from user
region = input("Enter region name: (Hit enter to use default us-east-1): ") or "us-east-1"

# Create bucket name
bucket_name = "awseventhealth-{}-{}".format(account_id,region)
bucket_name = input("Enter S3 bucket name (Hit enter to use default : {}): ".format(bucket_name)) or bucket_name

principal_org_id = input("Enter AWS organization ID (Hit enter to use default {}): ".format(PrincipalOrgID)) or PrincipalOrgID
quicksight_service_role = input("Enter QuickSight Service Role (Hit enter to use default aws-quicksight-service-role-v0): ") or "aws-quicksight-service-role-v0"
qsidregion = input("Enter your QuickSight Identity region (Hit enter to use default us-east-1): ") or "us-east-1"



# Retrieve the list of namespaces and corresponding usernames
try:
    quicksight_client = boto3.client('quicksight', qsidregion)
    response = quicksight_client.list_namespaces(AwsAccountId=account_id)
    namespaces = [namespace['Name'] for namespace in response['Namespaces']]
    qsusernames = []
except:
    print("Invalid QuickSight region")
    exit()

try:
    for namespace in namespaces:
        response = quicksight_client.list_users(AwsAccountId=account_id, Namespace=namespace, MaxResults=100)
        qsusernames.extend([user['Arn'] for user in response['UserList']])
except ClientError as q:
    print("Wrong QuickSight Identity region ")
    print(q)
    exit()

print()
print("Available QuickSight Users")
for i, qsusername in enumerate(qsusernames, 1):
    print("{}. {}".format(i, qsusername))
print()
quicksight_number = input("Enter the number corresponding to the QuickSight Username from the list: ")
quicksight_user = qsusernames[int(quicksight_number) - 1] if quicksight_number.isdigit() and 1 <= int(quicksight_number) <= len(qsusernames) else None

if not quicksight_user:
    print("Invalid input. Exiting script.")
    exit()

try:
    # Check if the bucket exists
    s3_client = boto3.client('s3')
    s3_client.head_bucket(Bucket=bucket_name)
    print("S3 bucket {} already exists".format(bucket_name))
except ClientError as e:
    if region == 'us-east-1':
        s3_client = boto3.client('s3')
        s3_client.create_bucket(Bucket=bucket_name)
        # Wait for the bucket to finish creation
        s3_client.get_waiter("bucket_exists").wait(Bucket=bucket_name)
        print(f"S3 bucket {bucket_name} has been created")
    else:
        s3_client = boto3.client('s3', region_name=region)
        location = {'LocationConstraint': region}
        s3_client.create_bucket(Bucket=bucket_name,
                                CreateBucketConfiguration=location)
        # Wait for the bucket to finish creation
        s3_client.get_waiter("bucket_exists").wait(Bucket=bucket_name)
        print(f"S3 bucket {bucket_name} has been created")       

# Sync src directory with S3 bucket
aws_sync_command = "aws s3 sync src s3://{}/".format(bucket_name)
subprocess.call(aws_sync_command.split())

# Initialize CloudFormation stack
stack_name = "HealthEventDashboardStack{}".format(account_id)
cfn_client = boto3.client("cloudformation", region)

stacks = cfn_client.list_stacks(StackStatusFilter=["CREATE_FAILED","UPDATE_FAILED"])
response = None
for stack in stacks.get("StackSummaries"):
    if stack.get("StackName") == stack_name:
        response = cfn_client.update_stack(
            StackName=stack_name,
            TemplateURL=f"https://{bucket_name}.s3.amazonaws.com/ManagementAccountStack/managementaccount-stack.yaml",
            Parameters=[
                {"ParameterKey": "EventHealthBucket", "ParameterValue": bucket_name},
                {"ParameterKey": "PrincipalOrgID", "ParameterValue": principal_org_id},
                {"ParameterKey": "QuickSightUser", "ParameterValue": quicksight_user},
                {"ParameterKey": "QuicksightServiceRole", "ParameterValue": quicksight_service_role or "aws-quicksight-service-role-v0"}
            ],
            Capabilities=["CAPABILITY_NAMED_IAM","CAPABILITY_AUTO_EXPAND"],
            DisableRollback=True
        )
        print(f"Stack update initiated: {response.get('StackId')}")
        break

if response is None:
    response = cfn_client.create_stack(
        StackName=stack_name,
        TemplateURL=f"https://{bucket_name}.s3.amazonaws.com/ManagementAccountStack/managementaccount-stack.yaml",
        Parameters=[
            {"ParameterKey": "EventHealthBucket", "ParameterValue": bucket_name},
            {"ParameterKey": "PrincipalOrgID", "ParameterValue": principal_org_id},
            {"ParameterKey": "QuickSightUser", "ParameterValue": quicksight_user},
            {"ParameterKey": "QuicksightServiceRole", "ParameterValue": quicksight_service_role or "aws-quicksight-service-role-v0"}
        ],
        Capabilities=["CAPABILITY_NAMED_IAM","CAPABILITY_AUTO_EXPAND"],
        DisableRollback=True
    )
    print(f"Stack creation initiated: {response.get('StackId')}")

print(response)

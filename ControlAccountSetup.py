import boto3
import subprocess
from botocore.exceptions import ClientError

# Get the organization details for the specified AWS account
org_client = boto3.client('organizations')
PrincipalOrgID = org_client.describe_organization()['Organization']['Id']

# Get the username details for the specified AWS account
sts_client = boto3.client("sts")
account_id = sts_client.get_caller_identity().get("Account")
username = sts_client.get_caller_identity().get("Arn").split("/")[-2:]
username = "/".join(username)

# Create bucket name
bucket_name = "awseventhealth-{}".format(account_id)

# Get input parameters from user
region_name = input("Enter region name: (Hit enter to use default us-east-1): ") or "us-east-1"
bucket_name = input("Enter S3 bucket name: (Hit enter to use default : {}): ".format(bucket_name)) or bucket_name
quicksight_user = input("Enter QuickSight Username(This can't be arn):(Hit enter to use default {}): ".format(username)) or username
principal_org_id = input("Enter AWS organization ID of the principal (Hit enter to use default {}): ".format(PrincipalOrgID)) or PrincipalOrgID
quicksight_service_role = input("Enter QuickSight Service Role (Hit enter to use default aws-quicksight-service-role-v0): ") or "aws-quicksight-service-role-v0"

s3_client = boto3.client('s3')
# Check if the bucket already exists
try:
    # Check if the bucket exists
    s3_client.head_bucket(Bucket=bucket_name)
    print("S3 bucket {} already exists".format(bucket_name))
except ClientError as e:
    # If the bucket does not exist, create it
    if e.response['Error']['Code'] == '404':
        print("S3 bucket {} does not exist. Creating...".format(bucket_name))
        s3_client.create_bucket(Bucket=bucket_name)
        # Wait for the bucket to finish creation
        s3_client.get_waiter("bucket_exists").wait(Bucket=bucket_name)
        print(f"S3 bucket {bucket_name} has been created")
    else:
        # Handle other errors
        raise

# Upload CloudFormation template to S3 bucket
s3_client = boto3.client("s3",region_name)
# Sync src directory with S3 bucket
aws_sync_command = "aws s3 sync src s3://{}/".format(bucket_name)
subprocess.call(aws_sync_command.split())

# Initialize CloudFormation stack
stack_name = "HealthEventDashboardStack"
cfn_client = boto3.client("cloudformation", region_name)

stacks = cfn_client.list_stacks(StackStatusFilter=["CREATE_FAILED"])
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

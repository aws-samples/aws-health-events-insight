import boto3
import re

# Get the default region
session = boto3.Session()
default_region = session.region_name

# Get the username details for the specified AWS account
sts_client = boto3.client("sts")
account_id = sts_client.get_caller_identity().get("Account")

# Get input parameters from user
region = input("Enter region name: (Hit enter to use default: {}): ".format(default_region)) or default_region

# Prompt the user to enter the value for the HealthEventBusArn parameter
# Get input for multiRegion Deployment
multiregion = input(f"Do you have multi region deployment for central account (yes/no): ")

PrimaryEventHealthBus = input("Enter the value for Primary EventHealth Bus: ")
if multiregion == "yes":
    SecondaryEventHealthBus = input("Enter the value for Secondary EventHealth Bus: ")
else:
    SecondaryEventHealthBus = ""

def deploy_cloudformation_template(template_path, parameters):
    cloudformation = boto3.client('cloudformation',region)
    
    with open(template_path, 'r') as file:
        template_body = file.read()
    
    stack_name = "EventHealthLink{}-{}".format(account_id,region)
    
    try:
        response = cloudformation.create_stack(
            StackName=stack_name,
            TemplateBody=template_body,
            Parameters=parameters,
            Capabilities=['CAPABILITY_NAMED_IAM']
        )
        print("CloudFormation stack creation initiated. Stack ID:", response['StackId'])
    except Exception as e:
        print("Failed to create CloudFormation stack:", str(e))

# Specify the path to the CloudFormation YAML template
template_path = 'src/ChildAccountStack/childaccount-stack.yaml'

# Input parameter values
parameters = [
    {'ParameterKey': 'PrimaryEventHealthBus','ParameterValue': PrimaryEventHealthBus},
    {'ParameterKey': 'SecondaryEventHealthBus','ParameterValue': SecondaryEventHealthBus}
    ]

deploy_cloudformation_template(template_path, parameters)

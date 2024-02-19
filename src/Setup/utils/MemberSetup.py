import boto3
import subprocess
from botocore.exceptions import ClientError
import os

# Get Current Account ID
def get_account_id():
    # Get the AWS account ID for Unique names
    sts_client = boto3.client("sts")
    account_id = sts_client.get_caller_identity().get("Account")
    return account_id

# Get yes or no for modules
def ask_yes_no(prompt):
    while True:
        user_input = input(f"{prompt} (yes/no): ").lower()
        if user_input == 'yes':
            return True
        elif user_input == 'no':
            return False
        else:
            print("Invalid input. Please enter 'yes' or 'no'.")

# Print pretty Box
def print_boxed_text(text):
    lines = text.strip().split('\n')
    max_length = max(len(line) for line in lines)
    
    print('═' * (max_length + 2))
    for line in lines:
        print(f' {line.ljust(max_length)} ')
    print('═' * (max_length + 2))


# deploy stack
def deploy_stack(command):
    try:
        subprocess.call(command, shell=True)
    except Exception as e:
        print("An error occurred:", e)

# User Input Data
def get_user_input():
    DeploymentRegionHealth = input("Enter comma-separated Region names for AWS health data collection: ")
    print_boxed_text("Data Collection Account Parameters")
    DataCollectionAccountID = input(f"Enter Data Collection Account ID, Default {get_account_id()}: ") or get_account_id()
    DataCollectionRegion = input("Enter Data Collection Region ID: ")
    MultiAccountRoleName = input("Enter MultiAccountRoleName, Hit enter to use default (MultiAccountRole): ") or "MultiAccountRole"
    ResourcePrefix = input("Enter ResourcePrefix, Hit enter to use default (Heidi-): ") or "Heidi-"
    return (
        DataCollectionAccountID, DataCollectionRegion, DeploymentRegionHealth,
        MultiAccountRoleName, ResourcePrefix
    )

# setup
def setup():
    parameters_dict = {}
    DataCollectionAccountID, DataCollectionRegion, DeploymentRegionHealth, MultiAccountRoleName, ResourcePrefix = get_user_input()

    parameters_dict['DataCollectionAccountID'] = DataCollectionAccountID
    parameters_dict['DataCollectionRegion'] = DataCollectionRegion
    parameters_dict['MultiAccountRoleName'] = MultiAccountRoleName
    parameters_dict['ResourcePrefix'] = ResourcePrefix

    parameters = f"DataCollectionAccountID={parameters_dict['DataCollectionAccountID']} \
                DataCollectionRegion={parameters_dict['DataCollectionRegion']} \
                MultiAccountRoleName={parameters_dict['MultiAccountRoleName']} \
                ResourcePrefix={parameters_dict['ResourcePrefix']}"

    for region in DeploymentRegionHealth.split(','):
        stack_name = f"Heidi-HealthModule-{get_account_id()}-{region}"
        command = f"sam deploy --stack-name {stack_name} --region {region} --parameter-overrides {parameters} \
            --template-file ../HealthModule/HealthModuleCollectionSetup.yaml --capabilities CAPABILITY_NAMED_IAM --disable-rollback"
        # Deploy Stack
        deploy_stack(command)

if __name__ == "__main__":
    setup()

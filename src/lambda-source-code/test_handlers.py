import json
import os
import unittest
from unittest.mock import MagicMock, patch
from lambda_handler import aws_health


#####################################
# Install Unittest
# python3 -m unittest test_lambda_handler.py to invoke test cases 
# Update the 3 OS variable
#####################################

class TestLambdaHandler(unittest.TestCase):

    @patch('boto3.resource')
    @patch('lambda_handler.translate_text')
    @patch('lambda_handler.summarize_event_description')
    @patch('lambda_handler.get_account_name')
    def test_aws_health(self, mock_get_account_name, mock_summarize_event_description, mock_translate_text, mock_resource):
        # Mocking the necessary dependencies
        mock_table = MagicMock()
        mock_table.put_item = MagicMock()
        mock_resource.return_value.Table.return_value = mock_table
        mock_translate_text.return_value = {"TranslatedText": "Translated Text"}
        mock_summarize_event_description.return_value = None
        mock_get_account_name.return_value = None

        # Set the environment variables
        os.environ['DynamoDBName'] = 'DummyEventTable'
        os.environ['SageMakerEndpoint'] = 'your-sagemaker-endpoint'
        os.environ['targetLang'] = 'en'

        # Read event data from file
        with open("../MockEvent.json", "r") as file:
            event = json.load(file)

        context = None

        # Execute the Lambda handler
        response = aws_health(event, context)
        print(response)

        # Assertions
        self.assertEqual(response, {'statusCode': 200, 'body': '"Successfully inserted item into DynamoDB"'})
        mock_translate_text.assert_called_once()
        mock_summarize_event_description.assert_called_once()
        mock_get_account_name.assert_called_once()

        # Clean up the environment variables
        del os.environ['DynamoDBName']
        del os.environ['SageMakerEndpoint']
        del os.environ['targetLang']

if __name__ == '__main__':
    unittest.main()

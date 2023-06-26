# Webhook to consume third party events

This sample solution enables you to ingest third-party events. If you choose to enable the webhook option, CloudFormation (cfn) will deploy an HTTP API on API Gateway and integrate it with EventBridge. You can send events to EventBridge from a third-party source using the following format. You can also bring your own format, you may have to update ingestion lambda in that case.


# Sample event format: You can send event to APIGW in EB format.

The Sample is specifically created to receive data from two sources, namely awshealthtest and aws.health. If you wish to provide a different source for a third party, you need to modify the eventbridge rule and include the additional source type. Additionally, if your JSON payload differs, you may also want to adjust the integration detail for the route in apigw e.g. Detail : "$request.body.data.essentials" for Azure. 

**Warning** To impose access restrictions who can post events to this API, navigate to the API GW console and incorporate an authorizer based on your specific requirements.

```json
{
"source":"awshealthtest",
"DetailType": "awshealthtest", 
"Detail": {
"eventArn":"MockEvent-from third party",
"service":"WORKSPACES",
"eventScopeCode":"ACCOUNT_SPECIFIC",
"communicationId":"8f7ef91f0c9f2f3e3f68dffd0fa34fe299e56f323f06154df1de185d0e3f49bf",
"lastUpdatedTime":"Wed, 3 May 2023 13:30:55 GMT",
"eventRegion":"us-east-1",
"eventTypeCode":"EC2",
"eventTypeCategory":"issue",
"startTime":"Wed, 3 May 2023 11:00:00 GMT",
"eventDescription":[{
         "language":"en_US",
         "latestDescription":"MockEvent\n"
         }],
   "affectedEntities":[{
    "entityValue":"i-mockevent"
    }]
        }   
}
```

# Sample command to send event

```json
curl --location --request POST 'invoke url' --header 'Content-Type: application/json' --data-raw '{
"source":"awshealthtest",
"DetailType": "awshealthtest", 
"Detail": {
"eventArn":"MockEvent-from third party -2",
"service":"WORKSPACES",
"eventScopeCode":"ACCOUNT_SPECIFIC",
"communicationId":"8f7ef91f0c9f2f3e3f68dffd0fa34fe299e56f323f06154df1de185d0e3f49bf",
"lastUpdatedTime":"Wed, 3 May 2023 13:30:55 GMT",
"eventRegion":"us-east-1",
"eventTypeCode":"EC2",
"eventTypeCategory":"issue",
"startTime":"Wed, 3 May 2023 11:00:00 GMT",
"eventDescription":[{
         "language":"en_US",
         "latestDescription":"MockEvent\n"
         }],
   "affectedEntities":[{
    "entityValue":"i-mockevent"
    }]
        }   
}'



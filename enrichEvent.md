# Enrich AWS Health Events

You can enrich AWS Health Events with additional data such as Resource Tags, Resource Arn, Resource Availability Zone etc. Heidi Solution uses an AWS Config to extract the resource configuration through configuration snapshots. 

AWS Config delivers configuration snapshots of the AWS resources that AWS Config is recording to the Amazon S3 bucket that you specified when you configured your delivery channel. You need a centralized system to collect configuration snapshots from multiple accounts. Customers are using these main approches.

1. Configure delivery channel to centralized Amazon S3 bucket. When Amazon S3 bucket that belongs to another AWS account, that bucket must have policies that grant access permissions to AWS Config. 
2. Replicate all AWS Config delivery Amazon S3 buckets buckets from different accounts to centerlized Amazon S3 bucket.

# Reading

![Granting AWS Config access to the Amazon S3 Bucket](https://docs.aws.amazon.com/config/latest/developerguide/s3-bucket-policy.html#granting-access-in-another-account)

![configuration history and configuration snapshot files](https://aws.amazon.com/blogs/mt/configuration-history-configuration-snapshot-files-aws-config/)

![recreate AWS Config delivery channel](https://repost.aws/knowledge-center/recreate-config-delivery-channel)

![Enable frequency of config snapshot](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-config-deliverychannel.html)

# Limitation
The data obtained from AWS Health events occasionally arrives in a non-ARN format. AWS Heidi conducts a comparison of the Affected Entity with the resourceName, ResourceID, and ResourceArn. This could return multiple rows. There might be duplicate tags with entities with duplicate names. Cross check AWS Config aggregator with following query. Go to aggregator account, nevigate to  AWS Config Console run following in query editor. 

`SELECT * WHERE resourceId = '<affectedEntity>' or resourceName = '<affectedEntity>' or arn = '<affectedEntity>'`

We recognize this constraint and are actively addressing it.
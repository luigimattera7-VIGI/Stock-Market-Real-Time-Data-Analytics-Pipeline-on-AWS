# Deployment Guide

This guide provides step-by-step instructions for deploying the Stock Market Analytics Pipeline on AWS.

## Prerequisites

- AWS CLI configured with appropriate credentials
- Python 3.8+ installed locally
- IAM permissions to create Kinesis, Lambda, DynamoDB, S3, and SNS resources

## 1. Create AWS Resources

### 1.1 Create Kinesis Stream

```bash
# Create Kinesis stream
aws kinesis create-stream \
  --stream-name stock-market-stream \
  --shard-count 1 \
  --region us-east-1

# Verify stream creation
aws kinesis describe-stream \
  --stream-name stock-market-stream \
  --region us-east-1
```

### 1.2 Create DynamoDB Table

```bash
# Create DynamoDB table
aws dynamodb create-table \
  --table-name stock-market-data \
  --attribute-definitions \
    AttributeName=symbol,AttributeType=S \
    AttributeName=timestamp,AttributeType=S \
  --key-schema \
    AttributeName=symbol,KeyType=HASH \
    AttributeName=timestamp,KeyType=RANGE \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1

# Verify table creation
aws dynamodb describe-table \
  --table-name stock-market-data \
  --region us-east-1
```

### 1.3 Create S3 Bucket

```bash
# Create S3 bucket (bucket names must be globally unique)
aws s3 mb s3://stock-market-data-bucket-$(date +%s) \
  --region us-east-1

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket stock-market-data-bucket-xxxxx \
  --versioning-configuration Status=Enabled \
  --region us-east-1

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket stock-market-data-bucket-xxxxx \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }' \
  --region us-east-1
```

### 1.4 Create IAM Role

```bash
# Create trust policy document
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name StockMarketLambdaRole \
  --assume-role-policy-document file://trust-policy.json

# Attach policies
aws iam attach-role-policy \
  --role-name StockMarketLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonKinesisFullAccess

aws iam attach-role-policy \
  --role-name StockMarketLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonDynamoDBFullAccess

aws iam attach-role-policy \
  --role-name StockMarketLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AWSLambdaBasicExecutionRole

aws iam attach-role-policy \
  --role-name StockMarketLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonS3FullAccess

aws iam attach-role-policy \
  --role-name StockMarketLambdaRole \
  --policy-arn arn:aws:iam::aws:policy/AmazonSNSFullAccess

# Verify role creation
aws iam get-role --role-name StockMarketLambdaRole
```

## 2. Deploy Data Producer (Step 1)

```bash
# Navigate to Step1
cd Step1

# Install dependencies
pip install -r requirements.txt

# Configure the script
# Edit stream_stock_data.py to set:
# - STREAM_NAME = "stock-market-stream"
# - STOCK_SYMBOL = "USDCLP=X" (or your desired stock)
# - Region: "sa-east-1" or your region

# Run the producer
python stream_stock_data.py
```

**Note**: Keep this running in the background. Consider using systemd, supervisor, or EC2 for production.

## 3. Deploy Lambda Functions

### 3.1 Package and Deploy Data Processing Lambda (Step 2)

```bash
# Navigate to Step2
cd ../Step2

# Create deployment package
pip install -r ../Step1/requirements.txt -t package/
cp lambda_function.py package/
cd package
zip -r ../lambda_deployment.zip .
cd ..

# Deploy Lambda function
ROLE_ARN=$(aws iam get-role --role-name StockMarketLambdaRole --query 'Role.Arn' --output text)

aws lambda create-function \
  --function-name StockMarketProcessor \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 60 \
  --memory-size 256 \
  --region us-east-1 \
  --environment Variables='{
    DYNAMO_TABLE=stock-market-data,
    S3_BUCKET=stock-market-data-bucket-xxxxx
  }'

# Configure Kinesis trigger
STREAM_ARN=$(aws kinesis describe-stream \
  --stream-name stock-market-stream \
  --query 'StreamDescription.StreamARN' \
  --output text \
  --region us-east-1)

aws lambda create-event-source-mapping \
  --event-source-arn $STREAM_ARN \
  --function-name StockMarketProcessor \
  --enabled \
  --starting-position LATEST \
  --region us-east-1
```

### 3.2 Deploy Alerting Lambda (Step 4)

```bash
# Navigate to Step4
cd ../Step4

# Create deployment package
pip install -r ../Step1/requirements.txt -t package/
cp lambda_function.py package/
cd package
zip -r ../lambda_deployment.zip .
cd ..

# Deploy Lambda function
aws lambda create-function \
  --function-name StockMarketAlerter \
  --runtime python3.11 \
  --role $ROLE_ARN \
  --handler lambda_function.lambda_handler \
  --zip-file fileb://lambda_deployment.zip \
  --timeout 60 \
  --memory-size 256 \
  --region us-east-1 \
  --environment Variables='{
    SNS_TOPIC_ARN=arn:aws:sns:us-east-1:xxxxx:stock-alerts
  }'
```

## 4. Create SNS Topic for Alerts

```bash
# Create SNS topic
aws sns create-topic --name stock-alerts --region us-east-1

# Get topic ARN
SNS_TOPIC_ARN=$(aws sns list-topics --query 'Topics[?TopicArn.contains(@, `stock-alerts`)].TopicArn' --output text --region us-east-1)

# Subscribe email
aws sns subscribe \
  --topic-arn $SNS_TOPIC_ARN \
  --protocol email \
  --notification-endpoint your-email@example.com \
  --region us-east-1
```

## 5. Set Up Athena for Querying

```bash
# Create Athena database
aws athena start-query-execution \
  --query-string "CREATE DATABASE IF NOT EXISTS stock_market;" \
  --query-execution-context Database=default \
  --result-configuration OutputLocation=s3://stock-market-data-bucket-xxxxx/athena-results/ \
  --region us-east-1

# Create external table using schema from Step3/schema.json
aws athena start-query-execution \
  --query-string "$(cat Step3/schema.json)" \
  --query-execution-context Database=stock_market \
  --result-configuration OutputLocation=s3://stock-market-data-bucket-xxxxx/athena-results/ \
  --region us-east-1
```

## 6. Monitoring and Testing

### Monitor Kinesis Stream

```bash
# Check stream status
aws kinesis describe-stream --stream-name stock-market-stream --region us-east-1

# Get records from stream
aws kinesis get-shard-iterator \
  --stream-name stock-market-stream \
  --shard-id shardId-000000000000 \
  --shard-iterator-type LATEST \
  --region us-east-1
```

### Monitor Lambda Logs

```bash
# View recent logs for data processor
aws logs tail /aws/lambda/StockMarketProcessor --follow --region us-east-1

# View recent logs for alerter
aws logs tail /aws/lambda/StockMarketAlerter --follow --region us-east-1
```

### Query DynamoDB

```bash
# Scan recent items
aws dynamodb scan \
  --table-name stock-market-data \
  --limit 10 \
  --region us-east-1
```

## 7. Cleanup

To remove all resources and avoid costs:

```bash
# Delete Lambda functions
aws lambda delete-function --function-name StockMarketProcessor --region us-east-1
aws lambda delete-function --function-name StockMarketAlerter --region us-east-1

# Delete DynamoDB table
aws dynamodb delete-table --table-name stock-market-data --region us-east-1

# Delete Kinesis stream
aws kinesis delete-stream --stream-name stock-market-stream --region us-east-1

# Delete S3 bucket (must be empty first)
aws s3 rm s3://stock-market-data-bucket-xxxxx --recursive
aws s3 rb s3://stock-market-data-bucket-xxxxx

# Delete IAM role
aws iam detach-role-policy --role-name StockMarketLambdaRole --policy-arn arn:aws:iam::aws:policy/AmazonKinesisFullAccess
# (Repeat for all attached policies)
aws iam delete-role --role-name StockMarketLambdaRole

# Delete SNS topic
aws sns delete-topic --topic-arn $SNS_TOPIC_ARN --region us-east-1
```

## Troubleshooting Deployment

### Lambda Execution Role Issues
```bash
# Verify role has correct permissions
aws iam list-attached-role-policies --role-name StockMarketLambdaRole
```

### Kinesis Stream Not Receiving Data
```bash
# Check if producer is running and configured correctly
# Verify stream name and region match configuration
```

### DynamoDB Throttling
```bash
# Switch to on-demand billing
aws dynamodb update-billing-mode \
  --table-name stock-market-data \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

## Production Considerations

1. **High Availability**: Use multiple shards in Kinesis
2. **Auto-scaling**: Enable DynamoDB auto-scaling
3. **Data Retention**: Configure S3 lifecycle policies
4. **Monitoring**: Set up CloudWatch alarms
5. **Logging**: Enable VPC Flow Logs and CloudTrail
6. **Cost**: Monitor AWS costs regularly

## Support

For issues during deployment, check:
- CloudWatch Logs
- IAM permissions
- AWS service quotas
- AWS Documentation

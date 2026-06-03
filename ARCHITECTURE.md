# Architecture Documentation

## System Overview

The Stock Market Real-Time Data Analytics Pipeline is a serverless, event-driven architecture on AWS that ingests, processes, and analyzes real-time stock market data.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Data Streaming Layer                          │
│  ┌──────────────┐                                                 │
│  │   yfinance   │ ──► USDCLP=X, AAPL, GOOGL, etc.               │
│  └──────────────┘                                                 │
│         │                                                         │
│         ▼                                                         │
│  ┌──────────────────────────────────────────────────────┐       │
│  │  Step1: stream_stock_data.py (Local/EC2)            │       │
│  │  • Fetches stock data every 30 seconds               │       │
│  │  • Calculates technical indicators                   │       │
│  │  • Streams to Kinesis                                │       │
│  └──────────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│           Real-time Stream Processing Layer                      │
│  ┌──────────────────────────────────────────────────────┐       │
│  │   Amazon Kinesis Data Streams                        │       │
│  │   • Stream Name: stock-market-stream                 │       │
│  │   • Shards: Configurable (1+)                        │       │
│  │   • Retention: 24 hours (default)                    │       │
│  └──────────────────────────────────────────────────────┘       │
│         │                      │                                 │
│         ▼                      ▼                                 │
│  ┌─────────────────┐   ┌─────────────────┐                     │
│  │ Step2 Lambda    │   │ (Optional)      │                     │
│  │ Processor       │   │ Consumer        │                     │
│  └─────────────────┘   └─────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              Processing & Storage Layer                          │
│                                                                  │
│  ┌────────────────┐              ┌──────────────────┐           │
│  │  Anomaly       │              │  Data Storage    │           │
│  │  Detection     │              │                  │           │
│  │  • >5% change  │              │  ┌────────────┐  │           │
│  │  • Metrics     │──────┬───────►│  │ DynamoDB   │  │           │
│  │  • Validation  │      │       │  │ Table      │  │           │
│  └────────────────┘      │       │  │ (Processed)│  │           │
│                          │       │  └────────────┘  │           │
│                          │       │                  │           │
│                          └──────►│  ┌────────────┐  │           │
│                                  │  │ S3 Bucket  │  │           │
│                                  │  │ (Raw Data) │  │           │
│                                  │  └────────────┘  │           │
│                                  └──────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│            Alerting & Analytics Layer                            │
│                                                                  │
│  ┌────────────────┐       ┌────────────────┐                   │
│  │ Step4 Lambda   │       │  Athena        │                   │
│  │ Alerter        │       │  Query Engine  │                   │
│  │                │       │                │                   │
│  │ Triggers SNS   │       │ Historical     │                   │
│  │ Notifications  │       │ Analysis       │                   │
│  └────────────────┘       └────────────────┘                   │
│         │                         │                             │
│         ▼                         ▼                             │
│  ┌─────────────────────────────────────────┐                  │
│  │  SNS Topic: stock-alerts                │                  │
│  │  • Email notifications                  │                  │
│  │  • SMS alerts                           │                  │
│  │  • Custom subscribers                   │                  │
│  └─────────────────────────────────────────┘                  │
└─────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Data Producer (Step1)

**File**: `Step1/stream_stock_data.py`

**Purpose**: Fetches real-time stock data and streams it to Kinesis

**Key Functions**:
```python
get_stock_data(symbol) -> dict
    │ Fetches stock OHLCV data
    │ Calculates price change
    │ Returns structured stock data
    │
send_to_kinesis() -> None
    │ Continuously fetches data
    │ Sends to Kinesis every 30 seconds
```

**Data Structure**:
```json
{
  "symbol": "USDCLP=X",
  "open": 800.50,
  "high": 805.25,
  "low": 798.75,
  "price": 802.00,
  "previous_close": 801.00,
  "change": 1.00,
  "change_percent": 0.12,
  "volume": 1000000,
  "timestamp": "2024-06-03T14:30:00Z"
}
```

### 2. Data Processing Lambda (Step2)

**File**: `Step2/lambda_function.py`

**Trigger**: Kinesis stream events (batch)

**Purpose**: Process stock data, detect anomalies, store in dual formats

**Workflow**:
```
Kinesis Record
    │
    ├─► Decode Base64 data
    │
    ├─► Extract payload
    │
    ├─► Store to S3 (raw)
    │   └─ Path: raw-data/{symbol}/{timestamp}.json
    │
    ├─► Calculate metrics
    │   ├─ Price change %
    │   ├─ Moving average
    │   └─ Anomaly flag (>5%)
    │
    └─► Store to DynamoDB (processed)
        └─ Partition Key: symbol
        └─ Sort Key: timestamp
```

**Environment Variables**:
- `DYNAMO_TABLE`: DynamoDB table name
- `S3_BUCKET`: S3 bucket for raw data

### 3. Schema Definition (Step3)

**File**: `Step3/schema.json`

**Purpose**: Defines Athena table schema for S3 data querying

**Fields**:
| Field | Type | Purpose |
|-------|------|---------|
| symbol | string | Stock ticker |
| timestamp | string | Event timestamp (ISO 8601) |
| open | double | Opening price |
| high | double | Highest price |
| low | double | Lowest price |
| price | double | Current/closing price |
| previous_close | double | Previous close price |
| volume | bigint | Trading volume |

### 4. Alert Lambda (Step4)

**File**: `Step4/lambda_function.py`

**Trigger**: CloudWatch Events / DynamoDB Streams

**Purpose**: Send SNS notifications for anomalous movements

**Logic**:
```
Monitor DynamoDB / Events
    │
    ├─► Filter anomalies (is_anomaly = "Yes")
    │
    ├─► Format alert message
    │   └─ Include: symbol, change %, threshold
    │
    ├─► Check throttling (avoid alert spam)
    │
    └─► Publish to SNS
        └─ Recipients: Email, SMS
```

## AWS Services Used

| Service | Purpose | Config |
|---------|---------|--------|
| **Kinesis** | Real-time data streaming | 1 shard, 24hr retention |
| **Lambda** | Serverless compute | 256 MB, 60s timeout |
| **DynamoDB** | NoSQL data store | On-demand billing |
| **S3** | Object storage | Encrypted, versioned |
| **Athena** | SQL queries on S3 | Glue Catalog integration |
| **SNS** | Notifications | Email/SMS subscriptions |
| **CloudWatch** | Logging/Monitoring | Automatic Lambda logs |
| **IAM** | Access control | Role-based permissions |

## Data Flow

### Real-time Path
```
yfinance
   ↓
stream_stock_data.py (Step1)
   ↓
Kinesis Stream
   ↓
Lambda Processor (Step2)
   ├─→ S3 (raw data)
   └─→ DynamoDB (processed)
       ↓
Lambda Alerter (Step4)
       ↓
SNS
```

### Analytics Path
```
S3 (raw data)
   ↓
Glue Crawler (auto-discovery)
   ↓
Athena Tables
   ↓
SQL Queries
   ↓
Analytics Results
```

## Scalability Considerations

### Horizontal Scaling
- **Kinesis**: Increase shard count for higher throughput
- **Lambda**: Auto-scales with concurrent executions
- **DynamoDB**: On-demand billing scales automatically
- **S3**: Unlimited capacity

### Vertical Scaling
- **Lambda Memory**: 128 MB to 10,240 MB
- **Timeout**: Up to 15 minutes

### Optimization Tips
- Batch records in Lambda
- Use Kinesis batch settings
- Enable Lambda reserved concurrency
- S3 partitioning by date/symbol

## Performance Metrics

### Latency
- Data producer to Kinesis: ~100ms
- Kinesis to Lambda: ~1-2 seconds
- Lambda processing: ~200-500ms
- DynamoDB write: ~10-50ms
- SNS delivery: ~1-5 seconds

**End-to-end latency**: ~3-10 seconds

### Throughput
- Kinesis (1 shard): ~1,000 records/second
- Lambda: Scales with concurrent executions
- DynamoDB: On-demand mode
- S3: Unlimited

### Cost Estimation (Monthly)
| Service | Usage | Cost |
|---------|-------|------|
| Kinesis | 1M records | $0.50 |
| Lambda | 10M invocations | $0.20 |
| DynamoDB | 10GB stored | $1.25 |
| S3 | 100GB stored | $2.30 |
| **Total** | | **~$4.25** |

*Costs vary by region and usage pattern*

## Security Architecture

### Authentication
- IAM roles for Lambda functions
- AWS credentials for local producer

### Authorization
- Least-privilege IAM policies
- Resource-level permissions

### Encryption
- S3: AES-256 encryption at rest
- Kinesis: Optional KMS encryption
- DynamoDB: Optional KMS encryption
- Transit: HTTPS/TLS

### Audit
- CloudTrail logging
- VPC Flow Logs
- S3 Access Logs
- CloudWatch Logs

## Disaster Recovery

### Backups
- S3 versioning enabled
- Cross-region replication (optional)
- Athena external tables

### Recovery
- S3 restore from versions
- DynamoDB point-in-time recovery
- Lambda function versions/aliases

### RTO/RPO
- **RTO**: ~5 minutes (recreate resources)
- **RPO**: ~1 minute (latest DynamoDB state)

## Monitoring & Alerts

### Key Metrics
- Kinesis: GetRecords latency, Iterator age
- Lambda: Duration, Errors, Throttles
- DynamoDB: ConsumedWriteCapacity, FailedToPutItem
- S3: 4xx/5xx Errors, Latency

### CloudWatch Alarms
```
- Lambda Errors > 5 per minute → Alert
- DynamoDB Throttling → Alert
- Kinesis Iterator Age > 60s → Alert
- S3 4xx Errors > 10 per minute → Alert
```

## Future Enhancements

- [ ] Multi-region deployment
- [ ] Real-time dashboard (QuickSight)
- [ ] Advanced ML anomaly detection
- [ ] API Gateway for external access
- [ ] EventBridge for workflow orchestration
- [ ] Step Functions for complex workflows
- [ ] Terraform/CDK for infrastructure as code

---

**Architecture Version**: 1.0  
**Last Updated**: June 2024

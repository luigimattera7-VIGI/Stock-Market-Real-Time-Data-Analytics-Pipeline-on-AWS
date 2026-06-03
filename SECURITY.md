# Security Policy

## Supported Versions

We release patches for security vulnerabilities.

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, please report them to: **security@yourproject.dev** (or create a private security advisory)

Please include the following details when reporting:

- Type of issue (e.g., credential exposure, injection vulnerability)
- Location of the vulnerability (file, function, etc.)
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### What to expect:

1. You will receive a response within 48 hours
2. We will work on a fix and provide updates
3. We'll coordinate a disclosure timeline with you
4. Your name will be credited in the security advisory (if desired)

## Security Best Practices

When using this project:

### 1. Credentials & Secrets
- **NEVER** commit AWS credentials, API keys, or passwords
- Use AWS IAM roles and instance profiles in production
- Use `aws configure` with temporary credentials
- Store sensitive values in AWS Secrets Manager or Parameter Store
- The `.env` file is in `.gitignore` - use it for local development only

### 2. AWS Configuration
- Use least-privilege IAM policies
- Enable CloudTrail for audit logging
- Enable S3 bucket encryption (AES-256 or KMS)
- Enable versioning on S3 buckets
- Use VPC endpoints for private AWS service access
- Enable MFA on AWS account root user

### 3. Network Security
- Restrict Lambda execution to specific VPCs if needed
- Use security groups to limit Kinesis access
- Enable VPC Flow Logs
- Consider using PrivateLink for AWS service endpoints

### 4. Data Protection
- Enable S3 bucket encryption at rest
- Use HTTPS/TLS for data in transit
- Implement S3 access logging
- Use server-side encryption for DynamoDB items
- Consider data retention and deletion policies

### 5. Application Security
- Keep dependencies up to date: `pip install --upgrade boto3 yfinance`
- Use input validation for stock symbols
- Implement rate limiting
- Log all significant events
- Use CloudWatch for monitoring and alerting

### 6. Monitoring & Logging
- Review CloudWatch Logs regularly
- Set up CloudWatch alarms for anomalies
- Monitor Lambda execution errors
- Track DynamoDB throttling events
- Review S3 access logs

## Dependency Security

We use these external dependencies:

- **boto3**: AWS SDK for Python - [GitHub](https://github.com/boto/boto3)
- **yfinance**: Financial data downloader - [GitHub](https://github.com/ranaroussi/yfinance)

Keep these updated:
```bash
pip install --upgrade boto3 yfinance
```

Check for known vulnerabilities:
```bash
pip install safety
safety check
```

## Vulnerability Disclosure Process

1. **Report**: Contact us privately with vulnerability details
2. **Acknowledge**: We'll acknowledge within 48 hours
3. **Assessment**: We'll evaluate the severity and impact
4. **Fix**: We'll create and test a security patch
5. **Release**: We'll release a patched version
6. **Disclosure**: We'll publish a security advisory
7. **Credit**: We'll credit the reporter (unless they prefer anonymity)

## Known Security Considerations

### Current Limitations
- Public S3 bucket access requires careful configuration
- DynamoDB items are not encrypted by default
- Kinesis data is not encrypted by default (enable with service-side encryption)

### Recommendations
- Use AWS KMS for encryption of sensitive data
- Implement API Gateway with authentication
- Use AWS WAF for web application firewall protection
- Consider AWS GuardDuty for threat detection

## Compliance

This project should be used in compliance with:
- AWS Security Best Practices
- Data protection regulations (GDPR, CCPA, etc.)
- Your organization's security policies
- Financial data regulations if applicable

## Changelog

All security updates are documented in [CHANGELOG.md](CHANGELOG.md)

## Questions?

Contact us through:
- GitHub Issues (for non-security questions)
- Email: security@yourproject.dev
- GitHub Security Advisories: Private vulnerability reporting

---

**Last Updated**: June 2024

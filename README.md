# EventBridge Rule & Lambda Setup for ECS Service Refresh

Created a set up for **AWS EventBridge Rule** and an **AWS Lambda function** to automatically refresh an ECS service when AWS announces upcoming **ECS Task Patching Retirement** events.

## Overview
- **EventBridge Rule** listens for AWS ECS Task Patching Retirement events.
- **Lambda Function** triggers an ECS service refresh when an event occurs.
- **IAM Role** is created for the Lambda function with necessary permissions.
- **Terraform** is used to automate the setup.

## AWS Setup

### 1️⃣ Create IAM Role for Lambda
Created an **IAM Role** and attached the following policies:
- `AWSLambdaBasicExecutionRole`
- `AmazonECS_FullAccess`

### 2️⃣ Create the Lambda Function
- **Runtime:** Python 3.12
- **Deployment Package:** Zip file containing Lambda code

#### Lambda Code (Python 3.12)
```python
import json
import boto3

ecs_client = boto3.client('ecs')

CLUSTER_NAME = "poc-test-cluster"
SERVICE_NAME = "nginx-service"

def lambda_handler(event, context):
    print("Lambda Function Triggered!!")
    try:
        response = ecs_client.update_service(
            cluster=CLUSTER_NAME,
            service=SERVICE_NAME,
            forceNewDeployment=True
        )
        print("Service Refresh Triggered")
        return {
            'message': 'ECS Service refresh triggered successfully',
            'response': response
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}
```

### 3️⃣ Create EventBridge Rule
This rule listens for **AWS Health Events** related to ECS task retirements:
```json
{
  "source": ["custom.ecs.retirement"],
  "detail-type": ["AWS Health Event"],
  "detail": {
    "service": ["ECS"],
    "eventTypeCode": ["AWS_ECS_TASK_PATCHING_RETIREMENT"],
    "eventStatusCode": ["upcoming"]
  }
}
```

### 4️⃣ Manually Trigger EventBridge for Testing
To simulate an AWS Health Event and invoke the Lambda function:
```sh
aws events put-events --entries '[
  {
    "Source": "custom.ecs.retirement",
    "DetailType": "AWS Health Event",
    "Detail": "{ \"service\": \"ECS\", \"eventTypeCode\": \"AWS_ECS_TASK_PATCHING_RETIREMENT\", \"eventStatusCode\": \"upcoming\", \"affectedEntities\": [{ \"entityValue\": \"arn:aws:<account-id>>:service/test-cluster/nginx-service\" }] }",
    "EventBusName": "default"
  }
]'
```

## Terraform Commands Used
Below are the essential Terraform commands used to manage the infrastructure:
```sh
terraform init            # Initialize Terraform
terraform validate        # Validate Terraform configuration
terraform plan            # Preview changes before applying
terraform apply           # Apply changes
terraform refresh         # Sync state with real infrastructure
terraform state show      # Inspect resource states
```



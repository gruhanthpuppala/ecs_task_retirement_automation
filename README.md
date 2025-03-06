# EventBridge Rule & Lambda Setup for ECS Service Refresh

Created a set up to automate the Service-Refreshment for upcoming ECS Task Retirements with **AWS Lambda function** to automatically refresh an ECS service when AWS announces upcoming **ECS Task Patching Retirement** events.

## Overview
- **EventBridge Rule** listens for AWS ECS Task Patching Retirement events.
- **Lambda Refresh Function** triggers an ECS service refresh when an event occurs.
  - Get the input data from event bridge (Triggered AWS Health event).
  - Pull in the input and extract the required details from the event.
  - Iterate through each value and does:
    - Check the service status for the current entity.
    - If any on-going activity detected on this service, it stops executing the remaining script and iterate for the next one.
    - If this is stable and no on-going deployments detected it check for any alarms associated with it (CPU Utilization alarm) if any disable this alarm.
    - Preform the refresh to this respective service.
    - Right after the refresh it triggers a custom API event containing the respective service/cluster/region details to check the status post refreshment.
      - This custom API is given as a input to another lambda function (lambda_post_refresh_function).
  - Iterates for all events same as above mentioned.
- **IAM Role for Lambda Refresh Function** is created for the Lambda function with necessary permissions.
  - Set the Inline permission to disable / describe alarm.
  - Grant ECS full access policy.
  - Grant LambdaBasicExecutionRole.
  - Set custom inline policy to put events for lambda.
- **Step Function** is used to introduce certain amount of delay post refreshment for a service is triggered. 
- **Lambda Post Refrsh Function** this check's the state of the service and enable the alarms post service is stable.
  - Get the input from step function retrive the input (service/cluster/region).
  - Check the service is stable
    - If service is stable enable the alarm.
    - If service is not stable (logs service is not stable) notifies via slack.
- **Terraform** is used to automate the setup.

<!---
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
    "Detail": "{ \"service\": \"ECS\", \"eventTypeCode\": \"AWS_ECS_TASK_PATCHING_RETIREMENT\", \"eventStatusCode\": \"upcoming\", \"affectedEntities\": [{ \"entityValue\": \"arn:aws:ecs:us-east-1:013545207027:service/poc-test-cluster/nginx-service\" }] }",
    "EventBusName": "default"
  }
]'
```
-->
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
<!---
### **Automation Workflow**
![Description](https://github.com/cb-gruhanthpuppala/cb-cloudops-automations/blob/main/lambda-eventbridge-terraform-scripts/assets/ecs-task-retirement-automation-flowchart.png?raw=true)
--->
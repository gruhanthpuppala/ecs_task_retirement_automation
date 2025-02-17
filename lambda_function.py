import json
import boto3

ecs_client = boto3.client("ecs")

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
            "message": "ECS Service refresh triggered successfully",
            "response": response
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": str(e)}

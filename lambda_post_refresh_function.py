import json
import boto3
import time
from botocore.exceptions import ClientError

# AWS Clients
cloudwatch_client = boto3.client('cloudwatch')

def enable_cloudwatch_alarms(service_name, region):
    """Enables only ECS CPUUtilization CloudWatch alarms for the given service if stable."""
    print(f"🔍 Checking CloudWatch CPU Utilization alarms to enable for {service_name} in {region}")

    try:
        # Fetch CloudWatch alarms filtering for ECS CPU Utilization
        response = cloudwatch_client.describe_alarms()

        # Filter alarms specific to the service and with MetricName = CPUUtilization
        alarms_to_enable = [
            alarm["AlarmName"] for alarm in response.get("MetricAlarms", [])
            if alarm["MetricName"] == "CPUUtilization" and
               any(dim["Name"] == "ServiceName" and dim["Value"] == service_name for dim in alarm.get("Dimensions", []))
        ]

        if not alarms_to_enable:
            print(f"✅ No CloudWatch CPU Utilization alarms found for {service_name} to enable.")
            return

        print(f"🚀 Found CloudWatch CPU Utilization alarms to enable for {service_name}: {alarms_to_enable}")

        # Enable only CPU Utilization alarms
        cloudwatch_client.enable_alarm_actions(AlarmNames=alarms_to_enable)
        print(f"✅ Enabled CloudWatch CPU Utilization alarms for {service_name}")

    except ClientError as e:
        print(f"❌ AWS Error enabling CloudWatch alarms: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"❌ General Error enabling alarms: {str(e)}")


def lambda_handler(event, context):
    print("🚀 Received Event (RAW):", json.dumps(event, indent=4))

    # ✅ Extract necessary fields
    cluster_name = event.get("clusterName")
    refreshed_services = event.get("refreshed_services", [])
    region = event.get("region", "us-east-1")

    # Validate input
    if not cluster_name or not refreshed_services:
        print("❌ ERROR: Missing cluster or service names in event!")
        return {"status": "error", "message": "Missing cluster or service names in event"}

    # Ensure refreshed_services is a list
    if isinstance(refreshed_services, str):
        refreshed_services = [refreshed_services]

    # Initialize ECS client
    ecs_client = boto3.client('ecs', region_name=region)

    print(f"🔍 Checking ECS service status for: {refreshed_services} in cluster {cluster_name}")

    try:
        # Describe all refreshed services at once
        response = ecs_client.describe_services(
            cluster=cluster_name,
            services=refreshed_services
        )

        service_status_list = []

        if "services" in response:
            for service in response["services"]:
                service_name = service["serviceName"]
                running_tasks = service.get("runningCount", 0)
                pending_tasks = service.get("pendingCount", 0)
                desired_tasks = service.get("desiredCount", 0)

                print(f"\n📊 **ECS Service Status for {service_name}**:")
                print(f"  - 🟢 Running Tasks: {running_tasks}")
                print(f"  - 🟡 Pending Tasks: {pending_tasks}")
                print(f"  - 🔵 Desired Tasks: {desired_tasks}")

                is_stable = running_tasks == desired_tasks

                service_status_list.append({
                    "serviceName": service_name,
                    "runningCount": running_tasks,
                    "pendingCount": pending_tasks,
                    "desiredCount": desired_tasks,
                    "isStable": is_stable
                })

                if is_stable:
                    print(f"✅ Service {service_name} is now stable! Enabling CloudWatch alarms.")
                    enable_cloudwatch_alarms(service_name, region)
                else:
                    print(f"⚠️ Service {service_name} is NOT stable yet. Skipping alarm re-enablement.")

        else:
            print("❌ No services found in the response.")

        return {
            "status": "completed",
            "service_status": service_status_list
        }

    except Exception as e:
        print(f"❌ ERROR fetching ECS service state: {str(e)}")
        return {"status": "error", "message": str(e)}

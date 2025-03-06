import json
import boto3
import time
from datetime import datetime
from botocore.exceptions import ClientError

# AWS Clients
# stepfunctions_client = boto3.client('stepfunctions', region_name='us-east-1')
eventbridge_client = boto3.client('events', region_name='us-east-1')
cloudwatch_client = boto3.client('cloudwatch', region_name=region)

def send_event_to_eventbridge(cluster_name, service_name, region):
    """Sends an event to EventBridge to track ECS service status."""
    print(f"⏳ Sending EventBridge event for {service_name} in {cluster_name}, to check service status post refreshment")

    response = eventbridge_client.put_events(
        Entries=[
            {
                'Source': 'custom.ecs.check-status',
                'DetailType': 'ECS Service Status Check',
                'Detail': json.dumps({
                    "clusterName": cluster_name,
                    "serviceName": service_name,
                    "region": region
                }),
                'EventBusName': 'default',
                'Time': datetime.utcnow()
            }
        ]
    )
    print(f"✅ EventBridge event sent successfully for {service_name}: {response} to check the status post refresment trigger. This will check the status of the service after 5 mints.")
    time.sleep(2)

def check_service_status(cluster_name, service_name, region):
    """Checks ECS service status in the given cluster and region."""
    print(f"🔍 Checking status of {service_name} in {cluster_name} (Region: {region})")
    ecs_client = boto3.client('ecs', region_name=region)

    try:
        response = ecs_client.describe_services(cluster=cluster_name, services=[service_name])

        if "services" not in response or not response["services"]:
            print(f"❌ No services found for {service_name} in cluster {cluster_name}")
            return False 

        service = response['services'][0]
        running_tasks = service.get("runningCount", 0)
        pending_tasks = service.get("pendingCount", 0)
        deployments = service.get("deployments", [])
        desired_count = service.get("desiredCount", 0)

        print(f"Service Status: Running={running_tasks}, Pending={pending_tasks}, Deployments={len(deployments)}, DesiredCount={desired_count}")

        if len(deployments) == 1:
            deployment = deployments[0]
            rollout_state = deployment.get("rolloutState", "")
            deployment_status = deployment.get("status", "")

            if rollout_state == "COMPLETED" and deployment_status == "PRIMARY" and running_tasks == desired_count and pending_tasks == 0:
                print(f"✅ Service {service_name} is stable and ready for refresh.")
                return True
            else:
                print(f"❌ Service {service_name} has an active deployment in progress.")
                return False
        else:
            print(f"❌ Multiple deployments detected for {service_name}.")
            return False

    except ClientError as e:
        print(f"❌ AWS Error checking status: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ General Error checking status: {str(e)}")
        return False

'''
def trigger_step_function(cluster_name, service_name, region):
    """Triggers Step Function to delay and re-process the event."""
    print(f"🚀 Triggering Step Function for {service_name} in {cluster_name} (Region: {region})")

    event_detail = {
        "events": [
            {
                "service": "ECS",
                "eventTypeCode": "AWS_ECS_TASK_PATCHING_RETIREMENT",
                "eventTypeCategory": "scheduledChange",
                "region": region,
                "entities": [
                    {
                        "entityValue": f"{cluster_name}|{service_name}",
                        "statusCode": "IMPAIRED"
                    }
                ]
            }
        ]
    }

    response = eventbridge_client.put_events(
        Entries=[
            {
                'Source': 'custom.ecs.event.re-trigger',
                'DetailType': 'ECS Event Re-trigger',
                'Detail': json.dumps(event_detail),
                'EventBusName': 'default',
                'Time': datetime.utcnow()
            }
        ]
    )
    print(f"✅ Step Function triggered successfully for {service_name}: {response}")
    return response
'''

def disable_cloudwatch_alarms(service_name, region):
    """Disables only ECS CPUUtilization CloudWatch alarms for the given service."""
    print(f"🔍 Checking CloudWatch CPU Utilization alarms for {service_name} in {region}")

    try:
        # Fetch CloudWatch alarms filtering for ECS CPU Utilization
        response = cloudwatch_client.describe_alarms(
            MetricName="CPUUtilization"
        )

        alarms_to_disable = []
        for alarm in response.get("MetricAlarms", []):
            dimensions = alarm.get("Dimensions", [])
            metricName = alarm.get("MetricName")
            for dim in dimensions:
                if dim["Value"] == service_name:
                    alarms_to_disable.append(alarm["AlarmName"])
                    break 
        
        if not alarms_to_disable:
            print(f"✅ No CloudWatch CPU Utilization alarms found for {service_name}.")
            return

        print(f"Found {len(alarms_to_disable)} alarms related to {service_name} ECS service")
        print(f"🚨 Disabling {MetricName} alarms for {service_name}")

        # Disable only CPU Utilization alarms
        cloudwatch_client.disable_alarm_actions(AlarmNames=alarms_to_disable)
        print(f"✅ Disabled {alarms_to_disable} CloudWatch CPU Utilization alarms for {service_name}")

        time.sleep(3)  # Delay before proceeding with service refresh

    except ClientError as e:
        print(f"❌ AWS Error disabling CloudWatch alarms: {e.response['Error']['Message']}")
    except Exception as e:
        print(f"❌ General Error disabling alarms: {str(e)}")

def lambda_handler(event, context):
    print("🚀 Received Event (RAW):", json.dumps(event, indent=4))

    processed_services = set()

    # ✅ Standardize input format - Expecting "event_data"
    detail = event.get("Detail") or event.get("detail")
    '''
    if "event_data" in event:
        event = event["event_data"]  # Step Function case
    elif "detail" in event:
        event = event["detail"]  # EventBridge case
    elif "detail.$" in event:
        try:
            # 🔹 Fix: Convert JSON string into a dictionary
            event = json.loads(event.get("detail", "{}"))
        except json.JSONDecodeError:
            print("❌ ERROR: Failed to decode 'detail.$' JSON format")
            return {"message": "Invalid JSON format in 'detail.$' field."}
    else:
        print("⚠️ No valid 'detail' or 'event_data' found. Skipping processing.")
        return {"message": "No valid input found. Skipping."}
    '''

    # ✅ Ensure "Detail" is always a dictionary
    if isinstance(detail, str):
        try:
            detail = json.loads(detail)
        except json.JSONDecodeError as e:
            print(f"❌ ERROR: Failed to decode 'Detail' JSON string: {e}")
            return {"message": "Invalid JSON format in 'Detail' field."}

    # ✅ Extract 'events' from detail
    events_in_detail = detail.get("events", [])

    if not events_in_detail:
        print("⚠️ No 'events' field found. Skipping processing.")
        return {"message": "No 'events' field in event. Skipping."}

    for event_entry in events_in_detail:
        event_region = event_entry.get("region", "us-east-1")
        affected_entities = event_entry.get("entities", [])

        for entity in affected_entities:
            try:
                entity_value = entity.get("entityValue", "")
                parts = entity_value.split("|")

                if len(parts) < 2:
                    print(f"❌ Invalid entity format: {entity_value}")
                    continue

                cluster_name, service_name = parts[0], parts[1]
                service_identifier = f"{cluster_name}|{service_name}"

                if service_identifier in processed_services:
                    print(f"⏭️ Skipping already processed service: {service_identifier}")
                    continue

                processed_services.add(service_identifier)

                print(f"🔄 Checking ECS Service status for: {service_name} in Cluster: {cluster_name} (Region: {event_region})")

                if check_service_status(cluster_name, service_name, event_region):
                    print(f"✅ Service {service_name} is stable. Disabling the alarms & proceeding with service refresh.")
                    disable_cloudwatch_alarms(service_name, event_region)
                    ecs_client = boto3.client('ecs', region_name=event_region)
                    ecs_client.update_service(cluster=cluster_name, service=service_name, forceNewDeployment=True)
                    send_event_to_eventbridge(cluster_name, service_name, event_region)
                else:
                    print(f"❌ Skipping service {service_name} due to ongoing activity.")
                    # trigger_step_function(cluster_name, service_name, event_region)

            except Exception as e:
                print(f"❌ ERROR processing service {entity_value} in {event_region}: {str(e)}")

    print("✅ Lambda execution completed.")
    return {"message": "ECS Service Refresh Completed"}

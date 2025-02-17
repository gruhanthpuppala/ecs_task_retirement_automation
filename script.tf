# Define the AWS provider
provider "aws" {
  region = "us-east-1" # Change this to your preferred region
}

# Create an IAM Role for Lambda Execution
resource "aws_iam_role" "lambda_execution_role" {
  name = "Lambda_IAM_Role"

  # Define the trust policy that allows AWS Lambda to assume this role
  assume_role_policy = <<EOF
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
}

# Attach AWSLambdaBasicExecutionRole policy to the IAM Role
resource "aws_iam_role_policy_attachment" "lambda_execution_role_attachment" {
  role      = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Attach AmazonECS_FullAccess policy to the IAM Role
resource "aws_iam_role_policy_attachment" "ecs_full_access_attachment" {
  role      = aws_iam_role.lambda_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonECS_FullAccess"
}

# Create an AWS Lambda function
resource "aws_lambda_function" "ecs_service_refresh_lambda" {
  function_name    = "ECS_Service_Refresh"
  role             = aws_iam_role.lambda_execution_role.arn
  runtime          = "python3.12"
  handler          = "lambda_function.lambda_handler" # lambda_function is the lambda_function.py in which execution code of lambda to trigger ECS exists
  filename         = "lambda_code.zip" # The zipped deployment package must be manually created
  source_code_hash = filebase64sha256("lambda_code.zip") # checking sha for the zip file
  timeout          = 10 # Timeout in seconds
}

# Create an EventBridge Rule to capture AWS Health Dashboard events related to ECS task retirements
resource "aws_cloudwatch_event_rule" "ecs_task_retirement_rule" {
  name          = "TaskRetirementListenerRule"
  description   = "Listens for ECS task retirement events and triggers Lambda."
  event_pattern = <<EOF
{
  "source": ["custom.ecs.retirement"],
  "detail-type": ["AWS Health Event"],
  "detail": {
    "service": ["ECS"],
    "eventTypeCode": ["AWS_ECS_TASK_PATCHING_RETIREMENT"],
    "eventStatusCode": ["upcoming"]
  }
}
EOF
}

# Set up EventBridge target to invoke the Lambda function
resource "aws_cloudwatch_event_target" "ecs_lambda_target" {
  rule      = aws_cloudwatch_event_rule.ecs_task_retirement_rule.name
  target_id = "InvokeLambda"
  arn       = aws_lambda_function.ecs_service_refresh_lambda.arn
}

# Grant EventBridge permissions to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ecs_service_refresh_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ecs_task_retirement_rule.arn
}

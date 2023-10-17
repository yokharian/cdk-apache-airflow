from typing import List

from aws_cdk import aws_iam as iam
from constructs import Construct

datasync_managed_policies: List[iam.IManagedPolicy] = [
    (iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"))
]


class PolicyConstruct(Construct):
    policyStatements: List[iam.PolicyStatement]
    managedPolicies: List[iam.IManagedPolicy]

    def __init__(self, app: Construct, name: str) -> None:
        """
        Initializes the policy statements for the given application and name.

        Args:
            app: write your description
            name: write your description
        """
        super().__init__(app, name)

        self.managedPolicies = [
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSQSFullAccess"),
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonECS_FullAccess"),
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonElasticFileSystemClientReadWriteAccess"
            ),
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "CloudWatchLogsReadOnlyAccess"
            ),
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonS3FullAccess"),
            iam.ManagedPolicy.from_aws_managed_policy_name("SecretsManagerReadWrite"),
            iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMReadOnlyAccess"),
            iam.ManagedPolicy.from_managed_policy_arn(
                self,
                "ecsTaskExecutionRolePolicy",
                "arn:aws:iam::aws:policy/service-role/"
                + "AmazonECSTaskExecutionRolePolicy",
            ),
        ]

        # You can add custom Policy Statements as well.
        # Sample code for SQS and IAM Full Access would like like:
        self.policyStatements = [
            iam.PolicyStatement(
                actions=["sqs:*"], effect=iam.Effect.ALLOW, resources=["*"]
            ),
            iam.PolicyStatement(
                actions=[
                    "dynamodb:BatchGet*",
                    "dynamodb:DescribeStream",
                    "dynamodb:DescribeTable",
                    # READ ONLY
                    "states:ListStateMachines",
                    "states:ListActivities",
                    "states:DescribeStateMachine",
                    "states:DescribeStateMachineForExecution",
                    "states:ListExecutions",
                    "states:DescribeExecution",
                    "states:GetExecutionHistory",
                    "states:DescribeActivity",
                    # NON-READ
                    "states:StartExecution",
                    "states:SendTaskSuccess",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    # READ ONLY
                    "s3:Get*",
                    "s3:List*",
                    "s3-object-lambda:Get*",
                    "s3-object-lambda:List*",
                    # NON-READ
                    "s3:PutObject",
                    "s3:CreateBucket",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    # READ ONLY
                    "secretsmanager:Describe*",
                    "secretsmanager:Get*",
                    "secretsmanager:List*",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    # READ ONLY
                    "dynamodb:BatchGetItem",
                    "dynamodb:Describe*",
                    "dynamodb:List*",
                    "dynamodb:GetItem",
                    "dynamodb:Query",
                    "dynamodb:Scan",
                    "dynamodb:PartiQLSelect",
                    # NON-READ
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:DeleteItem",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    # READ ONLY
                    "lambda:GetAccountSettings",
                    "lambda:GetEventSourceMapping",
                    "lambda:GetFunction",
                    "lambda:GetFunctionConfiguration",
                    "lambda:GetFunctionCodeSigningConfig",
                    "lambda:GetFunctionConcurrency",
                    "lambda:ListEventSourceMappings",
                    "lambda:ListFunctions",
                    "lambda:ListTags",
                    # NON READ (execute)
                    "lambda:InvokeFunction",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
            iam.PolicyStatement(
                actions=[
                    # READ ONLY
                    "kinesis:Get*",
                    "kinesis:List*",
                    "kinesis:Describe*",
                    # WRITE ONLY
                    "kinesis:Put*",
                ],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            ),
        ]

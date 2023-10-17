from os import getenv
from typing import List

from aws_cdk import Stack, aws_ecs as ecs, aws_iam as iam, aws_logs
import aws_cdk as cdk
from aws_cdk.aws_ecr_assets import DockerImageAsset
from aws_cdk.aws_ecs import (
    RuntimePlatform,
    CpuArchitecture,
    OperatingSystemFamily,
)
from constructs import Construct

STAGE = getenv("STAGE", "prod")
PROJECT_NAME = "YokharianDags".capitalize().replace(" ", "")
STACK_ID = f"{PROJECT_NAME}{STAGE.capitalize()}"

# containers config
CPU, MEMORY = 512, 1024
CONTAINER_INFO = {"assetDir": ".", "name": "yokharian_dags"}
EFS_VOLUME_INFO = {
    "containerPath": "/shared-volume",
    "volumeName": f"{STAGE}SharedVolume",
    "efsFileSystemId": "fs-0301ce3903c6ae401",
}
# noinspection PyTypeChecker
DEFAULT_RUNTIME_PLATFORM = RuntimePlatform(
    cpu_architecture=CpuArchitecture.X86_64,
    operating_system_family=OperatingSystemFamily.LINUX,
)


def _90_percent(target: int) -> int:
    """useful to set a hard limit to the 90%, available memory often is
    100mb less of what is expected, if your instance type has not enough
    memory it won't be ran (even if 100mb)"""
    return target - (target // 10)


def _75_percent(target: int) -> int:
    """useful to set a soft limit to the 75%"""
    return target - (target // 4)


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
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonECS_FullAccess"
            ),
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonElasticFileSystemClientReadWriteAccess"
            ),
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "CloudWatchLogsReadOnlyAccess"
            ),
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonS3FullAccess"
            ),
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "SecretsManagerReadWrite"
            ),
            iam.ManagedPolicy.from_aws_managed_policy_name(
                "AmazonSSMReadOnlyAccess"
            ),
            iam.ManagedPolicy.from_managed_policy_arn(
                self,
                "ecsTaskExecutionRolePolicy",
                "arn:aws:iam::aws:policy/service-role/"
                + "AmazonECSTaskExecutionRolePolicy",
            ),
        ]
        # You can add custom Policy Statements as well.
        self.policyStatements = [
            iam.PolicyStatement(  # WRITE & READ
                actions=["Timestream:*"],
                effect=iam.Effect.ALLOW,
                resources=["*"],
            )
        ]


class MainStack(Stack):
    def set_policies(self, ec2_task_definition):
        policies = PolicyConstruct(self, "ec2DagsTaskPolicies")
        for policy in policies.managedPolicies:
            ec2_task_definition.task_role.add_managed_policy(policy)
        for policy in policies.policyStatements:
            ec2_task_definition.task_role.add_to_principal_policy(policy)

    def __init__(self, scope: Construct, stack_id: str, **kwargs) -> None:
        """
        Create the Airflow construct.

        Args:
            scope: write your description
            stack_id: write your description
        """
        super().__init__(scope, stack_id, **kwargs)

        # noinspection PyTypeChecker
        task_definition = ecs.FargateTaskDefinition(
            self,
            "TaskDef",
            family="yokharian",
            cpu=CPU,
            memory_limit_mib=MEMORY,
            runtime_platform=DEFAULT_RUNTIME_PLATFORM,
        )
        self.set_policies(task_definition)

        container = task_definition.add_container(
            CONTAINER_INFO["name"],
            image=ecs.ContainerImage.from_docker_image_asset(
                DockerImageAsset(
                    self,
                    CONTAINER_INFO["name"] + "-BuildImage",
                    directory=CONTAINER_INFO["assetDir"],
                )
            ),
            logging=ecs.AwsLogDriver(
                stream_prefix=f"{STAGE}{PROJECT_NAME}Logging",
                log_group=aws_logs.LogGroup(
                    self,
                    "LogGroup",
                    log_group_name=f"{STAGE}/{PROJECT_NAME}Logs",
                    retention=aws_logs.RetentionDays.ONE_MONTH,
                    removal_policy=cdk.RemovalPolicy.DESTROY,
                ),
            ),
        )
        if EFS_VOLUME_INFO:
            task_definition.add_volume(
                name=EFS_VOLUME_INFO["volumeName"],
                efs_volume_configuration=ecs.EfsVolumeConfiguration(
                    file_system_id=EFS_VOLUME_INFO["efsFileSystemId"]
                ),
            )
            container.add_mount_points(
                ecs.MountPoint(
                    container_path=EFS_VOLUME_INFO["containerPath"],
                    source_volume=EFS_VOLUME_INFO["volumeName"],
                    read_only=False,
                )
            )


app = cdk.App()
MainStack(
    scope=app,
    stack_id=STACK_ID,
    termination_protection=True,
    tags={"stack": STACK_ID, "stage": STAGE},
    env=cdk.Environment(
        account=getenv("CDK_DEFAULT_ACCOUNT"),  # needed
        region=getenv("CDK_DEFAULT_REGION", "us-east-1"),  # needed
    ),
)
app.synth()

from typing import Dict, List, Optional, Union
from uuid import uuid4

import aws_cdk as cdk
import aws_cdk.aws_logs
from aws_cdk import (
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_iam as iam,
    aws_s3 as s3,
)
from aws_cdk.aws_ecr_assets import DockerImageAsset
from constructs import Construct

from .core.config import (
    SCHEDULER_CONFIG,
    STAGE,
    WEB_SERVER_CONFIG,
    WORKER_CONFIG,
)
from .service_base import ServiceConstruct


class AirflowConstruct(Construct):
    _airflows_url: str

    def __init__(
        self,
        parent: Construct,
        name: str,
        vpc: ec2.Vpc,
        cluster: ecs.ICluster,
        default_sg: ec2.CfnSecurityGroup,
        private_subnets: List[ec2.Subnet],
        public_subnets: List[ec2.Subnet],
        capacity_providers: Dict[str, ecs.AsgCapacityProvider],
        s3_log_bucket: s3.Bucket,
        efs_volume_info: Optional[dict] = None,
        db_connection: str = "",
    ) -> None:
        """
        Build Airflow task.

        Args:
            parent: write your description
            name: write your description
            vpc: write your description
            cluster: write your description
            default_sg: write your description
            db_connection: write your description
        """
        super().__init__(parent, name)

        self._admin_password: str = str(uuid4())
        efs_git_repo_full_path = f'{efs_volume_info["containerPath"]}/git_repo'
        environment_variables = {
            "AWS_DEFAULT_REGION": str(cdk.Stack.of(self).region),
            # user-custom env vars
            "ADMIN_PASS": self._admin_password,
            "CLUSTER": cluster.cluster_name,
            "SECURITY_GROUP": default_sg.security_group_id,
            "SUBNETS": ",".join(
                subnet.subnet_id for subnet in private_subnets
            ),
            "STAGE": STAGE,
            "CSRF_SECRET_KEY": str(uuid4()),
            # [-] These settings have higher priority than airflow.cfg...
            "AIRFLOW__DATABASE__SQL_ALCHEMY_CONN": db_connection,
            "AIRFLOW__WEBSERVER__RBAC": "True",
            "AIRFLOW__WEBSERVER__WARN_DEPLOYMENT_EXPOSURE": "False",
            "AIRFLOW__CORE__XCOM_BACKEND": "s3_xcom_backend.S3XComBackend",
            "AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL": (
                "600" if STAGE == "prod" else "15"
            ),
            # executor configs
            "AIRFLOW__CORE__EXECUTOR": "CeleryExecutor",
            "AIRFLOW__CELERY__RESULT_BACKEND": f"db+{db_connection}",
            "AIRFLOW__CELERY__BROKER_URL": "sqs://",  # will use localhost
            # remote logging
            "REMOTE_BASE_LOG_BUCKET": s3_log_bucket.bucket_name,
            "AIRFLOW__LOGGING__REMOTE_LOGGING": "True",
            "AIRFLOW__LOGGING__WORKER_LOG_SERVER_PORT": "8082",
            "AIRFLOW__LOGGING__REMOTE_LOG_CONN_ID": "AWSS3LogStorage",
            "AIRFLOW__LOGGING__REMOTE_BASE_LOG_FOLDER": (
                f"s3://{s3_log_bucket.bucket_name}/logs"
            ),
            # EFS configs
            "EFS_FULL_PATH": efs_volume_info["containerPath"],
            "EFS_GIT_REPO_FULL_PATH": efs_git_repo_full_path,
            "AIRFLOW__CODE_EDITOR__ROOT_DIRECTORY": efs_git_repo_full_path,
            "AIRFLOW_HOME": efs_git_repo_full_path,
        }
        airflow_image_asset = DockerImageAsset(
            self, "AirflowBuildImage", directory="."
        )
        # Build Airflow docker image from Dockerfile
        airflow_task = ecs.Ec2TaskDefinition(
            self, "AirflowTask", network_mode=ecs.NetworkMode.BRIDGE
        )
        worker_task = ecs.Ec2TaskDefinition(
            self, "WorkerTask", network_mode=ecs.NetworkMode.BRIDGE
        )
        mmap = (
            (WEB_SERVER_CONFIG, airflow_task),
            (SCHEDULER_CONFIG, airflow_task),
            (WORKER_CONFIG, worker_task),
        )
        self.populate_tasks_with_corresponding_containers(
            airflow_image_asset, efs_volume_info, environment_variables, mmap
        )

        # noinspection PyProtectedMember
        self._airflows_url = ServiceConstruct(
            self,
            "AirflowSvc",
            cluster=cluster,
            default_sg=default_sg,
            vpc=vpc,
            task_definition=airflow_task,
            subnets=public_subnets,  # accessible from outside
            asg_capacity_providers=[capacity_providers["default"]],
            config=WEB_SERVER_CONFIG,
        )._airflows_url

        ServiceConstruct(
            self,
            "WorkerSvc",
            cluster=cluster,
            default_sg=default_sg,
            vpc=vpc,
            task_definition=worker_task,
            is_worker_service=True,
            subnets=private_subnets,  # non accessible from outside
            asg_capacity_providers=[capacity_providers["worker"]],
            config=WORKER_CONFIG,
        )

    def populate_tasks_with_corresponding_containers(
        self, airflow_image_asset, efs_volume_info, environment_variables, mmap
    ):
        """
        Populate the tasks with the containers that are equivalent.

        Args:
            self: write your description
            airflow_image_asset: write your description
            efs_volume_info: write your description
            environment_variables: write your description
            mmap: write your description
        """
        for (container_info, task) in mmap:
            task: Union[ecs.Ec2TaskDefinition]
            container_info: dict

            if efs_volume_info:
                task.add_volume(
                    name=efs_volume_info["volumeName"],
                    efs_volume_configuration=ecs.EfsVolumeConfiguration(
                        file_system_id=efs_volume_info["efsFileSystemId"],
                    ),
                )

            container = task.add_container(
                id=container_info["name"],
                image=ecs.ContainerImage.from_docker_image_asset(
                    airflow_image_asset
                ),
                logging=ecs.AwsLogDriver(
                    stream_prefix="AirflowsLogging",
                    log_group=aws_cdk.aws_logs.LogGroup(
                        self,
                        container_info["name"],
                        log_group_name=f"airflows/"
                        f"{STAGE}-{container_info['name']}",
                        removal_policy=cdk.RemovalPolicy.DESTROY,
                        retention=container_info["logRetention"],
                    ),
                ),
                entry_point=[container_info["entryPoint"]],
                environment=environment_variables,
                cpu=container_info.get("cpu"),
                memory_limit_mib=container_info.get("memoryLimitMiB"),
                memory_reservation_mib=container_info.get(
                    "memoryReservationMiB"
                ),
            )
            container.add_port_mappings(
                ecs.PortMapping(container_port=container_info["containerPort"])
            )
            if efs_volume_info:
                task.task_role.add_managed_policy(
                    iam.ManagedPolicy.from_aws_managed_policy_name(
                        "AmazonElasticFileSystemClientReadWriteAccess"
                    )
                )
                container.add_mount_points(
                    ecs.MountPoint(
                        container_path=efs_volume_info["containerPath"],
                        source_volume=efs_volume_info["volumeName"],
                        read_only=False,
                    )
                )

    @property
    def airflows_url(self):
        return self._airflows_url

    @property
    def admin_password(self):
        return self._admin_password

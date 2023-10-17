from typing import List

import aws_cdk as cdk
from aws_cdk import (
    aws_autoscaling as autoscaling,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_s3 as s3,
)
from aws_cdk.aws_autoscaling import UpdatePolicy
from constructs import Construct

from .airflow_services import AirflowConstruct
from .efs import EFSConstruct
from .rds import RDSConstruct
from .core.config import INSTANCE_TYPES, STAGE


class ApacheAirflowsMainConstruct(Construct):
    _web_admin_password: str
    _airflows_url: str
    _efs_id: str
    _efs_arn: str
    _datasync_task_name: str
    _s3_bucket_name: str
    _main_efs: EFSConstruct

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        sg: ec2.SecurityGroup,
        vpc: ec2.Vpc,
        private_subnets: List[ec2.Subnet],
        public_subnets: List[ec2.Subnet],
        isolated_subnets: List[ec2.Subnet],
    ) -> None:
        """
        Initializes the Airflow construct.

        Args:
            self: write your description
            scope: write your description
            construct_id: write your description
            sg: write your description
            vpc: write your description
            private_subnets: write your description
            public_subnets: write your description
            isolated_subnets: write your description
        """
        super().__init__(scope, construct_id)
        all_subnets = public_subnets + isolated_subnets + private_subnets
        # you need a NAT GATEWAY in order to provide internet access to
        # private subnets with ec2 capacity provider strategy...
        _private_subnets = public_subnets

        cluster = ecs.Cluster(
            self,
            "ECSCluster",
            cluster_name=f"airflows-{STAGE}",
            vpc=vpc,
            enable_fargate_capacity_providers=True,
        )
        capacity_provider = dict(
            self.set_up_capacity_provider_config(
                cluster, _private_subnets, public_subnets, sg, vpc
            )
        )

        # Create RDS instance for Airflow backend
        rds = RDSConstruct(
            self, "RDS", default_sg=sg, vpc=vpc, vpc_subnets=isolated_subnets
        )

        # create efs system
        self._main_efs = EFSConstruct(
            self, "EFS", vpc=vpc, security_group=sg, subnets=all_subnets
        )

        # create a bucket to save logs
        s3_log_bucket = self.build_s3_log_bucket()

        # Create Airflow service: Webserver, Scheduler and minimal Worker
        airflow_construct = AirflowConstruct(
            self,
            "Airflow",
            cluster=cluster,
            vpc=vpc,
            default_sg=sg,
            db_connection=rds.dbConnection,
            private_subnets=_private_subnets,
            public_subnets=public_subnets,
            efs_volume_info=self.main_efs.efs_volume_info,
            capacity_providers=capacity_provider,
            s3_log_bucket=s3_log_bucket,
        )

        self._efs_id = self.main_efs.efs_id
        self._efs_arn = self.main_efs.efs_arn
        self._datasync_task_name = self.main_efs.datasync_task_name
        self._s3_bucket_name = self.main_efs.s3_bucket_name
        self._airflows_url = airflow_construct.airflows_url
        self._web_admin_password = airflow_construct.admin_password
        self._s3_log_bucket_name = s3_log_bucket.bucket_name

    # noinspection PyTypeChecker,PydanticTypeChecker
    def build_s3_log_bucket(self) -> s3.Bucket:
        """
        Build the s3 bucket.

        Args:
            self: write your description
        """
        transitions = [
            s3.Transition(
                storage_class=s3.StorageClass.INFREQUENT_ACCESS,
                transition_after=cdk.Duration.days(30),
            )
        ]
        return s3.Bucket(
            self,
            "s3Bucket",
            bucket_name=f"{STAGE}-airflows-bucket",
            versioned=False,
            lifecycle_rules=[s3.LifecycleRule(transitions=transitions)],
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )

    def set_up_capacity_provider_config(
        self, cluster, private_subnets, public_subnets, sg, vpc
    ):
        """
        Configure the capacity provider configurations for the cluster.

        Args:
            self: write your description
            cluster: write your description
            private_subnets: write your description
            public_subnets: write your description
            sg: write your description
            vpc: write your description
        """
        for name, configs in INSTANCE_TYPES.items():
            subnets = public_subnets if name == "default" else private_subnets

            asg = autoscaling.AutoScalingGroup(
                self,
                f"{name}AutoScalingGroup",
                max_capacity=configs["asg"]["max_capacity"],
                min_capacity=configs["asg"]["min_capacity"],
                desired_capacity=configs["asg"]["desired_capacity"],
                vpc=vpc,
                instance_monitoring=autoscaling.Monitoring.BASIC,
                vpc_subnets={"subnets": subnets},
                instance_type=configs["type"],
                machine_image=ecs.EcsOptimizedImage.amazon_linux2(
                    hardware_type=ecs.AmiHardwareType.ARM
                    if configs["arm"]
                    else ecs.AmiHardwareType.STANDARD
                ),
                security_group=sg,
                associate_public_ip_address=True,  # needed for deploy (BUG)
                block_devices=configs["ebs"],
                update_policy=UpdatePolicy.rolling_update(),
            )
            asg_capacity_provider = ecs.AsgCapacityProvider(
                self, f"{name}AsgCapacityProvider", auto_scaling_group=asg
            )
            cluster.add_asg_capacity_provider(asg_capacity_provider)
            yield name, asg_capacity_provider

    @property
    def main_efs(self):
        return self._main_efs

    @property
    def airflows_url(self):
        return self._airflows_url

    @property
    def web_admin_password(self):
        return self._web_admin_password

    @property
    def efs_id(self):
        return self._efs_id

    @property
    def efs_arn(self):
        return self._efs_arn

    @property
    def datasync_task_name(self):
        return self._datasync_task_name

    @property
    def s3_bucket_name(self):
        return self._s3_bucket_name

    @property
    def s3_log_bucket_name(self):
        return self._s3_log_bucket_name

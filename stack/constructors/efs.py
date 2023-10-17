from typing import List

from aws_cdk import (
    aws_ec2 as ec2,
    aws_efs as efs,
)
import aws_cdk as cdk
from constructs import Construct

from .core.config import STAGE


class EFSConstruct(Construct):
    shared_efs: efs.IFileSystem

    _efs_id: str
    _efs_arn: str
    _datasync_task_name: str
    _s3_bucket_name: str

    def sg_arn(self, security_group: ec2.ISecurityGroup) -> str:
        """
        Format security group ARN.

        Args:
            self: write your description
            security_group: write your description
        """
        return cdk.Stack.of(self).format_arn(
            resource="security-group",
            service="ec2",
            account=security_group.env.account,
            region=security_group.env.region,
            resource_name=security_group.security_group_id,
        )

    def subnet_arn(self, subnet: ec2.Subnet) -> str:
        """
        Format the Subnet ARN for the stack.

        Args:
            self: write your description
            subnet: write your description
        """
        return cdk.Stack.of(self).format_arn(
            resource="subnet",
            service="ec2",
            account=subnet.env.account,
            region=subnet.env.region,
            resource_name=subnet.subnet_id,
        )

    def __init__(
        self,
        scope: Construct,
        name: str,
        vpc: ec2.Vpc,
        security_group: ec2.SecurityGroup,
        subnets: List[ec2.ISubnet],
        file_system_name=f"{STAGE}SharedVolume",
    ) -> None:
        """
        Initializes the EFS.

        Args:
            self: write your description
            scope: write your description
            name: write your description
            vpc: write your description
            security_group: write your description
            subnets: write your description
            file_system_name: write your description
        """
        super().__init__(scope, name)
        self.shared_efs = efs.FileSystem(
            self,
            "EFSVolume",
            vpc=vpc,
            security_group=security_group,
            file_system_name=file_system_name,
            lifecycle_policy=efs.LifecyclePolicy.AFTER_14_DAYS,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            performance_mode=efs.PerformanceMode.GENERAL_PURPOSE,
            vpc_subnets={"subnets": subnets},
        )
        self.efs_volume_info = {
            "containerPath": "/shared-volume",
            "volumeName": file_system_name,
            "efsFileSystemId": self.shared_efs.file_system_id,
        }

        self.datasync_task_name, self.s3_bucket_name = None, None
        self._efs_id = self.shared_efs.file_system_id
        self._efs_arn = self.shared_efs.file_system_arn

    @property
    def efs_id(self):
        return self._efs_id

    @property
    def efs_arn(self):
        return self._efs_arn

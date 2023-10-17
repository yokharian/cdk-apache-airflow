import typing
from os import getenv
from typing import List

import aws_cdk as cdk
from aws_cdk import Stack, aws_ec2 as ec2, aws_ssm as ssm
from constructs import Construct

from constructors.core.config_vpc import (
    DEFAULT_SECURITY_GROUP_ID,
    create_security_groups,
)
from constructors.main_airflows import ApacheAirflowsMainConstruct
from constructors.core.config import STACK_NAME, STAGE


def parse_output(to_parse: str, stack="MainVpc"):
    """
    Parses the output of a script.

    Args:
        to_parse: write your description
        stack: write your description
    """
    return f"{to_parse}{stack}{STAGE.capitalize()}"


class AirflowsMainStack(Stack):
    def import_from_ssm(self, key: str) -> str:
        """
        Import value from Motorola SSM code.

        Args:
            self: write your description
            key: write your description
        """
        return ssm.StringParameter.value_for_string_parameter(
            self, f"/cdk/SSM/{key}"
        )

    def import_list(
        self, key: str, assumed_length: typing.Optional[int] = 2
    ) -> List[str]:
        """
        Imports a list of strings from a Motorola SSM file.

        Args:
            self: write your description
            key: write your description
            assumed_length: write your description
        """
        return cdk.Fn.split(",", self.import_from_ssm(key), assumed_length)

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        """
        Create the Airflow construct.

        Args:
            scope: write your description
            construct_id: write your description
        """
        super().__init__(scope, construct_id, **kwargs)
        cdk.Tags.of(scope).add("Stack", construct_id)

        subnets = (f"{s}Subnets" for s in ("public", "private", "isolated"))
        subnets = (self.import_list(parse_output(s)) for s in subnets)
        public_subnets, private_subnets, isolated_subnets = subnets
        vpc: ec2.IVpc = ec2.Vpc.from_vpc_attributes(
            self,
            "VPC",
            vpc_id=self.import_from_ssm(parse_output("vpcId")),
            availability_zones=self.import_list(parse_output("azs")),
            public_subnet_ids=public_subnets,
            private_subnet_ids=private_subnets,
            isolated_subnet_ids=isolated_subnets,
        )
        security_groups = dict(create_security_groups(self, vpc))
        default_sg = security_groups[DEFAULT_SECURITY_GROUP_ID]

        airflows_construct = ApacheAirflowsMainConstruct(
            self,  # EVERYTHING about vanilla apache airflows here
            construct_id=" ",
            vpc=vpc,
            sg=default_sg,
            private_subnets=vpc.private_subnets,
            public_subnets=vpc.public_subnets,
            isolated_subnets=vpc.isolated_subnets,
        )

        # Stack Outputs here...
        for key, value in {
            "webUrl": airflows_construct.airflows_url,
            "AdminPassword": airflows_construct.web_admin_password,
            "efsId": airflows_construct.efs_id,
            "efsArn": airflows_construct.efs_arn,
            "datasyncTaskName": airflows_construct.datasync_task_name,
            "S3EfsBucketName": airflows_construct.s3_bucket_name,
            "S3LogsBucketName": airflows_construct.s3_log_bucket_name,
        }.items():
            if not value:
                continue  # will raise exception on cloudformation if empty
            key = f"{key}{STAGE.capitalize()}Airflows"
            cfn_output = cdk.CfnOutput(
                self,
                key,
                value=value,
                export_name=parse_output(key, stack=STACK_NAME),
            )
            setattr(self, f"{key}Output", cfn_output)


app = cdk.App()

AirflowsMainStack(
    app,
    f"{STACK_NAME}{STAGE.capitalize()}",
    env=cdk.Environment(
        account=getenv("CDK_DEFAULT_ACCOUNT"),  # needed
        region=getenv("CDK_DEFAULT_REGION", "us-east-1"),  # needed
    ),
)

app.synth()

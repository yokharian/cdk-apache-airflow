from json import dumps

import aws_cdk as cdk
from aws_cdk import (
    aws_ec2 as ec2,
    aws_rds as rds,
    aws_secretsmanager as secrets_manager,
)
from constructs import Construct

from .core.config import STAGE, RDS_DATABASE_CONFIG


class RDSConstruct(Construct):
    dbConnection: str
    rdsInstance: rds.DatabaseInstance

    def __init__(
        self,
        parent: Construct,
        name: str,
        vpc: ec2.Vpc,
        default_sg: ec2.ISecurityGroup,
        vpc_subnets: ec2.Subnet,
    ) -> None:
        """
        Initialize the RDS connection.

        Args:
            parent: write your description
            name: write your description
            vpc: write your description
            default_sg: write your description
            vpc_subnets: write your description
        """
        super().__init__(parent, name)
        backend_secret: secrets_manager.Secret = secrets_manager.Secret(
            self,
            "DatabaseSecret",
            secret_name=f"{name}Secret{STAGE}",
            description="airflow RDS secrets",
            generate_secret_string=secrets_manager.SecretStringGenerator(
                secret_string_template=dumps(
                    {"username": RDS_DATABASE_CONFIG["masterUsername"]}
                ),
                generate_string_key="password",
                exclude_punctuation=True,
                exclude_uppercase=False,
                require_each_included_type=False,
                include_space=False,
                exclude_lowercase=False,
                exclude_numbers=False,
                password_length=16,
            ),
        )
        database_password_secret = backend_secret.secret_value_from_json(
            "password"
        )
        # noinspection PyTypeChecker,PydanticTypeChecker
        self.rdsInstance = rds.DatabaseInstance(
            self,
            "RDSInstance",
            engine=rds.DatabaseInstanceEngine.postgres(
                version=rds.PostgresEngineVersion.VER_14_2
            ),
            instance_type=RDS_DATABASE_CONFIG["instanceType"],
            instance_identifier=RDS_DATABASE_CONFIG["dbName"],
            vpc=vpc,
            security_groups=[default_sg],
            vpc_subnets={"subnets": vpc_subnets},
            storage_encrypted=True,
            multi_az=False,
            auto_minor_version_upgrade=False,
            allocated_storage=RDS_DATABASE_CONFIG["allocatedStorageInGB"],
            max_allocated_storage=RDS_DATABASE_CONFIG["maxAllocatedStorage"],
            storage_type=rds.StorageType.GP2,
            backup_retention=cdk.Duration.days(
                RDS_DATABASE_CONFIG["backupRetentionInDays"]
            ),
            deletion_protection=False,
            database_name=RDS_DATABASE_CONFIG["dbName"],
            port=RDS_DATABASE_CONFIG["port"],
            credentials=rds.Credentials.from_username(
                username=RDS_DATABASE_CONFIG["masterUsername"],
                password=database_password_secret,
            ),
            removal_policy=cdk.RemovalPolicy.RETAIN,
        )
        self.dbConnection = self.get_db_connection(
            RDS_DATABASE_CONFIG,
            self.rdsInstance.db_instance_endpoint_address,
            database_password_secret.to_string(),
        )

    @staticmethod
    def get_db_connection(
        db_config: dict, endpoint: str, password: str
    ) -> str:
        """
        Get a connection string from the db_config.

        Args:
            db_config: write your description
            endpoint: write your description
            password: write your description
        """
        return (
            f"postgresql+psycopg2://{db_config['masterUsername']}:"
            f"{password}@{endpoint}:{db_config['port']}/{db_config['dbName']}"
        )

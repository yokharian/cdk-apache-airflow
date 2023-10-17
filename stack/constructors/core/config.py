"""
cpu and memory values are very dangerous, choosing non-compatible values between
instance_type & (sum of containers in a task) will cause instances stuck in
provisioning state.

# RECOMMENDED EC2 INSTANCE TYPES
## [-] good if you're starting
t3a.SMALL (2 VCpu 2 GiB memory) - around $13.9872 month (each instance)
## [-] good if you're growing
t3a.MEDIUM (2 VCpu 4 GiB memory) - around $27.9744 month (each instance)

mapping for instances
https://gist.githubusercontent.com/zanozbot/d4dc737dea855519c0805e8bfa9dc13b/raw/387b1d15fecfefa67831a5f0165300603cfe8a78/ec2_instance_class_mapping.csv

you must consider this if Dockerfiles
https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-eni.html#AvailableIpPerENI

consider reserving ec2 instances as you'll obtain 50% off directly
read more about ec2 pricing
https://instances.vantage.sh/

all prices shown here are in USD, updated 24/04/2022
"""
from os import getenv

from aws_cdk.aws_autoscaling import (
    EbsDeviceVolumeType,
)
from aws_cdk.aws_logs import RetentionDays
from aws_cdk import aws_ec2 as ec2

from .utils import (
    _75_percent,
    _90_percent,
    block_device,
)

STAGE = getenv("STAGE", "prod")
STACK_NAME = "Airflows"  # "-{STAGE}" is appended to it
DOMAIN_NAME = "airflows.yokharian.com"  # none to obtain dns default
DOMAIN_NAME = f"{STAGE}.{DOMAIN_NAME}" if STAGE != "prod" else DOMAIN_NAME
LOCAL_DNS = f"airflows.{STAGE}.yokharian.local"  # none to obtain dns default
# Set to None to generate a new one, with acm
EXISTING_CERTIFICATE_ARN = None

# web & scheduler are in one single container, the worker is in
# a single container, this 'asg' configuration facilitates
# deployments because while building one, when it's running
# right after it deletes the old one.
INSTANCE_TYPES = {  # just a mapping for the ASGs
    "default": {
        "type": ec2.InstanceType.of(  # (2 VCpu & 4 GiB RAM) ~ $27.9744 month
            ec2.InstanceClass.BURSTABLE3_AMD, ec2.InstanceSize.MEDIUM
        ),
        "arm": False,
        # (30 gb & STANDARD Type) ~ 0.2 USD per month 2022-07-01
        "ebs": [block_device(EbsDeviceVolumeType.STANDARD, 30)],
        "asg": {"max_capacity": 2, "min_capacity": 1, "desired_capacity": 1},
    },
    "worker": {
        "type": ec2.InstanceType.of(  # (2 VCpu & 4 GiB RAM) ~ $27.9744 month
            ec2.InstanceClass.BURSTABLE3_AMD, ec2.InstanceSize.MEDIUM
        ),
        "arm": False,
        # (30 gb & GP3 Type) ~ 2.4 USD per month 2022-07-03
        "ebs": [block_device(EbsDeviceVolumeType.GP3, 30)],
        "asg": {"max_capacity": 2, "min_capacity": 1, "desired_capacity": 1},
    },
}  # https://us-east-1.console.aws.amazon.com/ec2/v2/home#InstanceTypes

# If webserver is down after adding more DAGs, it is because loading all
# DAGs requires > 2G memory, increase the memory of webserver instance.
WEB_SERVER_CONFIG = {  # 2048 memory is a GOOD value !
    "cpu": 1024,  # minimum is 512, but ec2 instance can handle it
    "memoryReservationMiB": _75_percent(2048),  # soft limit
    # If your container attempts to exceed the allocated memory,
    # the container is terminated.
    "memoryLimitMiB": _90_percent(2048),  # hard limit
    "name": "WebserverContainer",
    "containerPort": 8080,
    "entryPoint": "/webserver_entry.sh",
    "logRetention": RetentionDays.ONE_MONTH,
}
SCHEDULER_CONFIG = {
    "cpu": WEB_SERVER_CONFIG["cpu"],
    "memoryReservationMiB": WEB_SERVER_CONFIG["memoryReservationMiB"],
    "memoryLimitMiB": WEB_SERVER_CONFIG["memoryLimitMiB"],
    "name": "SchedulerContainer",
    "containerPort": 8081,
    "entryPoint": "/scheduler_entry.sh",
    "logRetention": RetentionDays.ONE_MONTH,
}
WORKER_CONFIG = {  # 2048 is a good memory value, less may crash it
    "cpu": 2048,  # minimum is 1024, but ec2 instance can handle it
    "memoryReservationMiB": _75_percent(4096),  # soft limit
    # If your container attempts to exceed the allocated memory,
    # the container is terminated.
    "memoryLimitMiB": _90_percent(4096),  # hard limit
    "name": "WorkerContainer",
    "containerPort": 8082,
    "entryPoint": "/worker_entry.sh",
    "logRetention": RetentionDays.ONE_MONTH,
    "workerAutoScalingConfig": {
        "minTaskCount": 1 if STAGE == "prod" else 1,
        "maxTaskCount": 2 if STAGE == "prod" else 2,
        "cpuUsagePercent": 90,  # set None to ignore this one
        "memUsagePercent": 85,  # set None to ignore this one
    },
}

RDS_DATABASE_CONFIG = {
    "dbName": f"{STAGE}AirFlows",
    "port": 5432,
    "masterUsername": "airflow",
    "allocatedStorageInGB": 20,  # minimum 20 GiB reserved for GP2 ($2.30 month)
    # set maximum scaling size to avoid leaks.
    "maxAllocatedStorage": 30,  # can be modified later
    "backupRetentionInDays": 0,  # Set to zero to disable backups.
    # t4g.micro (2 VCpu 1 GiB memory) - around $6.2496 month (each instance)
    "instanceType": ec2.InstanceType.of(
        ec2.InstanceClass.BURSTABLE4_GRAVITON, ec2.InstanceSize.MICRO
    ),
}

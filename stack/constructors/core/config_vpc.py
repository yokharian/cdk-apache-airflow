"""https://github.com/abkunal/custom-vpc-cdk"""
from aws_cdk import aws_ec2 as ec2

# abbreviations to simplify
from constructs import Construct

In = ec2.CfnSecurityGroup.IngressProperty
Egress = ec2.CfnSecurityGroup.EgressProperty

# security groups
DEFAULT_SECURITY_GROUP_ID = "airflowsSecurityGroup"


def create_security_groups(scope: Construct, vpc: ec2.IVpc):
    """Creates all the security groups, sg is the abbreviation"""
    security_group_id = DEFAULT_SECURITY_GROUP_ID
    security_group = ec2.SecurityGroup(
        scope,
        security_group_id,
        vpc=vpc,
        description="SG of the airflows servers",
        security_group_name=DEFAULT_SECURITY_GROUP_ID,
    )
    # you can be as granular as you want here...
    security_group.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.all_traffic())
    security_group.add_ingress_rule(ec2.Peer.any_ipv6(), ec2.Port.all_traffic())
    yield security_group_id, security_group

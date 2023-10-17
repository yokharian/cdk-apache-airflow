from typing import List, Optional, Union

import aws_cdk as cdk
from aws_cdk import (
    aws_certificatemanager as certificatemanager,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_route53 as route53,
    aws_route53_targets as r53_targets,
)
from aws_cdk.aws_certificatemanager import CertificateValidation
from constructs import Construct

from .core.config import (
    DOMAIN_NAME,
    EXISTING_CERTIFICATE_ARN,
    LOCAL_DNS,
    STAGE,
    WORKER_CONFIG,
)
from .core.policies import PolicyConstruct


class ServiceConstruct(Construct):
    _airflows_url: str
    ecs_service: Union[ecs.Ec2Service]

    def __init__(
        self,
        parent: Construct,
        name: str,
        vpc: ec2.Vpc,
        cluster: ecs.ICluster,
        default_sg: ec2.ISecurityGroup,
        task_definition: Union[ecs.Ec2TaskDefinition],
        subnets: ec2.Subnet,
        asg_capacity_providers: List[ecs.AsgCapacityProvider],
        config: dict,
        is_worker_service: Optional[bool] = False,
    ) -> None:
        """
        Create a new Airflow service.

        Args:
            parent: write your description
            name: write your description
            vpc: write your description
            cluster: write your description
            default_sg: write your description
            task_definition: write your description
        """
        super().__init__(parent, name)

        # Attach required policies to Task Role
        policies = PolicyConstruct(self, f"{name}TaskPolicies")
        for policy in policies.managedPolicies:
            task_definition.task_role.add_managed_policy(policy)
        for policy in policies.policyStatements:
            task_definition.task_role.add_to_principal_policy(policy)

        # Create ec2 Service for Airflow
        service_name = (
            f"{STAGE}-{'worker' if is_worker_service else 'web'}-airflows"
        )
        self.ecs_service = ecs.Ec2Service(
            self,
            name,
            cluster=cluster,
            task_definition=task_definition,
            enable_execute_command=True,
            service_name=service_name,
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(
                    capacity_provider=p.capacity_provider_name,
                    weight=1,
                    base=1,
                )
                for p in asg_capacity_providers
            ],
            # not enabled in ec2 task network bridge mode
            # security_groups=[default_sg],
            # vpc_subnets={"subnets": subnets},
            # assign_public_ip=False,  # needed for deploy (BUG)
        )
        if is_worker_service:
            ...
            # self.configure_worker_auto_scaling()
        else:
            # Export Load Balancer DNS Name
            # which will be used to access Airflow UI
            self.attach_application_load_balancer(
                vpc=vpc, subnets=subnets, default_sg=default_sg, config=config
            )

    def attach_application_load_balancer(
        self,
        vpc: ec2.Vpc,
        subnets: ec2.Subnet,
        default_sg: ec2.CfnSecurityGroup,
        config: dict,
    ):
        """Attaches the load balancer to the service. ec2 needs this to be
        public accessible because of https://stackoverflow.com/a/60885984"""
        load_balancer = elbv2.ApplicationLoadBalancer(
            self,
            "AppLoadBalancer",
            vpc=vpc,
            security_group=default_sg,
            vpc_subnets={"subnets": subnets},
            internet_facing=True,
            load_balancer_name=f"{cdk.Stack.of(self).stack_name}-ALB",
        )

        if DOMAIN_NAME:
            main_protocol, main_port = elbv2.ApplicationProtocol.HTTPS, 443
            domain = DOMAIN_NAME
        else:
            main_protocol, main_port = elbv2.ApplicationProtocol.HTTP, 80
            domain = load_balancer.load_balancer_dns_name

        self.set_up_route53_local(load_balancer=load_balancer, vpc=vpc)
        target_group = elbv2.ApplicationTargetGroup(
            self,
            "TargetGroupELBv2",
            health_check=elbv2.HealthCheck(
                port="traffic-port",
                protocol=elbv2.Protocol.HTTP,
                path="/health",
                healthy_threshold_count=3,
                unhealthy_threshold_count=10,
                interval=cdk.Duration.seconds(30),
                timeout=cdk.Duration.seconds(10),
                healthy_http_codes="200",
            ),
            port=config["containerPort"],
            targets=[self.ecs_service],
            deregistration_delay=cdk.Duration.seconds(60),
            vpc=vpc,
        )
        main_listener = main_80_listener = load_balancer.add_listener(
            "80Listener",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            default_target_groups=[target_group],
        )
        if DOMAIN_NAME:  # allow HTTPS connections
            main_80_listener.add_action(  # REDIRECT EVERYTHING TO HTTPS
                "httpToHttpsAction",
                action=elbv2.ListenerAction.redirect(
                    protocol=elbv2.ApplicationProtocol.HTTPS.value,
                    permanent=True,
                    port="443",
                    host=DOMAIN_NAME,
                ),
            )
            main_listener = main_443_listener = load_balancer.add_listener(
                "443Listener",
                port=443,
                certificates=[self.set_up_route53(load_balancer)],
                protocol=elbv2.ApplicationProtocol.HTTPS,
                default_target_groups=[target_group],
            )
        main_listener.add_action(
            "redirectWwwToNonWwwAction",
            conditions=[
                elbv2.ListenerCondition.host_headers(values=[f"www.{domain}"])
            ],
            action=elbv2.ListenerAction.redirect(host=domain),
            priority=1,
        )
        load_balancer.add_listener("8080Listener", port=8080).add_action(
            "forwardToTGDefaultLocalAction",
            action=elbv2.ListenerAction.forward([target_group]),
        )
        self._airflows_url = (
            f"{main_protocol.value.lower()}://{domain}:{main_port}/"
        )
        return target_group

    def set_up_route53(
        self, load_balancer: elbv2.ApplicationLoadBalancer
    ) -> certificatemanager.Certificate:
        """
        Create route53 hosted zone and certificate.

        Args:
            self: write your description
            load_balancer: write your description
        """
        # create route 53 hosted zone, (must previously own the base domain)
        zone = route53.HostedZone(
            self, "r53-public-zone", zone_name=DOMAIN_NAME
        )
        zone.apply_removal_policy(cdk.RemovalPolicy.RETAIN)  # delete easily
        route53.ARecord(
            self,
            "wwwpublicArecord",
            zone=zone,
            record_name=f"www.{DOMAIN_NAME}",
            target=route53.RecordTarget.from_alias(
                r53_targets.LoadBalancerTarget(load_balancer)
            ),
        )
        route53.ARecord(
            self,
            "publicArecord",
            target=route53.RecordTarget.from_alias(
                r53_targets.LoadBalancerTarget(load_balancer)
            ),
            zone=zone,
        )
        if EXISTING_CERTIFICATE_ARN:
            certificate = certificatemanager.Certificate.from_certificate_arn(
                self, "web-certificate", EXISTING_CERTIFICATE_ARN
            )
        else:
            certificate = certificatemanager.Certificate(
                self,
                "web-certificate",
                domain_name=DOMAIN_NAME,
                subject_alternative_names=[f"www.{DOMAIN_NAME}"],
                validation=CertificateValidation.from_dns(zone),
            )
            # preserve 1 unique certificate to retain security fingerprints
            certificate.apply_removal_policy(cdk.RemovalPolicy.RETAIN)
        return certificate

    def set_up_route53_local(
        self, load_balancer: elbv2.ApplicationLoadBalancer, vpc: ec2.IVpc
    ):
        """
        Sets up route53 for the local load balancer.

        Args:
            self: write your description
            load_balancer: write your description
            vpc: write your description
        """
        zone = route53.HostedZone(
            self, "r53-local-zone", zone_name=LOCAL_DNS, vpcs=[vpc]
        )
        zone.apply_removal_policy(cdk.RemovalPolicy.DESTROY)
        route53.ARecord(
            self,
            "privateArecord",
            target=route53.RecordTarget.from_alias(
                r53_targets.LoadBalancerTarget(load_balancer)
            ),
            zone=zone,
        ).apply_removal_policy(cdk.RemovalPolicy.DESTROY)

    def configure_worker_auto_scaling(
        self, config: dict = WORKER_CONFIG["workerAutoScalingConfig"]
    ):
        """Configures scaling for the worker."""
        scaling = self.ecs_service.auto_scale_task_count(
            max_capacity=config["maxTaskCount"],
            min_capacity=config["minTaskCount"],
        )
        if config.get("cpuUsagePercent"):
            scaling.scale_on_cpu_utilization(
                "CpuScaling",
                target_utilization_percent=config["cpuUsagePercent"],
                scale_in_cooldown=cdk.Duration.seconds(60),
                scale_out_cooldown=cdk.Duration.seconds(60),
            )
        if config.get("memUsagePercent"):
            scaling.scale_on_memory_utilization(
                "MemoryScaling",
                target_utilization_percent=config["memUsagePercent"],
                scale_in_cooldown=cdk.Duration.seconds(60),
                scale_out_cooldown=cdk.Duration.seconds(60),
            )

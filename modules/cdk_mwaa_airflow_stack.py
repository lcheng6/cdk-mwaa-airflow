from typing import Any, Dict, List, Literal, Mapping, Optional

import aws_cdk as cdk
import yaml
from aws_cdk import CfnTag, NestedStack, Stack, Tags
from aws_cdk import aws_ec2 as ec2  # Duration,; aws_sqs as sqs,
from aws_cdk import aws_mwaa as mwaa
from constructs import Construct


class CdkMwaaAirflowStack(Stack):
    def __init__(
        self, scope: Construct, construct_id: str, vpc_id: str = None, vpc_cidr_assignment: str = None, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if vpc_id:
            # if vpc_id is given, lookup the vpc_id
            self._vpc = ec2.Vpc.from_lookup(
                self,
                "VpcLookupFromId",
                vpc_id = vpc_id
            )
            self._vpc_id = vpc_id
        else:
            # Create a new VPC, when one isn't defined

            subnet_configurations: List[Any] = [
                ec2.SubnetConfiguration(
                    cidr_mask=24, name="PublicSubnet", subnet_type=ec2.SubnetType.PUBLIC
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=20,
                    name="PrivateWithNatSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_NAT,
                ),
                ec2.SubnetConfiguration(
                    cidr_mask=24,
                    name="IsolatedSubnet",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                ),
            ]
            self._vpc = ec2.Vpc(
                self,
                f"VpcStack",
                cidr=vpc_cidr_assignment,
                vpc_name=f"MwaaNewVPC",
                max_azs=2,
                nat_gateways=1,
                subnet_configuration=subnet_configurations,
            )

            self._vpc_id = self._vpc.vpc_id

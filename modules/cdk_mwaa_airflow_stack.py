from typing import Any, Dict, List, Literal, Mapping, Optional

import aws_cdk as cdk
import yaml
from aws_cdk import CfnOutput, CfnTag, NestedStack, Stack, Tags
from aws_cdk import aws_ec2 as ec2  # Duration,; aws_sqs as sqs,
from aws_cdk import aws_iam as iam
from aws_cdk import aws_mwaa as mwaa
from aws_cdk import aws_s3 as s3
from constructs import Construct


class CdkMwaaAirflowStack(Stack):
    @property
    def vpc_id(self) -> str:
        return self._vpc.vpc_id

    def __init__(
        self,
        scope: Construct,
        construct_id: str,
        vpc_id: str = None,
        dags_s3_bucket_name: str = None,
        vpc_cidr_assignment: str = None,
        create_vpc:bool = True,
        create_mwaa:bool = True,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        if create_vpc:
            if vpc_id:
                # if vpc_id is given, lookup the vpc_id
                self._vpc = ec2.Vpc.from_lookup(self, "VpcLookupFromId", vpc_id=vpc_id)
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


            private_subnets: List[ec2.ISubnet] = self._vpc.private_subnets
            private_subnet_ids: List[str] = [subnet.subnet_id for subnet in private_subnets]

        if create_mwaa:
            mwaa_security_group = ec2.SecurityGroup(
                self,
                "MwaaSecurityGroup",
                vpc=self._vpc,
                allow_all_outbound=True,
            )

            dags_s3_bucket = s3.Bucket(
                self,
                "DagsBucket",
                auto_delete_objects=True,
                enforce_ssl=True,
                public_read_access=False,
                bucket_name=dags_s3_bucket_name,
                removal_policy=cdk.RemovalPolicy.DESTROY
            )
            # dags_s3_bucket.apply_removal_policy(policy=cdk.RemovalPolicy.DESTROY)

            mwaa_environment_s3_bucket = s3.Bucket(
                self,
                "MwaaEnvironmentBucket",
                auto_delete_objects=True,
                enforce_ssl=True,
                public_read_access=False,
                removal_policy=cdk.RemovalPolicy.DESTROY
            )
            # mwaa_environment_s3_bucket.apply_removal_policy(
            #     policy=cdk.RemovalPolicy.DESTROY
            # )

            mwaa_execution_role = iam.Role(
                self,
                "MwaaExecutionRole",
                assumed_by=iam.ServicePrincipal("airflow.amazonaws.com")
            )
            mwaa_environemnt_name = "ExperimentMwaa"
            mwaa_execution_role.attach_inline_policy(
                policy=iam.Policy(
                    self,
                    "MwaaExecutionPolicy",
                    statements=[
                        iam.PolicyStatement(
                            actions=["airflow:PublishMetrics"],
                            resources=[
                                f"arn:aws:airflow:{self.region}:{self.account}:environment/{mwaa_environemnt_name}"
                            ],
                        ),
                        iam.PolicyStatement(
                            effect=iam.Effect.DENY,
                            actions=["s3:ListAllMyBuckets"],
                            resources=[
                                mwaa_environment_s3_bucket.bucket_arn,
                                f"{mwaa_environment_s3_bucket.bucket_arn}/*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["s3:GetObject*", "s3:GetBucket*", "s3:List*"],
                            resources=[
                                mwaa_environment_s3_bucket.bucket_arn,
                                f"{mwaa_environment_s3_bucket.bucket_arn}/*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["logs:DescribeLogGroups"],
                            resources=[
                                "*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "logs:CreateLogStream",
                                "logs:CreateLogGroup",
                                "logs:PutLogEvents",
                                "logs:GetLogEvents",
                                "logs:GetLogRecord",
                                "logs:GetLogGroupFields",
                                "logs:GetQueryResults",
                                "logs:DescribeLogGroups",
                            ],
                            resources=[
                                f"arn:aws:logs:{self.region}:{self.account}:log-group:airflow-*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=["cloudwatch:PutMetricData"],
                            resources=[
                                "*",
                            ],
                        ),
                        iam.PolicyStatement(
                            actions=[
                                "sqs:ChangeMessageVisibility",
                                "sqs:DeleteMessage",
                                "sqs:GetQueueAttributes",
                                "sqs:GetQueueUrl",
                                "sqs:ReceiveMessage",
                                "sqs:SendMessage",
                            ],
                            resources=[
                                f"arn:aws:sqs:{self.region}:*:airflow-celery-*",
                            ],
                        ),
                        # iam.PolicyStatement(
                        #     actions=[
                        #         "kms:Decrypt",
                        #         "kms:DescribeKey",
                        #         "kms:GenerateDataKey*",
                        #         "kms:Encrypt",
                        #     ],
                        #     not_resources=f"arn:aws:kms:*:{self.account}:key/*",
                        #     conditions={
                        #         "StringLike": {
                        #             "kms:ViaService": f"sqs.{self.region}.amazonaws.com"
                        #         }
                        #     },
                        # ),
                    ],
                )
            )

            # mwaa_execution_role =

            # cfn_environment = mwaa.CfnEnvironment(
            #     self,
            #     "MyMwaaEnvironment",
            #     name="ExperimentMwaa",
            #     # the properties below are optional
            #     # airflow_configuration_options=airflow_configuration_options,
            #     airflow_version="2.0.2",
            #     # dag_s3_path="dagS3Path",
            #     environment_class="mw1.small",
            #     execution_role_arn=mwaa_execution_role.role_arn,
            #     # kms_key="kmsKey",
            #     # logging_configuration=mwaa.CfnEnvironment.LoggingConfigurationProperty(
            #     #     dag_processing_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
            #     #         cloud_watch_log_group_arn="cloudWatchLogGroupArn",
            #     #         enabled=False,
            #     #         log_level="logLevel",
            #     #     ),
            #     #     scheduler_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
            #     #         cloud_watch_log_group_arn="cloudWatchLogGroupArn",
            #     #         enabled=False,
            #     #         log_level="logLevel",
            #     #     ),
            #     #     task_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
            #     #         cloud_watch_log_group_arn="cloudWatchLogGroupArn",
            #     #         enabled=False,
            #     #         log_level="logLevel",
            #     #     ),
            #     #     webserver_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
            #     #         cloud_watch_log_group_arn="cloudWatchLogGroupArn",
            #     #         enabled=False,
            #     #         log_level="logLevel",
            #     #     ),
            #     #     worker_logs=mwaa.CfnEnvironment.ModuleLoggingConfigurationProperty(
            #     #         cloud_watch_log_group_arn="cloudWatchLogGroupArn",
            #     #         enabled=False,
            #     #         log_level="logLevel",
            #     #     ),
            #     # ),
            #     max_workers=50,
            #     min_workers=1,
            #     network_configuration=mwaa.CfnEnvironment.NetworkConfigurationProperty(
            #         security_group_ids=[mwaa_security_group.security_group_id],
            #         subnet_ids=private_subnet_ids,
            #     ),
            #     # plugins_s3_object_version="pluginsS3ObjectVersion",
            #     # plugins_s3_path="pluginsS3Path",
            #     # requirements_s3_object_version="requirementsS3ObjectVersion",
            #     # requirements_s3_path="requirementsS3Path",
            #     # schedulers=123,
            #     # source_bucket_arn="sourceBucketArn",
            #     # tags=tags,
            #     # webserver_access_mode="webserverAccessMode",
            #     # weekly_maintenance_window_start="weeklyMaintenanceWindowStart",
            # )

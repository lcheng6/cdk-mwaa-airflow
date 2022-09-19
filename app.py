#!/usr/bin/env python3
import os

import aws_cdk as cdk

from modules.cdk_mwaa_airflow_stack import CdkMwaaAirflowStack

# there parameters need to be set before running the project.
CDK_DEFAULT_ACCOUNT = os.environ.get("CDK_DEFAULT_ACCOUNT")

CDK_DEFAULT_REGION = os.environ.get("CDK_DEFAULT_REGION")

cdk_env = cdk.Environment(account=CDK_DEFAULT_ACCOUNT, region=CDK_DEFAULT_REGION)

app = cdk.App()
CdkMwaaAirflowStack(
    app,
    "CdkMwaaAirflowStack",
)

app.synth()

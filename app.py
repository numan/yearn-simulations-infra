#!/usr/bin/env python3
import os

from aws_cdk import core

from yearn_simulations_infra.yearn_simulations_infra_stack import (
    YearnSimScheduledTasksInfraStack,
    YearnSimulationsInfraStack,
    SharedStack,
)

app = core.App()

vpc_id = os.environ.get("CDK_DEPLOY_VPC", None)
if not vpc_id:
    raise Exception(
        "Can not deploy without an existing VPC. Please specify which VPC you want to deploy to using the `CDK_DEPLOY_VPC` environment variable."
    )

shared_stack = SharedStack(
    app,
    "SharedStack",
    env=core.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
    ),
)

YearnSimulationsInfraStack(
    app,
    "YearnSimulationsInfraStack",
    vpc_id=vpc_id,
    log_group=shared_stack.log_group,
    container_repo=shared_stack.container_repo,
    env=core.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
    ),
)

YearnSimScheduledTasksInfraStack(
    app,
    "YearnSimScheduledTasksInfraStack",
    vpc_id=vpc_id,
    log_group=shared_stack.log_group,
    container_repo=shared_stack.container_repo,
    env=core.Environment(
        account=os.environ.get("CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]),
        region=os.environ.get("CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]),
    ),
)

app.synth()

#!/usr/bin/env python3
import os

from aws_cdk import core as cdk

from yearn_simulations_infra.yearn_simulations_infra_stack import (
    SharedStack, YearnSimScheduledTasksInfraStack, YearnSimulationsInfraStack)

app = cdk.App()


class ApplicationStack(cdk.Stack):
    def __init__(
        self, scope: cdk.Construct, construct_id: str, vpc_id: str, **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        shared_stack = SharedStack(
            self,
            "SharedStack",
            env=cdk.Environment(
                account=os.environ.get(
                    "CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]
                ),
                region=os.environ.get(
                    "CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]
                ),
            ),
        )

        YearnSimulationsInfraStack(
            self,
            "YearnSimulationsInfraStack",
            vpc_id=vpc_id,
            log_group=shared_stack.log_group,
            container_repo=shared_stack.container_repo,
            env=cdk.Environment(
                account=os.environ.get(
                    "CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]
                ),
                region=os.environ.get(
                    "CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]
                ),
            ),
        )

        YearnSimScheduledTasksInfraStack(
            self,
            "YearnSimScheduledTasksInfraStack",
            vpc_id=vpc_id,
            log_group=shared_stack.log_group,
            container_repo=shared_stack.container_repo,
            env=cdk.Environment(
                account=os.environ.get(
                    "CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]
                ),
                region=os.environ.get(
                    "CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]
                ),
            ),
        )


vpc_id = os.environ.get("CDK_DEPLOY_VPC", None)
if not vpc_id:
    raise Exception(
        "Can not deploy without an existing VPC. Please specify which VPC you want to deploy to using the `CDK_DEPLOY_VPC` environment variable."
    )

prod = ApplicationStack(app, "Production", vpc_id)
# staging = ApplicationStack(app, "Staging", staging_vpc_id)
# dev = ApplicationStack(app, "Dev", dev_vpc_id)

app.synth()

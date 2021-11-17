#!/usr/bin/env python3
import os
import sys
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules

from aws_cdk import core as cdk
from brownie import project

from yearn_simulations_infra.yearn_simulations_infra_stack import (
    SharedStack,
    YearnHarvestBotInfraStack,
    YearnSimScheduledTasksInfraStack,
    YearnSimulationsInfraStack,
)

app = cdk.App()


class ApplicationStack(cdk.Stack):
    def __init__(
        self, scope: cdk.Construct, construct_id: str, vpc_id: str, path: Path, **kwargs
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

        # Add root to sys path so we can import more predictively
        root_path = Path(".").resolve().root
        sys.path.insert(0, root_path)

        try:
            brownie_project = project.load(project_path=path)
            brownie_project.load_config()

            brownie_project._add_to_main_namespace()

            script_path = brownie_project._path.joinpath(
                brownie_project._structure["scripts"]
            )

            brownie_project_module = import_module("scheduler")

            # import all script modules so we can be
            scripts_module = ".".join(script_path.parts[1:])
            for (_, module_name, _) in iter_modules([script_path]):
                # import the module and iterate through its attributes
                import_module(f"{scripts_module}.{module_name}")

            scheduled_scripts = (
                brownie_project_module.schedule_scripts_storage.scheduled_scripts
            )

            YearnSimScheduledTasksInfraStack(
                self,
                "YearnSimScheduledTasksInfraStack",
                vpc_id=vpc_id,
                log_group=shared_stack.log_group,
                container_repo=shared_stack.container_repo,
                scheduled_scripts=scheduled_scripts,
                env=cdk.Environment(
                    account=os.environ.get(
                        "CDK_DEPLOY_ACCOUNT", os.environ["CDK_DEFAULT_ACCOUNT"]
                    ),
                    region=os.environ.get(
                        "CDK_DEPLOY_REGION", os.environ["CDK_DEFAULT_REGION"]
                    ),
                ),
            )

        finally:
            sys.path.remove(root_path)
            brownie_project._remove_from_main_namespace()

        YearnHarvestBotInfraStack(
            self,
            "YearnHarvestBotInfraStack",
            vpc_id=vpc_id,
            log_group=shared_stack.log_group,
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

yearn_simulations_dir = os.environ.get("YEARN_SIMULATIONS_WORKSPACE")
if not yearn_simulations_dir:
    raise Exception(
        "Can not find Yearn Simulations workspace. Please specify the workspace environment variable."
    )

path = Path(yearn_simulations_dir)
if not path.exists() or not path.is_dir():
    raise Exception(
        "Can not find Yearn Simulations workspace. Please specify the workspace directory."
    )

prod = ApplicationStack(app, "Production", vpc_id, path)
# staging = ApplicationStack(app, "Staging", staging_vpc_id)
# dev = ApplicationStack(app, "Dev", dev_vpc_id)

app.synth()

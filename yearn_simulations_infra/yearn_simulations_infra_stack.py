import json
from typing import Any

import aws_cdk.aws_applicationautoscaling as app_autoscaling
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_ecs_patterns as ecs_patterns
import aws_cdk.aws_logs as logs
import aws_cdk.aws_secretsmanager as secrets
from aws_cdk import core as cdk


from yearn_scheduled_task import YearnScheduledTaskStack


class YearnHarvestBotInfraStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        vpc_id: str,
        log_group: logs.LogGroup,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        self._vpc = ec2.Vpc.from_lookup(
            self,
            "VPCResource",
            vpc_id=vpc_id,
        )
        self._container_repository = ecr.Repository(self, "YearnHarvestBotRepository")
        self._container_repository.add_lifecycle_rule(
            tag_status=ecr.TagStatus.UNTAGGED, max_image_age=cdk.Duration.days(7)
        )

        self._secrets_manager = secrets.Secret(
            self,
            "YearnHarvestBotSecrets",
            generate_secret_string=secrets.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        "TELEGRAM_CHANNEL_ID": "",
                        "HARVEST_COLLECTOR_BOT": "",
                        "DISCORD_SECRET": "",
                        "INFURA_NODE": "",
                    }
                ),
                generate_string_key="password",  # Needed just to we can provision secrets manager with a template. Not used.
            ),
        )

        container_secrets = {
            "TELEGRAM_CHANNEL_ID": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "TELEGRAM_CHANNEL_ID"
            ),
            "HARVEST_COLLECTOR_BOT": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "HARVEST_COLLECTOR_BOT"
            ),
            "DISCORD_SECRET": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "DISCORD_SECRET"
            ),
            "INFURA_NODE": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "INFURA_NODE"
            ),
        }

        self._environment = {
            "ENVIRONMENT": "PROD",
            "DELAY_MINUTES": "20",
            "MINUTES": "20",
        }

        # General ECS Cluster
        self._yearn_harvest_bot_ecs_cluster = (
            self._create_yearn_harvest_bot_ecs_cluster(self._vpc)
        )

        # All scheduled tasks:
        scheduled_tasks = [
            ecs_patterns.ScheduledFargateTask(
                self,
                "HarvestBotTask",
                cluster=self._yearn_harvest_bot_ecs_cluster,
                scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                    image=ecs.ContainerImage.from_ecr_repository(
                        self._container_repository, "latest"
                    ),
                    log_driver=ecs.AwsLogDriver(
                        log_group=log_group,
                        stream_prefix="HarvestBotTask",
                        mode=ecs.AwsLogDriverMode.NON_BLOCKING,
                    ),
                    environment=self._environment,
                    secrets=container_secrets,
                    command=["ts-node", "runner.ts"],
                    cpu=2048,
                    memory_limit_mib=4096,
                ),
                schedule=app_autoscaling.Schedule.cron(
                    minute="20",
                ),  # Every day at 4pm
                platform_version=ecs.FargatePlatformVersion.LATEST,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            )
        ]

        # Permissions
        for scheduled_task in scheduled_tasks:
            self._container_repository.grant_pull(
                scheduled_task.task_definition.obtain_execution_role()
            )

    def _create_yearn_harvest_bot_ecs_cluster(self, vpc: ec2.IVpc):
        return ecs.Cluster(
            self,
            "YearnHarvestBotCluster",
            enable_fargate_capacity_providers=True,
            vpc=vpc,
        )


class SharedStack(cdk.Stack):
    @property
    def log_group(self):
        return self._log_group

    @property
    def container_repo(self):
        return self._container_repository

    def __init__(self, scope: cdk.Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self._log_group = logs.LogGroup(
            self, "YearnBotsLogGroup", retention=logs.RetentionDays.ONE_MONTH
        )

        self._container_repository = ecr.Repository(self, "SimScheduledTasksRepository")
        self._container_repository.add_lifecycle_rule(
            tag_status=ecr.TagStatus.UNTAGGED, max_image_age=cdk.Duration.days(7)
        )


class YearnSimScheduledTasksInfraStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        vpc_id: str,
        log_group: logs.LogGroup,
        container_repo: ecr.Repository,
        scheduled_scripts: Any,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        self._vpc = ec2.Vpc.from_lookup(
            self,
            "VPCResource",
            vpc_id=vpc_id,
        )

        self._secrets_manager = secrets.Secret(
            self,
            "YearnSimScheduledTasksSecrets",
            generate_secret_string=secrets.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        "INFURA_ID": "",
                        "WEB3_INFURA_PROJECT_ID": "",
                        "TELEGRAM_BOT_KEY": "",
                    }
                ),
                generate_string_key="password",  # Needed just to we can provision secrets manager with a template. Not used.
            ),
        )

        # General ECS Cluster
        self._yearn_sim_tasks_ecs_cluster = self._create_yearn_sim_tasks_ecs_cluster(
            self._vpc
        )

        base_environment = {
            "ENV": "PROD",
        }
        base_container_secrets = {
            "INFURA_ID": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "INFURA_ID"
            ),
            "WEB3_INFURA_PROJECT_ID": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "WEB3_INFURA_PROJECT_ID"
            ),
            "TELEGRAM_BOT_KEY": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "TELEGRAM_BOT_KEY"
            ),
        }

        # All scheduled tasks:
        scheduled_tasks = []
        for scheduled_script in scheduled_scripts:
            script_name = scheduled_script.script.__module__.split(".")[-1]

            # Add any additional environment variables
            environment = base_environment.copy()
            environment["TELEGRAM_CHAT_ID"] = scheduled_script.telegram_chat_id
            if scheduled_script.environment:
                environment.update(scheduled_script.environment)

            # Add additional secrets to the container
            container_secrets = base_container_secrets.copy()
            additional_container_secrets = {
                secret_name.upper(): ecs.Secret.from_secrets_manager(
                    self._secrets_manager, secret_name.upper()
                )
                for secret_name in scheduled_script.secrets
            }
            container_secrets.update(additional_container_secrets)

            YearnScheduledTaskStack(
                self,
                f"ScheduledTask{script_name}",
                script_name=script_name,
                environment=environment,
                secrets=container_secrets,
                schedule=app_autoscaling.Schedule.cron(
                    day=scheduled_script.day,
                    hour=scheduled_script.hour,
                    minute=scheduled_script.minute,
                    month=scheduled_script.month,
                    week_day=scheduled_script.week_day,
                    year=scheduled_script.year,
                ),
                log_group=log_group,
                container_repo=container_repo,
                cluster=self._yearn_sim_tasks_ecs_cluster,
                **kwargs,
            )

        # Permissions
        for scheduled_task in scheduled_tasks:
            container_repo.grant_pull(
                scheduled_task.task_definition.obtain_execution_role()
            )

    def _create_yearn_sim_tasks_ecs_cluster(self, vpc: ec2.IVpc):
        return ecs.Cluster(
            self,
            "YearnSimScheduledTasksCluster",
            enable_fargate_capacity_providers=True,
            vpc=vpc,
        )


class YearnSimulationsInfraStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        vpc_id: str,
        log_group: logs.LogGroup,
        container_repo: ecr.Repository,
        **kwargs,
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here
        self._vpc = ec2.Vpc.from_lookup(
            self,
            "VPCResource",
            vpc_id=vpc_id,
        )

        self._secrets_manager = secrets.Secret(
            self,
            "YearnSimulationsSecrets",
            generate_secret_string=secrets.SecretStringGenerator(
                secret_string_template=json.dumps(
                    {
                        "TELEGRAM_BOT_KEY": "",
                        "POLLER_KEY": "",
                        "TELEGRAM_YFI_HARVEST_SIMULATOR": "",
                        "INFURA_ID": "",
                        "WEB3_INFURA_PROJECT_ID": "",
                    }
                ),
                generate_string_key="password",  # Needed just to we can provision secrets manager with a template. Not used.
            ),
        )

        # General ECS Cluster
        self._yearn_simulations_ecs_cluster = (
            self._create_yearn_simulations_ecs_cluster(self._vpc)
        )

        # Create Services

        ## Create a service for the simulator bot
        self._create_simulator_bot_fargate_service(
            self._yearn_simulations_ecs_cluster,
            container_repo,
            log_group,
            self._secrets_manager,
        )

    def _create_yearn_simulations_ecs_cluster(self, vpc: ec2.IVpc):
        return ecs.Cluster(
            self,
            "YearnSimulationsCluster",
            enable_fargate_capacity_providers=True,
            vpc=vpc,
        )

    def _create_simulator_bot_fargate_service(
        self,
        ecs_cluster: ecs.Cluster,
        repository: ecr.Repository,
        log_group: logs.LogGroup,
        secrets_manager: secrets.Secret,
    ):

        # Create a task definition and add a container to it
        # A limited set of values can be provided for `cpu` and `memory_limit`.
        # See documentation here: https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-cpu-memory-error.html
        fargate_task_definition = ecs.FargateTaskDefinition(
            self,
            "SimulatorBotTaskDefinition",
            cpu=1024,
            memory_limit_mib=2048,
            ephemeral_storage_gib=21,
        )

        # During creation we'll just use the Amazon ECS sample image, but
        # in practice, we will pull images from our ECR repository
        fargate_task_definition.add_container(
            "SimulatorBotContainer",
            image=ecs.ContainerImage.from_registry("amazon/amazon-ecs-sample"),
            logging=ecs.AwsLogDriver(
                log_group=log_group,
                stream_prefix="SimulatorContainer",
                mode=ecs.AwsLogDriverMode.NON_BLOCKING,
            ),
            environment={
                "ENVIRONMENT": "prod",
            },
            secrets={
                "TELEGRAM_BOT_KEY": ecs.Secret.from_secrets_manager(
                    secrets_manager, "TELEGRAM_BOT_KEY"
                ),
                "POLLER_KEY": ecs.Secret.from_secrets_manager(
                    secrets_manager, "POLLER_KEY"
                ),
                "TELEGRAM_YFI_HARVEST_SIMULATOR": ecs.Secret.from_secrets_manager(
                    secrets_manager, "TELEGRAM_YFI_HARVEST_SIMULATOR"
                ),
                "INFURA_ID": ecs.Secret.from_secrets_manager(
                    secrets_manager, "INFURA_ID"
                ),
                "WEB3_INFURA_PROJECT_ID": ecs.Secret.from_secrets_manager(
                    secrets_manager, "WEB3_INFURA_PROJECT_ID"
                ),
            },
        )

        ecs.FargateService(
            self,
            "SimulatorBotService",
            cluster=ecs_cluster,
            task_definition=fargate_task_definition,
            desired_count=1,
            assign_public_ip=True,
            circuit_breaker=ecs.DeploymentCircuitBreaker(rollback=True),
            capacity_provider_strategies=[
                ecs.CapacityProviderStrategy(capacity_provider="FARGATE", weight=1),
                ecs.CapacityProviderStrategy(
                    capacity_provider="FARGATE_SPOT", weight=2
                ),
            ],
            enable_execute_command=True,
        )

        # Permissions

        ## Grant pull permission to the task so we don't have to pass credentials around
        repository.grant_pull(fargate_task_definition.obtain_execution_role())

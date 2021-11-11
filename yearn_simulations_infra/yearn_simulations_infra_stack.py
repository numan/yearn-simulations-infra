import json

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_ecs_patterns as ecs_patterns
import aws_cdk.aws_applicationautoscaling as app_autoscaling
import aws_cdk.aws_logs as logs
import aws_cdk.aws_secretsmanager as secrets
from aws_cdk import core as cdk


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
        **kwargs
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
                        ## Bribe Bot
                        "TELEGRAM_YFI_DEV_BOT": "",
                        "TELEGRAM_CHAT_ID_BRIBE": "",
                        ## FTM Bot
                        "FTM_BOT_KEY": "",
                        "FTM_GROUP": "",
                        ## SSC Bot
                        "SSC_BOT_KEY": "",
                        "PROD_GROUP": "",
                        ## Credit Available
                        "TELEGRAM_CHAT_ID_CREDIT_TRACKER": "",
                    }
                ),
                generate_string_key="password",  # Needed just to we can provision secrets manager with a template. Not used.
            ),
        )

        # General ECS Cluster
        self._yearn_sim_tasks_ecs_cluster = self._create_yearn_sim_tasks_ecs_cluster(
            self._vpc
        )

        environment = {
            "ENV": "PROD",
            "USE_DYNAMIC_LOOKUP": "True",
        }
        container_secrets = {
            "INFURA_ID": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "INFURA_ID"
            ),
            "WEB3_INFURA_PROJECT_ID": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "WEB3_INFURA_PROJECT_ID"
            ),
            "TELEGRAM_YFI_DEV_BOT": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "TELEGRAM_YFI_DEV_BOT"
            ),
            "TELEGRAM_CHAT_ID_BRIBE": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "TELEGRAM_CHAT_ID_BRIBE"
            ),
            "FTM_BOT_KEY": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "FTM_BOT_KEY"
            ),
            "SSC_BOT_KEY": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "SSC_BOT_KEY"
            ),
            "PROD_GROUP": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "PROD_GROUP"
            ),
            "TELEGRAM_CHAT_ID_CREDIT_TRACKER": ecs.Secret.from_secrets_manager(
                self._secrets_manager, "TELEGRAM_CHAT_ID_CREDIT_TRACKER"
            ),
        }

        # All scheduled tasks:
        scheduled_tasks = [
            ecs_patterns.ScheduledFargateTask(
                self,
                "BribeBotTask",
                cluster=self._yearn_sim_tasks_ecs_cluster,
                scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                    image=ecs.ContainerImage.from_ecr_repository(
                        container_repo, "latest"
                    ),
                    log_driver=ecs.AwsLogDriver(
                        log_group=log_group,
                        stream_prefix="BribeBotTask",
                        mode=ecs.AwsLogDriverMode.NON_BLOCKING,
                    ),
                    environment=environment,
                    secrets=container_secrets,
                    command=["run.sh", "bribe_bot"],
                    cpu=2048,
                    memory_limit_mib=4096,
                ),
                schedule=app_autoscaling.Schedule.cron(
                    minute="0", hour="16"
                ),  # Every day at 4pm
                platform_version=ecs.FargatePlatformVersion.LATEST,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            ),
            ecs_patterns.ScheduledFargateTask(
                self,
                "FTMBot",
                cluster=self._yearn_sim_tasks_ecs_cluster,
                scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                    image=ecs.ContainerImage.from_ecr_repository(
                        container_repo, "latest"
                    ),
                    log_driver=ecs.AwsLogDriver(
                        log_group=log_group,
                        stream_prefix="FTMBot",
                        mode=ecs.AwsLogDriverMode.NON_BLOCKING,
                    ),
                    environment=environment,
                    secrets=container_secrets,
                    command=["run.sh", "ftm_bot"],
                    cpu=2048,
                    memory_limit_mib=4096,
                ),
                schedule=app_autoscaling.Schedule.cron(
                    minute="0", hour="0,12"
                ),  # Every day at midnight and noon
                platform_version=ecs.FargatePlatformVersion.LATEST,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            ),
            ecs_patterns.ScheduledFargateTask(
                self,
                "SSCBot",
                cluster=self._yearn_sim_tasks_ecs_cluster,
                scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                    image=ecs.ContainerImage.from_ecr_repository(
                        container_repo, "latest"
                    ),
                    log_driver=ecs.AwsLogDriver(
                        log_group=log_group,
                        stream_prefix="SSCBot",
                        mode=ecs.AwsLogDriverMode.NON_BLOCKING,
                    ),
                    environment=environment,
                    secrets=container_secrets,
                    command=["run.sh", "ssc_bot"],
                    cpu=2048,
                    memory_limit_mib=4096,
                ),
                schedule=app_autoscaling.Schedule.cron(
                    minute="0", hour="0,8,16"
                ),  # Every day at midnight, 8am and 4pm
                platform_version=ecs.FargatePlatformVersion.LATEST,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            ),
            ecs_patterns.ScheduledFargateTask(
                self,
                "CreditsAvailableBot",
                cluster=self._yearn_sim_tasks_ecs_cluster,
                scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                    image=ecs.ContainerImage.from_ecr_repository(
                        container_repo, "latest"
                    ),
                    log_driver=ecs.AwsLogDriver(
                        log_group=log_group,
                        stream_prefix="CreditsAvailableBot",
                        mode=ecs.AwsLogDriverMode.NON_BLOCKING,
                    ),
                    environment=environment,
                    secrets=container_secrets,
                    command=["run.sh", "credits_available"],
                    cpu=2048,
                    memory_limit_mib=4096,
                ),
                schedule=app_autoscaling.Schedule.cron(
                    minute="30", hour="16"
                ),  # Every day at midnight, 8am and 4pm
                platform_version=ecs.FargatePlatformVersion.LATEST,
                subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
            ),
        ]

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
        **kwargs
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

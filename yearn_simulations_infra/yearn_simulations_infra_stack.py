import json

import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_logs as logs
import aws_cdk.aws_secretsmanager as secrets
from aws_cdk import core as cdk


class YearnSimulationsInfraStack(cdk.Stack):
    def __init__(
        self, scope: cdk.Construct, construct_id: str, vpc_id: str, **kwargs
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

        # Configure logging
        self._log_group = logs.LogGroup(
            self, "YearnSimulations", retention=logs.RetentionDays.ONE_MONTH
        )

        # General ECS Cluster
        self._yearn_simulations_ecs_cluster = (
            self._create_yearn_simulations_ecs_cluster(self._vpc)
        )

        # Create a repository where we can store all our containers
        self._repository = ecr.Repository(self, "SimulationsRepository")

        # Create Services

        ## Create a service for the simulator bot
        self._create_simulator_bot_fargate_service(
            self._yearn_simulations_ecs_cluster,
            self._repository,
            self._log_group,
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

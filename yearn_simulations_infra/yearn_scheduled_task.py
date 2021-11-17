import aws_cdk.aws_ecr as ecr
import aws_cdk.aws_logs as logs
from aws_cdk import core as cdk
import aws_cdk.aws_ecs as ecs
import aws_cdk.aws_ec2 as ec2
import aws_cdk.aws_ecs_patterns as ecs_patterns
import aws_cdk.aws_applicationautoscaling as app_autoscaling
import aws_cdk.aws_secretsmanager as secrets
from typing import Dict


class YearnScheduledTaskStack(cdk.Stack):
    def __init__(
        self,
        scope: cdk.Construct,
        construct_id: str,
        script_name: str,
        environment: Dict[str, str],
        secrets: Dict[str, secrets.Secret],
        schedule: app_autoscaling.Schedule,
        log_group: logs.LogGroup,
        container_repo: ecr.Repository,
        cluster: ecs.Cluster,
        cpu=1024,
        memory_limit=2048,
        **kwargs
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        task_name = f"{script_name}Task"
        ecs_patterns.ScheduledFargateTask(
            self,
            task_name,
            cluster=cluster,
            scheduled_fargate_task_image_options=ecs_patterns.ScheduledFargateTaskImageOptions(
                image=ecs.ContainerImage.from_ecr_repository(container_repo, "latest"),
                log_driver=ecs.AwsLogDriver(
                    log_group=log_group,
                    stream_prefix=task_name,
                    mode=ecs.AwsLogDriverMode.NON_BLOCKING,
                ),
                environment=environment,
                secrets=secrets,
                command=["/usr/src/app/run.sh", script_name],
                cpu=cpu,
                memory_limit_mib=memory_limit,
            ),
            schedule=schedule,
            platform_version=ecs.FargatePlatformVersion.LATEST,
            subnet_selection=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )

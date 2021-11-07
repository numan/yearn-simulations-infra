from diagrams import Diagram, Cluster
from diagrams.aws.compute import Fargate
from diagrams.aws.security import SecretsManager

with Diagram("Yearn Simulation Bot"):
    with Cluster("VPC"):
        with Cluster("Public Subnet"):
            with Cluster("ECS Service"):
                simulator_bot = Fargate("Container")

    secrets = SecretsManager("Secrets")

    simulator_bot >> secrets

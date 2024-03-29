import setuptools


with open("README.md") as fp:
    long_description = fp.read()


setuptools.setup(
    name="yearn_simulations_infra",
    version="0.0.1",

    description="An empty CDK Python app",
    long_description=long_description,
    long_description_content_type="text/markdown",

    author="author",

    package_dir={"": "yearn_simulations_infra"},
    packages=setuptools.find_packages(where="yearn_simulations_infra"),

    install_requires=[
        "aws-cdk.core==1.130.0",
        "aws-cdk.aws-ec2==1.130.0",
        "aws-cdk.aws-ecs==1.130.0", 
        "aws-cdk.aws-ecr==1.130.0", 
        "aws-cdk.aws-secretsmanager==1.130.0",
        "aws-cdk.aws-ecs-patterns==1.130.0",
        "aws-cdk.aws-applicationautoscaling==1.130.0"
    ],

    python_requires=">=3.6",

    classifiers=[
        "Development Status :: 4 - Beta",

        "Intended Audience :: Developers",

        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",

        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",

        "Typing :: Typed",
    ],
)

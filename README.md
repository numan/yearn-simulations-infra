
# Welcome to your CDK Python project!

This is a blank project for Python development with CDK.

The `cdk.json` file tells the CDK Toolkit how to execute your app.

This project is set up like a standard Python project.  The initialization
process also creates a virtualenv within this project, stored under the `.venv`
directory.  To create the virtualenv it assumes that there is a `python3`
(or `python` for Windows) executable in your path with access to the `venv`
package. If for any reason the automatic creation of the virtualenv fails,
you can create the virtualenv manually.

To manually create a virtualenv on MacOS and Linux:

```
$ python3 -m venv .venv
```

After the init process completes and the virtualenv is created, you can use the following
step to activate your virtualenv.

```
$ source .venv/bin/activate
```

If you are a Windows platform, you would activate the virtualenv like this:

```
% .venv\Scripts\activate.bat
```

Once the virtualenv is activated, you can install the required dependencies.

```
$ pip install -r requirements.txt
```

At this point you can now synthesize the CloudFormation template for this code.

```
$ cdk synth
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

# First Time Setup

This section will guide you through setting up your infrastructure for the simulation bot.

The infrastructure is defined using **[AWS Cloud Development Kit (AWS CDK)](https://aws.amazon.com/cdk/)**. AWS CDK is an open source software development framework to define your cloud application resources using familiar programming languages.

These definitions can then be synthesized to AWS CloudFormation Templates which can be deployed AWS.

## Initial Setup

Follow the steps to bootstrap your AWS Account to work with AWS CDK:

1. [Prerequisites](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html#getting_started_prerequisites) 
2. [Install AWS CDK Locally](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html#getting_started_install)
3. [Bootstrapping](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html#getting_started_bootstrap)

The infrastructure in this repository requires a VPC with at least one public subnet. If you don't have a VPC that meets this criteria or want to provision a new VPC for this project, you can follow the instructions [here](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/create-public-private-vpc.html).

## Creating the Infrastructure for the First Time

You can use the `cdk-deploy-to.sh` script to deploy the infrastructure for the first time and any subsequent updates to the infrastructure.

Usage:

```bash
> ./cdk-deploy-to.sh <AWS Account ID> <AWS Region> <AWS VPC ID>
```

Example:

```bash
> ./cdk-deploy-to.sh 1111111111 us-east-1 vpc-11111111
```

## Initializing Secrets

One of the resources created during the creation process is a **AWS Secrets Store**. Navigate to the newly created secrets store and modify the following values in the **Secret value** section:

1. TELEGRAM_YFI_HARVEST_SIMULATOR
2. WEB3_INFURA_PROJECT_ID
3. INFURA_ID
4. TELEGRAM_BOT_KEY
5. POLLER_KEY

## Deploy

Follow the instructions in https://github.com/yearn/yearn-simulations repo.

## Destroying The Environment

You can destroy the environment using CDK:

```bash
> CDK_DEPLOY_VPC="vpc-11111111" CDK_DEPLOY_ACCOUNT="1111111111" CDK_DEPLOY_REGION="us-east-1" cdk destroy
```
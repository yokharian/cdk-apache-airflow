
# Welcome to your CDK Python project!

## Deploying for the first time
 * you must have at least the vpc already deployed, this vpc must have 1 public subnet and 1 private/isolated subnet
 * read the main.py file to understand the handshake mechanisms used to reuse this vpc, do we use ssm
 * always you can use the `script_ssh_container.sh` file to fix the git repo located at`/shared-volume/git_repo`, this folder is a shared volume for all containers.

## Useful commands

 * `cdk ls`          list all stacks in the app
 * `cdk synth`       emits the synthesized CloudFormation template
 * `cdk deploy`      deploy this stack to your default AWS account/region
 * `cdk diff`        compare deployed stack with current state
 * `cdk docs`        open CDK documentation

Enjoy!

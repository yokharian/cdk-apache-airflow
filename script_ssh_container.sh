# install SessionManagerPlugin
# https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html#install-plugin-linux

# obtain your TASK_ID here !!!
# https://us-east-1.console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/airflows-dev/tasks
# https://us-east-1.console.aws.amazon.com/ecs/home?region=us-east-1#/clusters/airflows-prod/tasks

TASK_ID=1c002b1a94284cbe88fe5a850d520075

aws ecs execute-command  \
    --region us-east-1 \
    --cluster airflows-prod \
    --task $TASK_ID \
    --command "/bin/bash" \
    --interactive \
    --container WebserverContainer

# --container parameter is optional

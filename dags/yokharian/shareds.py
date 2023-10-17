import logging
import os
import sys
from os import getenv
from datetime import timedelta
from pathlib import Path
from typing import List

from airflow.hooks.base import BaseHook
from airflow.utils.trigger_rule import TriggerRule
from loguru import logger

STAGE = getenv("STAGE", "dev")
IS_PROD = STAGE == "prod"
DAGS_FOLDER_ALTERNATIVE_1 = Path(
    getenv("EFS_GIT_REPO_FULL_PATH", "/")
).joinpath("dags")
DAGS_FOLDER_ALTERNATIVE_2 = Path(getenv("AIRFLOW_HOME", "/")).joinpath("dags")
DAGS_FOLDER: Path = DAGS_FOLDER_ALTERNATIVE_1 or DAGS_FOLDER_ALTERNATIVE_2
YOKHARIAN_DAGS: Path = DAGS_FOLDER.joinpath("yokharian")


def basic_loguru(
    # https://loguru.readthedocs.io/en/stable/api/logger.html
    log_format="<level>{message}</level>",
    sink=sys.stderr,  # default in loguru
    colorize=False,
    level=logging.INFO,
    **kwargs,
):
    """
    Basic logging facility.

    Args:
        sink: write your description
        log_format: write your description
        colorize: write your description
        level: write your description
    """
    kwargs.setdefault("sink", sink)
    kwargs.setdefault("format", log_format)
    kwargs.setdefault("colorize", colorize)
    kwargs.setdefault("level", level)

    logger.remove()  # All configured handlers are removed
    logger.add(**kwargs)
    return logger


default_args = {
    # https://airflow.apache.org/docs/apache-airflow/2.3.1/concepts/
    "pool": "mainPool",  # where to run this dag
    "email": [],
    "owner": None,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 3 if IS_PROD else 0,
    "retry_delay": timedelta(minutes=15),
    # You can also say a task can only run if the previous run of the task
    # in the previous DAG Run succeeded
    # https://stackoverflow.com/questions/52103145/airflow-stops-scheduling-dagruns-after-task-failure
    "depends_on_past": False,
    # make sure you understand what it means -
    # all tasks immediately downstream of the previous task instance must
    # have succeeded. You can view how these properties are set from the
    # Task Instance Details page for your task.
    "wait_for_downstream": False,
    # time by which a task or DAG should have succeeded
    "sla": timedelta(minutes=15),
    "execution_timeout": timedelta(minutes=30),
    # https://marclamberti.com/blog/airflow-trigger-rules-all-you-need-to-know/
    "trigger_rule": TriggerRule.ALL_SUCCESS,
    # "queue": "bash_queue",
    "priority_weight": 1,  # default is 1, higher value, lower priority
    # "on_failure_callback": some_function,
    # "on_success_callback": some_other_function,
    # "on_retry_callback": another_function,
    # "sla_miss_callback": yet_another_function,
    "run_as_user": None,
}


import json
import shutil
from os import environ, getenv

BOOL_MAP = {"True": True, "False": False}

try:
    from airflow.hooks.base import BaseHook

    # required airflow connection, read
    # https://airflow.apache.org/docs/apache-airflow-providers-influxdb/1.1.0/connections/influxdb.html
    INFLUX_CONN: str = str(
        BaseHook.get_connection("InfluxDBConn").get_extra()
    )
    environ["INFLUX_TOKEN"] = json.loads(INFLUX_CONN).get("token", "")

    # required to retrieve & STORAGE logs in s3, read
    # https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/connections/aws.html
    # https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/logging/s3-task-handler.html
    # without this there will be no log messages
    BaseHook.get_connection("AWSS3LogStorage")

except ImportError:
    # disable for virtualenv operators, enable for all other dags, because
    # of virtualenv operators may not have airflow pip library installed
    # the priority is to ensure that the webServer & scheduler container's
    # has these connections.
    ...

if not shutil.which("virtualenv"):
    raise ModuleNotFoundError(
        "most dags listed here requires virtualenv library,"
        " please install it."
    )

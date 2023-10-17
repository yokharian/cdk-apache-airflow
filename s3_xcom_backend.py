from os import getenv
from typing import Any
import uuid
import json

from pandas import DataFrame as DaFe
import pandas as pd
from airflow.models.xcom import BaseXCom


def s3_hook(aws_conn_id="AWSS3LogStorage"):
    """needed to fix a bug

    ImportError: cannot import name 'S3Hook' from partially initialized module
    'airflow.providers.amazon.aws.hooks.s3'
    (most likely due to a circular import)"""
    from airflow.providers.amazon.aws.hooks.s3 import S3Hook

    return S3Hook(aws_conn_id=aws_conn_id)


class S3XComBackend(BaseXCom):
    """https://www.astronomer.io/guides/custom-xcom-backends"""

    VALUE_PREFIX = "xcom_s3://"
    BUCKET_NAME = getenv("REMOTE_BASE_LOG_BUCKET", "prod-airflows-logs")

    @staticmethod
    def serialize_value(value: Any, *args, **kwargs):
        key = f"data_{str(uuid.uuid4())}{{}}"
        filename = f"/tmp/{key}"
        key = "xcom/" + key

        if isinstance(value, pd.DataFrame):
            key = key.format(".parquet")
            value.to_parquet(filename)
            s3_hook().load_file(
                filename=filename,
                key=key,
                bucket_name=S3XComBackend.BUCKET_NAME,
                replace=True,
            )
            value = S3XComBackend.VALUE_PREFIX + key

        elif not isinstance(value, (str, list)):
            key = key.format(".json")
            with open(filename, "w") as f:
                json.dump(json.loads(str(value)), f)

            s3_hook().load_file(
                filename=filename,
                key=key,
                bucket_name=S3XComBackend.BUCKET_NAME,
                replace=True,
            )
            value = S3XComBackend.VALUE_PREFIX + key

        return BaseXCom.serialize_value(value)

    @staticmethod
    def deserialize_value(result) -> Any:
        # result i.e "xcom_s3://xcom/data_78c30142-25b0-4b3b-bd71-70a777b5bba0"
        result = BaseXCom.deserialize_value(result)
        if isinstance(result, str) and result.startswith(S3XComBackend.VALUE_PREFIX):
            key = result.replace(S3XComBackend.VALUE_PREFIX, "")
            file = s3_hook().download_file(
                key=key,
                bucket_name=S3XComBackend.BUCKET_NAME,
                local_path="/tmp",
            )
            if key.endswith(".parquet"):
                result: DaFe = pd.read_parquet(file)
            elif key.endswith(".json"):
                result: dict = json.loads(file)
            elif key.endswith(".csv"):
                result: DaFe = pd.read_csv(file)
            else:  # has s3 xcom backend prefix (was custom serialized)
                raise ValueError("unknown file format")
        return result

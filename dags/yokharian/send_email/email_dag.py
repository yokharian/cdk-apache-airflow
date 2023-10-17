"""<img alt="isolated" width="400"
src="https://www.howtogeek.com/wp-content/uploads/2019/03/gmail-1.png"/>

# SEND EMAILS PROGRAMMATICALLY
### USING AWS SES & AIRFLOWS ! 🐸

A connection with AWS SES is necessary to send emails called
'aws_email_default' [READ MORE](https://airflow.apache.org/docs/apache-airflow
/stable/howto/email-config.html).
&& [what is an AWS connection](https://airflow.apache.org/docs/apache-airflow
-providers-amazon/stable/connections/aws.html).

[How to Display Base64 Images in HTML](https://www.w3docs.com/snippets/html/
how-to-display-base64-images-in-html.html)
"""

from datetime import datetime, timedelta

from airflow.models import Param
from airflow.operators.email import EmailOperator
from airflow import DAG
from airflow.hooks.base import BaseHook

try:  # local environment
    from dags.yokharian.shareds import *
except ImportError:  # airflow environment
    # noinspection PyUnresolvedReferences
    from yokharian.shareds import *

EMAIL_CONN_ID = "awsEmailDefault"  # needed to load & run dag, read the __doc__

with DAG(
    doc_md=__doc__,
    dag_id="send_an_email",
    tags=["manual", "mail"],
    dagrun_timeout=timedelta(minutes=5),
    schedule_interval=None,
    default_args={
        **default_args,
        "email": ["sofia@escobedo.mx"],
        "owner": "sofia",
        "pool": None,
    },
    start_date=datetime(2022, 5, 24),
    # https://airflow.apache.org/docs/apache-airflow/2.3.1/concepts/params.html
    # https://json-schema.org/understanding-json-schema/reference/array.html
    params=dict(
        send_to=Param(
            default=["sofia@escobedo.mx"],
            description="who to send this email to",
            schema={
                "type": "array",
                "items": {"type": "string", "format": "idn-email"},
                "minItems": 1,
            },
        ),
        subject=Param(
            default="Test from SES",
            type="string",
            description="subject for this email",
        ),
        cc=Param(
            default=[],
            description="cc emails",
            schema={
                "type": "array",
                "items": {"type": "string", "format": "idn-email"},
            },
        ),
        bcc=Param(
            default=[],
            description="bcc emails",
            schema={
                "type": "array",
                "items": {"type": "string", "format": "idn-email"},
            },
        ),
        content=Param(
            type="string",
            default="Trying to send an email from airflow through SES.",
            description="message HTML content",
        ),
    ),
    render_template_as_native_obj=True,
    is_paused_upon_creation=False,
) as dag:
    BaseHook.get_connection(EMAIL_CONN_ID)
    EmailOperator.template_fields = "to,subject,html_content,files,cc,bcc".split(",")
    email_status = EmailOperator(
        task_id="send_email",
        conn_id=EMAIL_CONN_ID,
        # dag parameters
        to="{{ params.send_to }}",
        subject="{{ params.subject }}",
        cc="{{ params.cc }}",
        bcc="{{ params.bcc }}",
        html_content="{{ params.content }}",
        # you can send files too !
        files=None,
    )


if __name__ == "__main__":
    dag.cli()

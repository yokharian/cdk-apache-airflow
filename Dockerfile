# https://github.com/apache/airflow/blob/main/Dockerfile
# the following parameters are registered by the "apache/airflow" dockerfile
# AIRFLOW_HOME=/opt/airflow
FROM apache/airflow:2.3.1-python3.10

USER root

ARG AIRFLOW_HOME='/shared-volume/git_repo'
ARG AIRFLOW_USER_HOME_DIR='/shared-volume/git_repo'
ENV AIRFLOW_HOME='/shared-volume/git_repo'
ENV AIRFLOW_USER_HOME_DIR='/shared-volume/git_repo'

RUN apt-get update && apt-get install --no-install-recommends -y  \
    python3-pip \
    libcurl4-gnutls-dev \
    librtmp-dev \
    python3-dev \
    python3-setuptools \
    libpq-dev \
    gcc \
    build-essential \
    g++ \
    git-all \
    unixodbc-dev \
    apt-utils \
    apt-transport-https \
    debconf-utils \
    telnet

USER ${AIRFLOW_UID}
ENV PATH=${AIRFLOW_USER_HOME_DIR}/.local/bin:${PATH} \
	PYTHONPATH=${AIRFLOW_HOME}:${AIRFLOW_HOME}/dags:$PYTHONPATH \
	PIP_NO_CACHE_DIR=off \
    PIP_QUIET=1 \
	PYTHONFAULTHANDLER=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONHASHSEED=random \
	CSRF_SECRET_KEY=${CSRF_SECRET_KEY:-"HcT/ZSho1/6pAOubW/EatQ=="}
	# needed to install libraries that depends on setuptools specific version
	# VIRTUALENV_NO_SETUPTOOLS=1

COPY ./airflows/* /

RUN python3 -m pip install --upgrade pip awscli && aws --version
RUN python3 -m pip install --user -r /requirements.txt

COPY . /opt/airflow/

USER root
USER ${AIRFLOW_UID}

EXPOSE 8080
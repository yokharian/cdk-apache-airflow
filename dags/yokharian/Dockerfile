FROM public.ecr.aws/vedrai-dev/vedrai-python-builder:1.1.12-3.10

ENV PATH=$PATH:/home/user/.local/bin \
    PIP_NO_CACHE_DIR=off \
    PIP_QUIET=1 \
    PIP_USER=1 \
	LANG="C.UTF-8" \
	LC_ALL="C.UTF-8" \
	PYTHONFAULTHANDLER=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONHASHSEED=random \
	PIP_DISABLE_PIP_VERSION_CHECK=on

COPY ./default-requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

#CMD ["python","/shared-volume/git_repo/dags/yokharian/send_email/email_dag.py", '10']

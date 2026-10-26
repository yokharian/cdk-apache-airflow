FROM python:3.15.1-bookworm

RUN useradd --create-home --uid 1000 user

ENV PATH=/home/user/.local/bin:$PATH \
    PIP_NO_CACHE_DIR=off \
    PIP_QUIET=1 \
    PIP_USER=1 \
	LANG="C.UTF-8" \
	LC_ALL="C.UTF-8" \
	PYTHONFAULTHANDLER=1 \
	PYTHONUNBUFFERED=1 \
	PYTHONHASHSEED=random \
	PIP_DISABLE_PIP_VERSION_CHECK=on

USER user
WORKDIR /home/user

COPY --chown=user:user ./default-requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

#CMD ["python","/shared-volume/git_repo/dags/yokharian/send_email/email_dag.py", '10']

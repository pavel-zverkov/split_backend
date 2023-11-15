FROM python:3.11

COPY . /opt/backend
WORKDIR /opt/backend

RUN pip install --no-cache-dir --disable-pip-version-check poetry

RUN poetry config virtualenvs.create false && \
    poetry lock --check && \
    poetry install --no-cache --no-root

CMD [ "poetry", "run", "uvicorn", "src.app:app", "--reload" ]
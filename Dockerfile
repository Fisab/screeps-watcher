FROM python:3.8-slim-buster

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY watcher/ .
COPY config.yml /

CMD [ "python3", "daemon_watcher.py" ]
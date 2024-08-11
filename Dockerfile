FROM python:3.11-alpine
RUN pip3 freeze -l > requirments.txt
WORKDIR /app
COPY . .
RUN pip3 install -r requirments.txt
CMD ["python3", "-m", "modpoll","--runEnv","dockerEnvConfig.txt"]


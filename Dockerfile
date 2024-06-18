FROM python:3.11-alpine
WORKDIR /app
RUN pip3 freeze -l > requirements.txt
RUN pip3 install -r requirements.txt
RUN "ls -la"
COPY requirements.txt requirements.txt
COPY . .
CMD ["python3", "main.py", "--tcp 10.1.1.88","-f tristar.csv"]
#run cd modpoll && python3 main.py --tcp 10.1.1.88 -f tristar.csv


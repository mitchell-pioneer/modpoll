FROM python:3.11-alpine
WORKDIR /app
RUN pip3 freeze -l > requirements.txt
COPY requirements.txt requirements.txt
COPY . .
RUN pip3 install -r requirements.txt
CMD ["python3", "main.py", "--tcp","10.1.1.88","-f","tristar-test.csv"]


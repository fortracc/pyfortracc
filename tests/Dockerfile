FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir pyfortracc

WORKDIR /app/..

COPY . .

CMD ["python"]

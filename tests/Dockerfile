FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir pyfortracc

WORKDIR /app/..

COPY . .

CMD ["python"]

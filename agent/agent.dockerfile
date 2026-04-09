FROM python:3.13-slim AS builder
# Здесь происходит первичная сборка зависимостей

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential tree curl git && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

FROM builder AS runtime
# А это, если будете пересобирать без изменения зависимостей - будет быстрее намного

# Здесь копируюете нужные файлы
COPY agent ./agent
COPY storage ./storage

CMD ["python", "-m", "agent.app"]

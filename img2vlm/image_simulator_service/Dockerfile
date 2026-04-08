FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY shared ./shared
COPY integrations ./integrations
COPY image_simulator_service ./image_simulator_service

CMD ["python", "-m", "image_simulator_service.main"]

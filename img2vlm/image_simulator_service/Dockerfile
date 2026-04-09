FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Put the whole package on PYTHONPATH as `img2vlm.*`
COPY . ./img2vlm
ENV PYTHONPATH=/app

CMD ["python", "-m", "img2vlm.image_simulator_service.main"]

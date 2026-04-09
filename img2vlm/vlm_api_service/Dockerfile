FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Put the whole package on PYTHONPATH as `img2vlm.*`
COPY . ./img2vlm
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "img2vlm.vlm_api_service.main:app", "--host", "0.0.0.0", "--port", "8000"]

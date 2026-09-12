FROM python:3.11-slim

WORKDIR /app

COPY app2-behavior-baseline/backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt

COPY app2-behavior-baseline/backend /app/app2-behavior-baseline/backend
COPY shared /app/shared
WORKDIR /app/app2-behavior-baseline/backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]

FROM python:3.11-slim

WORKDIR /app

COPY app1-blast-radius/backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt

COPY app1-blast-radius/backend /app/app1-blast-radius/backend
COPY shared /app/shared
WORKDIR /app/app1-blast-radius/backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

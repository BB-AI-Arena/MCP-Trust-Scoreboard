FROM python:3.11-slim
RUN apt-get update && apt-get upgrade -y && apt-get clean

WORKDIR /app

COPY app4-mcp-scorecard/backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && pip install --no-cache-dir -r requirements.txt

COPY app4-mcp-scorecard/backend /app/app4-mcp-scorecard/backend
COPY shared /app/shared
WORKDIR /app/app4-mcp-scorecard/backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8004

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004"]

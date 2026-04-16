FROM python:3.11-slim

WORKDIR /app

# Install worker deps
COPY worker/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker
COPY worker/worker.py /app/worker.py

# Copy all app backends so worker can import their modules
COPY app1-blast-radius/backend /app/app1-blast-radius/backend
COPY app2-behavior-baseline/backend /app/app2-behavior-baseline/backend
COPY app3-code-provenance/backend /app/app3-code-provenance/backend
COPY app4-mcp-scorecard/backend /app/app4-mcp-scorecard/backend

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

CMD ["python", "worker.py"]

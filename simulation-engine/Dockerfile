FROM python:3.11-slim as builder
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH
# Note: shared utilities are mounted as volume in docker-compose
COPY src/ /app/src/
COPY config.yaml /app/
ENV PYTHONPATH=/app:$PYTHONPATH
EXPOSE 8004
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8004/health')"
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8004"]

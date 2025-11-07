# Multi-stage build for AI Manager Service
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY ai-manager-service/requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts are executable
ENV PATH=/root/.local/bin:$PATH

# Copy shared utilities first (from project root context)
COPY shared/ /app/shared/

# Copy application code
COPY ai-manager-service/src/ /app/src/
COPY ai-manager-service/config.yaml /app/

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port
EXPOSE 8005

# Run the service (as root for development)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8005"]

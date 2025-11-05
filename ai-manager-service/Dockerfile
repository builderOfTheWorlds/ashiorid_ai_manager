# Multi-stage build for AI Manager Service
FROM python:3.11-slim as builder

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Final stage
FROM python:3.11-slim

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts are executable
ENV PATH=/root/.local/bin:$PATH

# Copy application code
# Note: shared utilities are mounted as volume in docker-compose
COPY src/ /app/src/
COPY config.yaml /app/

# Set Python path
ENV PYTHONPATH=/app:$PYTHONPATH

# Expose port
EXPOSE 8005

# Run the service
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8005"]

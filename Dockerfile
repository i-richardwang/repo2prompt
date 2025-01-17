# Build stage
FROM python:3.12-slim AS builder

WORKDIR /build

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install build dependencies and Python packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc python3-dev \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --timeout 1000 -r requirements.txt \
    && rm -rf /var/lib/apt/lists/*

# Runtime stage
FROM python:3.12-slim

# Set Python environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install git, curl and clean up
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       git \
       curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user
RUN useradd -m -u 1000 appuser

# Copy Python packages and application code
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
COPY --from=builder /usr/local/bin/ /usr/local/bin/
COPY . .

# Create tmp directory and set permissions
RUN mkdir -p /app/tmp \
    && chown -R appuser:appuser /app \
    && chmod -R 755 /app \
    && chmod 777 /app/tmp

# Switch to non-root user
USER appuser

EXPOSE 8007

# Start the FastAPI application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8007", "--app-dir", "/app"]

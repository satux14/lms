# Multi-Instance Lending Management System Dockerfile
# ===================================================
# This Dockerfile creates a containerized version of the lending management system
# with support for multiple instances (prod, dev, testing)

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=run_multi.py \
    FLASK_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy and make health check script executable
COPY healthcheck.sh /usr/local/bin/healthcheck.sh
RUN chmod +x /usr/local/bin/healthcheck.sh

# Create necessary directories
RUN mkdir -p /app/backups/prod/database \
    /app/backups/prod/excel \
    /app/backups/prod/full \
    /app/backups/dev/database \
    /app/backups/dev/excel \
    /app/backups/dev/full \
    /app/backups/testing/database \
    /app/backups/testing/excel \
    /app/backups/testing/full \
    /app/instances/prod/uploads \
    /app/instances/dev/uploads \
    /app/instances/testing/uploads

# Compile translations
RUN pybabel compile -d translations -D messages && echo "✅ Translations compiled" || (echo "⚠️  Translation compilation failed, will compile at runtime" && exit 0)

# Set proper permissions
RUN chmod -R 755 /app/backups \
    && chmod -R 755 /app/instances \
    && chmod +x /app/run_multi.py

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Expose port 8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD /usr/local/bin/healthcheck.sh

# Default command
CMD ["python", "run_multi.py"]

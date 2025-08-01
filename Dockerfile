# Error Collector MCP Docker Image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r errorcolletor && useradd -r -g errorcolletor errorcolletor

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY pyproject.toml ./
RUN pip install -e .

# Copy application code
COPY . .

# Create data directory
RUN mkdir -p /data && chown errorcolletor:errorcolletor /data

# Switch to non-root user
USER errorcolletor

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["error-collector-mcp", "serve", "--config", "/app/config.json"]
# Error Collector MCP - Production Docker Image
FROM python:3.11-slim as builder

# Set build arguments
ARG BUILD_DATE
ARG VERSION
ARG VCS_REF

# Add metadata
LABEL org.opencontainers.image.title="Error Collector MCP"
LABEL org.opencontainers.image.description="Production-ready MCP server for intelligent error collection and AI analysis"
LABEL org.opencontainers.image.version="${VERSION}"
LABEL org.opencontainers.image.created="${BUILD_DATE}"
LABEL org.opencontainers.image.revision="${VCS_REF}"
LABEL org.opencontainers.image.source="https://github.com/error-collector-mcp/error-collector-mcp"
LABEL org.opencontainers.image.url="https://github.com/error-collector-mcp/error-collector-mcp"
LABEL org.opencontainers.image.documentation="https://error-collector-mcp.readthedocs.io/"
LABEL org.opencontainers.image.vendor="Error Collector MCP Team"
LABEL org.opencontainers.image.licenses="MIT"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml README.md ./
COPY error_collector_mcp/ ./error_collector_mcp/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -e . && \
    pip install --no-cache-dir gunicorn uvicorn[standard]

# Production stage
FROM python:3.11-slim as production

# Create non-root user
RUN groupadd -r errorcolletor && useradd -r -g errorcolletor errorcolletor

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    tini \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy application from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /app /app

# Copy configuration files
COPY config.production.json ./config.json
COPY config.example.json ./

# Create data directory
RUN mkdir -p /data && chown -R errorcolletor:errorcolletor /data /app

# Set environment variables
ENV PYTHONPATH=/app
ENV ERROR_COLLECTOR_DATA_DIR=/data
ENV ERROR_COLLECTOR_CONFIG=/app/config.json
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user
USER errorcolletor

# Expose port
EXPOSE 8000

# Use tini as init system
ENTRYPOINT ["/usr/bin/tini", "--"]

# Default command
CMD ["error-collector-mcp", "serve", "--config", "/app/config.json"]
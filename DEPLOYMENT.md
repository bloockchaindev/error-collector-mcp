# Production Deployment Guide

This guide covers deploying Error Collector MCP in production environments with
best practices for security, performance, and reliability.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Deployment Methods](#deployment-methods)
- [Configuration](#configuration)
- [Security](#security)
- [Monitoring](#monitoring)
- [Maintenance](#maintenance)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows
  Server
- **Python**: 3.9 or higher
- **Memory**: Minimum 512MB RAM, recommended 2GB+
- **Storage**: Minimum 1GB free space, recommended 10GB+ for error data
- **Network**: Outbound HTTPS access to OpenRouter API

### Dependencies

- **OpenRouter API Key**: Required for AI summarization
- **Docker** (optional): For containerized deployment
- **Reverse Proxy** (recommended): nginx, Apache, or similar
- **Process Manager** (recommended): systemd, supervisor, or PM2

## Environment Setup

### 1. Create Dedicated User

```bash
# Create system user for the service
sudo useradd -r -s /bin/false -d /opt/error-collector-mcp error-collector

# Create directories
sudo mkdir -p /opt/error-collector-mcp
sudo mkdir -p /var/lib/error-collector-mcp
sudo mkdir -p /var/log/error-collector-mcp

# Set ownership
sudo chown -R error-collector:error-collector /opt/error-collector-mcp
sudo chown -R error-collector:error-collector /var/lib/error-collector-mcp
sudo chown -R error-collector:error-collector /var/log/error-collector-mcp
```

### 2. Install Application

```bash
# Switch to application directory
cd /opt/error-collector-mcp

# Create virtual environment
sudo -u error-collector python3 -m venv venv

# Install application
sudo -u error-collector ./venv/bin/pip install error-collector-mcp

# Or install from source
sudo -u error-collector git clone https://github.com/error-collector-mcp/error-collector-mcp.git .
sudo -u error-collector ./venv/bin/pip install -e .
```

### 3. Environment Variables

Create `/etc/environment.d/error-collector-mcp.conf`:

```bash
# OpenRouter API Configuration
OPENROUTER_API_KEY=your-api-key-here

# Application Configuration
ERROR_COLLECTOR_CONFIG=/opt/error-collector-mcp/config.production.json
ERROR_COLLECTOR_DATA_DIR=/var/lib/error-collector-mcp

# Security
PYTHONHASHSEED=random
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

## Deployment Methods

### Method 1: Systemd Service (Recommended)

Create `/etc/systemd/system/error-collector-mcp.service`:

```ini
[Unit]
Description=Error Collector MCP Server
Documentation=https://error-collector-mcp.readthedocs.io/
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=exec
User=error-collector
Group=error-collector
WorkingDirectory=/opt/error-collector-mcp
Environment=PYTHONPATH=/opt/error-collector-mcp
EnvironmentFile=/etc/environment.d/error-collector-mcp.conf

ExecStart=/opt/error-collector-mcp/venv/bin/error-collector-mcp serve
ExecReload=/bin/kill -HUP $MAINPID

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/error-collector-mcp /var/log/error-collector-mcp

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

# Restart policy
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=error-collector-mcp

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable error-collector-mcp
sudo systemctl start error-collector-mcp
sudo systemctl status error-collector-mcp
```

### Method 2: Docker Deployment

#### Using Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/error-collector-mcp/error-collector-mcp.git
cd error-collector-mcp

# Set environment variables
export OPENROUTER_API_KEY=your-api-key-here

# Deploy with Docker Compose
docker-compose up -d

# Check status
docker-compose ps
docker-compose logs -f error-collector-mcp
```

#### Using Docker directly

```bash
# Pull image
docker pull ghcr.io/error-collector-mcp/error-collector-mcp:latest

# Run container
docker run -d \
  --name error-collector-mcp \
  --restart unless-stopped \
  -p 8000:8000 \
  -e OPENROUTER_API_KEY=your-api-key-here \
  -v error-collector-data:/data \
  ghcr.io/error-collector-mcp/error-collector-mcp:latest
```

### Method 3: Kubernetes Deployment

Create `k8s-deployment.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
    name: error-collector-mcp
---
apiVersion: v1
kind: Secret
metadata:
    name: error-collector-secrets
    namespace: error-collector-mcp
type: Opaque
stringData:
    openrouter-api-key: "your-api-key-here"
---
apiVersion: v1
kind: ConfigMap
metadata:
    name: error-collector-config
    namespace: error-collector-mcp
data:
    config.json: |
        {
          "openrouter": {
            "api_key": "${OPENROUTER_API_KEY}",
            "model": "qwen/qwen-2.5-coder-32b-instruct:free"
          },
          "storage": {
            "data_directory": "/data",
            "retention_days": 90
          },
          "server": {
            "host": "0.0.0.0",
            "port": 8000
          }
        }
---
apiVersion: apps/v1
kind: Deployment
metadata:
    name: error-collector-mcp
    namespace: error-collector-mcp
spec:
    replicas: 2
    selector:
        matchLabels:
            app: error-collector-mcp
    template:
        metadata:
            labels:
                app: error-collector-mcp
        spec:
            containers:
                - name: error-collector-mcp
                  image: ghcr.io/error-collector-mcp/error-collector-mcp:latest
                  ports:
                      - containerPort: 8000
                  env:
                      - name: OPENROUTER_API_KEY
                        valueFrom:
                            secretKeyRef:
                                name: error-collector-secrets
                                key: openrouter-api-key
                      - name: ERROR_COLLECTOR_CONFIG
                        value: "/config/config.json"
                      - name: ERROR_COLLECTOR_DATA_DIR
                        value: "/data"
                  volumeMounts:
                      - name: config
                        mountPath: /config
                      - name: data
                        mountPath: /data
                  livenessProbe:
                      httpGet:
                          path: /health
                          port: 8000
                      initialDelaySeconds: 30
                      periodSeconds: 10
                  readinessProbe:
                      httpGet:
                          path: /health
                          port: 8000
                      initialDelaySeconds: 5
                      periodSeconds: 5
                  resources:
                      requests:
                          memory: "256Mi"
                          cpu: "100m"
                      limits:
                          memory: "1Gi"
                          cpu: "500m"
            volumes:
                - name: config
                  configMap:
                      name: error-collector-config
                - name: data
                  persistentVolumeClaim:
                      claimName: error-collector-data
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
    name: error-collector-data
    namespace: error-collector-mcp
spec:
    accessModes:
        - ReadWriteOnce
    resources:
        requests:
            storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
    name: error-collector-mcp
    namespace: error-collector-mcp
spec:
    selector:
        app: error-collector-mcp
    ports:
        - port: 8000
          targetPort: 8000
    type: ClusterIP
```

Deploy to Kubernetes:

```bash
kubectl apply -f k8s-deployment.yaml
kubectl get pods -n error-collector-mcp
kubectl logs -f deployment/error-collector-mcp -n error-collector-mcp
```

## Configuration

### Production Configuration

Use the provided `config.production.json` as a starting point:

```json
{
    "openrouter": {
        "api_key": "${OPENROUTER_API_KEY}",
        "model": "qwen/qwen-2.5-coder-32b-instruct:free",
        "max_tokens": 2000,
        "temperature": 0.3,
        "timeout": 45,
        "max_retries": 5
    },
    "collection": {
        "enabled_sources": ["browser", "terminal"],
        "max_errors_per_minute": 500,
        "auto_summarize": true,
        "group_similar_errors": true,
        "similarity_threshold": 0.85
    },
    "storage": {
        "data_directory": "/var/lib/error-collector-mcp",
        "max_errors_stored": 100000,
        "retention_days": 90,
        "backup_enabled": true
    },
    "server": {
        "host": "0.0.0.0",
        "port": 8000,
        "log_level": "INFO",
        "enable_cors": true,
        "max_concurrent_requests": 50
    }
}
```

### Environment-Specific Overrides

Create environment-specific configurations:

- `config.staging.json` - Staging environment
- `config.production.json` - Production environment
- `config.development.json` - Development environment

## Security

### 1. API Key Management

**Never commit API keys to version control!**

```bash
# Use environment variables
export OPENROUTER_API_KEY="your-key-here"

# Or use a secrets management system
# AWS Secrets Manager, HashiCorp Vault, etc.
```

### 2. Network Security

```bash
# Configure firewall (UFW example)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # Application port
sudo ufw enable

# Or use iptables
sudo iptables -A INPUT -p tcp --dport 8000 -j ACCEPT
```

### 3. Reverse Proxy (nginx)

Create `/etc/nginx/sites-available/error-collector-mcp`:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /path/to/ssl/cert.pem;
    ssl_certificate_key /path/to/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
        access_log off;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/error-collector-mcp /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 4. SSL/TLS Certificate

```bash
# Using Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

## Monitoring

### 1. Health Checks

```bash
# Basic health check
curl -f http://localhost:8000/health

# Detailed status via MCP
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "get_server_status", "arguments": {}}}'
```

### 2. Log Monitoring

```bash
# View logs
sudo journalctl -u error-collector-mcp -f

# Log rotation
sudo logrotate -d /etc/logrotate.d/error-collector-mcp
```

### 3. Metrics Collection

Create `/etc/prometheus/prometheus.yml`:

```yaml
global:
    scrape_interval: 15s

scrape_configs:
    - job_name: "error-collector-mcp"
      static_configs:
          - targets: ["localhost:8000"]
      metrics_path: /metrics
      scrape_interval: 30s
```

### 4. Alerting

Create alerting rules for:

- Service availability
- High error rates
- API quota exhaustion
- Storage space usage
- Memory/CPU usage

## Maintenance

### 1. Updates

```bash
# Update application
sudo -u error-collector ./venv/bin/pip install --upgrade error-collector-mcp

# Restart service
sudo systemctl restart error-collector-mcp

# Verify update
sudo systemctl status error-collector-mcp
```

### 2. Backup

```bash
# Backup data directory
sudo tar -czf /backup/error-collector-$(date +%Y%m%d).tar.gz \
  /var/lib/error-collector-mcp

# Backup configuration
sudo cp /opt/error-collector-mcp/config.production.json \
  /backup/config-$(date +%Y%m%d).json
```

### 3. Log Rotation

Create `/etc/logrotate.d/error-collector-mcp`:

```
/var/log/error-collector-mcp/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 error-collector error-collector
    postrotate
        systemctl reload error-collector-mcp
    endscript
}
```

### 4. Data Cleanup

```bash
# Manual cleanup (if needed)
sudo -u error-collector /opt/error-collector-mcp/venv/bin/error-collector-mcp cleanup --older-than 90d

# Automated cleanup via cron
echo "0 2 * * 0 error-collector /opt/error-collector-mcp/venv/bin/error-collector-mcp cleanup --older-than 90d" | sudo tee -a /etc/crontab
```

## Troubleshooting

### Common Issues

#### 1. Service Won't Start

```bash
# Check service status
sudo systemctl status error-collector-mcp

# Check logs
sudo journalctl -u error-collector-mcp -n 50

# Check configuration
sudo -u error-collector /opt/error-collector-mcp/venv/bin/error-collector-mcp --config /opt/error-collector-mcp/config.production.json --validate
```

#### 2. High Memory Usage

```bash
# Check memory usage
ps aux | grep error-collector-mcp

# Adjust configuration
# Reduce max_errors_stored in config.json
# Reduce retention_days
# Enable more aggressive cleanup
```

#### 3. API Rate Limiting

```bash
# Check API usage
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {"name": "get_error_statistics", "arguments": {}}}'

# Adjust rate limiting in config.json
# Consider upgrading to paid OpenRouter plan
```

#### 4. Storage Issues

```bash
# Check disk space
df -h /var/lib/error-collector-mcp

# Check data directory permissions
ls -la /var/lib/error-collector-mcp

# Manual cleanup if needed
sudo -u error-collector find /var/lib/error-collector-mcp -name "*.json" -mtime +90 -delete
```

### Performance Tuning

#### 1. System Limits

```bash
# Increase file descriptor limits
echo "error-collector soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "error-collector hard nofile 65536" | sudo tee -a /etc/security/limits.conf
```

#### 2. Application Tuning

```json
{
    "collection": {
        "max_errors_per_minute": 1000
    },
    "server": {
        "max_concurrent_requests": 100
    },
    "storage": {
        "max_errors_stored": 500000
    }
}
```

### Support

For production support:

- **Documentation**: https://error-collector-mcp.readthedocs.io/
- **Issues**: https://github.com/error-collector-mcp/error-collector-mcp/issues
- **Security**: security@error-collector-mcp.org
- **Commercial Support**: Available for enterprise deployments

---

**Last Updated**: February 2025\
**Version**: 1.0.0

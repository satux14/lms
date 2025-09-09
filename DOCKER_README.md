# Docker Deployment Guide
# =======================

This guide explains how to deploy the Multi-Instance Lending Management System using Docker.

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository** (if not already done):
   ```bash
   git clone <repository-url>
   cd lending_app
   ```

2. **Start the application**:
   ```bash
   docker-compose up -d
   ```

3. **Access the application**:
   - Instance Selector: http://localhost:8080/
   - Production: http://localhost:8080/prod/
   - Development: http://localhost:8080/dev/
   - Testing: http://localhost:8080/testing/

4. **Stop the application**:
   ```bash
   docker-compose down
   ```

### Using Docker directly

1. **Build the image**:
   ```bash
   docker build -t lending-app .
   ```

2. **Run the container**:
   ```bash
   docker run -d \
     --name lending-management-system \
     -p 8080:8080 \
     -v lending_data:/app/instances \
     -v lending_backups:/app/backups \
     -v lending_uploads:/app/uploads \
     lending-app
   ```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `FLASK_ENV` | `production` | Flask environment |
| `PYTHONUNBUFFERED` | `1` | Python output buffering |

### Port Configuration

- **External Port**: 8080 (configurable in docker-compose.yml)
- **Internal Port**: 8080 (fixed in application)

To change the external port, modify the `ports` section in `docker-compose.yml`:
```yaml
ports:
  - "YOUR_PORT:8080"  # Replace YOUR_PORT with desired port
```

## Data Persistence

The application uses Docker volumes to persist data:

- **`lending_data`**: Database files for all instances
- **`lending_backups`**: Backup files and exports
- **`lending_uploads`**: User-uploaded files (payment proofs)

### Backup and Restore

**Backup data**:
```bash
# Create a backup of all volumes
docker run --rm -v lending_data:/data -v $(pwd):/backup alpine tar czf /backup/lending_data_backup.tar.gz -C /data .
docker run --rm -v lending_backups:/data -v $(pwd):/backup alpine tar czf /backup/lending_backups_backup.tar.gz -C /data .
docker run --rm -v lending_uploads:/data -v $(pwd):/backup alpine tar czf /backup/lending_uploads_backup.tar.gz -C /data .
```

**Restore data**:
```bash
# Restore volumes from backup
docker run --rm -v lending_data:/data -v $(pwd):/backup alpine tar xzf /backup/lending_data_backup.tar.gz -C /data
docker run --rm -v lending_backups:/data -v $(pwd):/backup alpine tar xzf /backup/lending_backups_backup.tar.gz -C /data
docker run --rm -v lending_uploads:/data -v $(pwd):/backup alpine tar xzf /backup/lending_uploads_backup.tar.gz -C /data
```

## Development

### Building for Development

```bash
# Build with development settings
docker build -t lending-app:dev --build-arg FLASK_ENV=development .

# Run in development mode
docker run -d \
  --name lending-dev \
  -p 8080:8080 \
  -v $(pwd):/app \
  -e FLASK_ENV=development \
  lending-app:dev
```

### Debugging

**View logs**:
```bash
docker-compose logs -f lending-app
```

**Access container shell**:
```bash
docker exec -it lending-management-system /bin/bash
```

**Check container health**:
```bash
docker ps  # Check if container is running
docker inspect lending-management-system  # Detailed container info
```

## Production Deployment

### Security Considerations

1. **Change default passwords** after first login
2. **Use environment variables** for sensitive configuration
3. **Enable HTTPS** in production (use reverse proxy like nginx)
4. **Regular backups** of Docker volumes
5. **Monitor logs** for security issues

### Reverse Proxy Setup (Nginx)

Example nginx configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/HTTPS Setup

Use Let's Encrypt with nginx for free SSL certificates:

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d your-domain.com
```

## Troubleshooting

### Common Issues

1. **Port already in use**:
   ```bash
   # Check what's using port 8080
   sudo netstat -tulpn | grep :8080
   
   # Kill the process or change port in docker-compose.yml
   ```

2. **Permission denied**:
   ```bash
   # Fix volume permissions
   sudo chown -R 1000:1000 ./data
   ```

3. **Container won't start**:
   ```bash
   # Check logs
   docker logs lending-management-system
   
   # Check if all required files are present
   docker run --rm -it lending-app ls -la /app
   ```

4. **Database issues**:
   ```bash
   # Access container and check database
   docker exec -it lending-management-system /bin/bash
   ls -la /app/instances/*/database/
   ```

### Health Checks

The application includes health checks that verify the web server is responding:

```bash
# Manual health check
curl -f http://localhost:8080/

# Check health status
docker inspect --format='{{.State.Health.Status}}' lending-management-system
```

## Maintenance

### Updates

1. **Pull latest changes**:
   ```bash
   git pull origin main
   ```

2. **Rebuild and restart**:
   ```bash
   docker-compose down
   docker-compose build --no-cache
   docker-compose up -d
   ```

### Monitoring

**Resource usage**:
```bash
docker stats lending-management-system
```

**Disk usage**:
```bash
docker system df
```

**Clean up unused resources**:
```bash
docker system prune -a
```

## Support

For issues and questions:
1. Check the logs: `docker-compose logs -f`
2. Verify configuration: `docker-compose config`
3. Check container health: `docker ps`
4. Review this documentation

## Version Information

- **Application Version**: 2.0
- **Docker Base Image**: python:3.12-slim
- **Flask Version**: 2.3.3
- **Python Version**: 3.12

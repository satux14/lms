# Docker Setup Guide

This project uses separate Docker Compose files for production and development environments.

## Files

- **`docker-compose.dev.yml`** - Development environment (port 9090)
- **`docker-compose.prod.yml`** - Production environment (port 8080)
- **`docker-compose.yml`** - Base configuration (references)

## Development Environment (lms-dev)

Since this is the `lms-dev` directory, use the development compose file:

### Start Development Environment

```bash
docker compose -f docker-compose.dev.yml up -d --build
```

### Stop Development Environment

```bash
docker compose -f docker-compose.dev.yml down
```

### View Logs

```bash
docker compose -f docker-compose.dev.yml logs -f
```

### Access Development Environment

- Instance Selector: http://localhost:9090/
- Production Instance: http://localhost:9090/prod/
- Development Instance: http://localhost:9090/dev/
- Testing Instance: http://localhost:9090/testing/

## Production Environment

The `docker-compose.prod.yml` file is intended for production deployments (typically on a production server or different location).

### Start Production Environment

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

### Access Production Environment

- Instance Selector: http://localhost:8080/
- Production Instance: http://localhost:8080/prod/
- Development Instance: http://localhost:8080/dev/
- Testing Instance: http://localhost:8080/testing/

## Replicating Production Data to Development

To copy production data into your development environment:

```bash
# Set production paths if different (defaults assume ../lms/)
export PROD_DATA_DIR=/path/to/production/instances
export PROD_BACKUPS_DIR=/path/to/production/backups

# Run replication script
./scripts/replicate_prod_to_dev.sh
```

This script will:
1. Stop the development container
2. Copy directories from production to development using rsync (or cp)
3. Restart the development container

**Note:** The script assumes production is in `../lms/` by default. Adjust `PROD_*` environment variables if production is in a different location.

## Volume Mounts (Host Directories)

All volumes are mounted from the host filesystem for easy access and backup.

### Directory Structure

All instance data is now consolidated in the **`instances/`** directory:

1. **`instances/`** (plural) - Contains all instance data
   - `instances/prod/database/` - Production databases
   - `instances/prod/uploads/` - Production file uploads
   - `instances/prod/daily-trackers/` - Production tracker Excel files
   - `instances/dev/database/` - Development databases
   - `instances/dev/uploads/` - Development file uploads
   - `instances/dev/daily-trackers/` - Development tracker Excel files
   - `instances/testing/database/` - Testing databases
   - `instances/testing/uploads/` - Testing file uploads
   - `instances/testing/daily-trackers/` - Testing tracker Excel files

2. **`backups/`** - Contains backup files
   - `backups/prod/` - Production backups
   - `backups/dev/` - Development backups
   - `backups/testing/` - Testing backups

### Configurable Paths

You can override default paths using environment variables:

```bash
# Development
export DATA_DIR=/custom/path/instances
export BACKUPS_DIR=/custom/path/backups
docker compose -f docker-compose.dev.yml up -d

# Production
export DATA_DIR=/custom/path/instances
export BACKUPS_DIR=/custom/path/backups
docker compose -f docker-compose.prod.yml up -d
```

## Default Credentials

All instances start with:
- **Username:** `admin`
- **Password:** `admin123`

## Troubleshooting

### Check Container Status

```bash
docker compose -f docker-compose.dev.yml ps
```

### Rebuild Containers

```bash
docker compose -f docker-compose.dev.yml up -d --build --force-recreate
```

### View Volume Information

```bash
docker volume ls | grep lms-dev
```

### Remove Development Container (⚠️ Data Preserved)

```bash
docker compose -f docker-compose.dev.yml down
```

**Note:** Since volumes are mounted from host directories, data persists even after removing the container. To delete data, manually remove the directories:

```bash
# ⚠️ DESTRUCTIVE - Removes all development data
rm -rf ./instances ./instance ./backups
```


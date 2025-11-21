# Production Docker Commands

## Start Production Environment

```bash
cd /Users/rsk/Documents/GitHub/lms-dev
docker compose -f docker-compose.prod.yml up -d --build
```

**Note:** The `--build` flag rebuilds the image before starting, ensuring latest code changes are included.

## Rebuild and Start (Alternative Methods)

**Method 1: Rebuild and start in one command**
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

**Method 2: Rebuild separately, then start**
```bash
# Rebuild the image
docker compose -f docker-compose.prod.yml build

# Start the container
docker compose -f docker-compose.prod.yml up -d
```

**Method 3: Force rebuild without cache**
```bash
docker compose -f docker-compose.prod.yml build --no-cache
docker compose -f docker-compose.prod.yml up -d
```

## Stop Production Environment

```bash
cd /Users/rsk/Documents/GitHub/lms-dev
docker compose -f docker-compose.prod.yml down
```

## View Logs

```bash
docker compose -f docker-compose.prod.yml logs -f
```

## Check Container Status

```bash
docker compose -f docker-compose.prod.yml ps
```

## Restart Production

```bash
docker compose -f docker-compose.prod.yml restart
```

## Access Production

- Instance Selector: http://localhost:8080/
- Production Instance: http://localhost:8080/prod/
- Development Instance: http://localhost:8080/dev/
- Testing Instance: http://localhost:8080/testing/

## Safety Confirmation

✅ **Your production database is SAFE** because:
- Volumes are **host-mounted** (bind mounts), not Docker volumes
- Database location: `./instances/prod/database/lending_app_prod.db`
- Container reads/writes directly to your existing database file
- No data will be lost or overwritten

The docker-compose.prod.yml mounts:
- `./instances` → `/app/instances` (contains your production database)
- `./backups` → `/app/backups` (backup files)
- `./daily-trackers/template` → `/app/daily-trackers/template` (read-only)


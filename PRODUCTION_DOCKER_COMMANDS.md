# Production Docker Commands

## Start Production Environment

```bash
cd /Users/rsk/Documents/GitHub/lms
docker compose -f docker-compose.prod.yml up -d --build
```

## Stop Production Environment

```bash
cd /Users/rsk/Documents/GitHub/lms
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


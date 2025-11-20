#!/bin/bash
set -euo pipefail

# Safe script to start production Docker containers
# This script verifies the setup before starting containers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "🔍 Verifying Production Docker Setup..."
echo ""

# Check if production database exists
PROD_DB="${PROJECT_ROOT}/instances/prod/database/lending_app_prod.db"
if [ -f "${PROD_DB}" ]; then
    DB_SIZE=$(ls -lh "${PROD_DB}" | awk '{print $5}')
    echo "✅ Production database found: ${PROD_DB} (${DB_SIZE})"
else
    echo "⚠️  Warning: Production database not found at ${PROD_DB}"
    echo "   A new database will be created on first run."
fi

# Check docker-compose file
if [ ! -f "docker-compose.prod.yml" ]; then
    echo "❌ Error: docker-compose.prod.yml not found!"
    exit 1
fi

echo "✅ docker-compose.prod.yml found"

# Verify volumes are host-mounted (not Docker volumes)
echo ""
echo "📦 Verifying volume mounts..."
docker compose -f docker-compose.prod.yml config 2>/dev/null | grep -q "type: bind" && \
    echo "✅ Volumes are host-mounted (safe - uses existing data)" || \
    echo "⚠️  Warning: Volumes may not be host-mounted"

# Check if container is already running
if docker ps --format '{{.Names}}' | grep -q "lending-management-system-prod"; then
    echo ""
    echo "⚠️  Production container is already running!"
    echo "   Use: docker compose -f docker-compose.prod.yml restart"
    exit 0
fi

echo ""
echo "🚀 Starting production containers..."
echo ""
docker compose -f docker-compose.prod.yml up -d --build

echo ""
echo "✅ Production containers started!"
echo ""
echo "📋 Container Status:"
docker compose -f docker-compose.prod.yml ps

echo ""
echo "🌐 Access Production Environment:"
echo "   Instance Selector: http://localhost:8080/"
echo "   Production Instance: http://localhost:8080/prod/"
echo ""
echo "📊 View Logs:"
echo "   docker compose -f docker-compose.prod.yml logs -f"
echo ""
echo "🛑 Stop Containers:"
echo "   docker compose -f docker-compose.prod.yml down"


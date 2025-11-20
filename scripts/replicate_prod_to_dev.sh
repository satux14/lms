#!/bin/bash
set -euo pipefail

# Replicate production data to development environment
# This script copies data from production host directories to development directories
# 
# Usage:
#   ./scripts/replicate_prod_to_dev.sh
# 
# Environment variables:
#   PROD_DATA_DIR - Production instances directory (default: ../lms/instances)
#   PROD_BACKUPS_DIR - Production backups directory (default: ../lms/backups)
#   DEV_DATA_DIR - Development instances directory (default: ./instances)
#   DEV_BACKUPS_DIR - Development backups directory (default: ./backups)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
cd "${PROJECT_ROOT}"

# Production paths (adjust if production is in a different location)
PROD_DATA_DIR="${PROD_DATA_DIR:-../lms/instances}"
PROD_BACKUPS_DIR="${PROD_BACKUPS_DIR:-../lms/backups}"

# Development paths
DEV_DATA_DIR="${DEV_DATA_DIR:-./instances}"
DEV_BACKUPS_DIR="${DEV_BACKUPS_DIR:-./backups}"

copy_directory() {
  local source_dir="$1"
  local dest_dir="$2"
  local description="$3"

  echo "⏳ Copying ${description}..."
  echo "   From: ${source_dir}"
  echo "   To:   ${dest_dir}"

  if [ ! -d "${source_dir}" ]; then
    echo "⚠️  Warning: Source directory ${source_dir} not found. Skipping..."
    return 0
  fi

  # Create destination directory if it doesn't exist
  mkdir -p "${dest_dir}"

  # Copy with rsync if available, otherwise use cp
  if command -v rsync >/dev/null 2>&1; then
    rsync -av --delete "${source_dir}/" "${dest_dir}/"
  else
    rm -rf "${dest_dir}"/*
    cp -a "${source_dir}/." "${dest_dir}/"
  fi

  echo "✅ ${description} copied successfully"
}

echo "🔧 Stopping development container (if running)…"
docker compose -f docker-compose.dev.yml stop >/dev/null 2>&1 || true

echo ""
echo "📦 Copying data from production to development…"
echo "   Production source: ${PROD_DATA_DIR}"
echo "   Development destination: ${DEV_DATA_DIR}"
echo ""

# Copy instances directory (contains databases, uploads, daily-trackers)
copy_directory "${PROD_DATA_DIR}" "${DEV_DATA_DIR}" "Instances directory (databases, uploads, daily-trackers)"

# Copy backups directory
copy_directory "${PROD_BACKUPS_DIR}" "${DEV_BACKUPS_DIR}" "Backups directory"

echo ""
echo "🚀 Restarting development container…"
docker compose -f docker-compose.dev.yml up -d

echo ""
echo "✅ Replication complete!"
echo "   Development environment is now available at: http://localhost:9090"
echo "   Data copied from: ${PROD_DATA_DIR}"


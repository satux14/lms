#!/bin/bash
# Health check script for Docker container
# ========================================

# Check if the application is responding
curl -f http://localhost:8080/ > /dev/null 2>&1

# Return the exit code from curl
exit $?

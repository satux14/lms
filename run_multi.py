#!/usr/bin/env python3
"""
Run script for Multi-Instance Lending Management System
====================================================

This script starts the multi-instance application with all three instances:
- Production (prod)
- Development (dev) 
- Testing (testing)

Usage:
    python3 run_multi.py

URLs:
    http://localhost:8080/ - Instance selector
    http://localhost:8080/prod/ - Production instance
    http://localhost:8080/dev/ - Development instance
    http://localhost:8080/testing/ - Testing instance
"""

from app_multi import app

if __name__ == '__main__':
    print("🏦 Starting Multi-Instance Lending Management System")
    print("=" * 60)
    print("📋 Available Instances:")
    print("   • Production:  http://localhost:8080/prod/")
    print("   • Development: http://localhost:8080/dev/")
    print("   • Testing:     http://localhost:8080/testing/")
    print("   • Instance Selector: http://localhost:8080/")
    print("=" * 60)
    print("🚀 Starting server on http://localhost:8080")
    print("Press Ctrl+C to stop the server")
    print()
    
    app.run(debug=True, port=8080, host='0.0.0.0')

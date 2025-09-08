#!/usr/bin/env python3
"""
Lending Management System - Startup Script
Run this script to start the lending management application.
"""

import os
import sys
from app import app, db

def main():
    """Main function to start the application"""
    print("=" * 60)
    print("🏦 LENDING MANAGEMENT SYSTEM")
    print("=" * 60)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('app.py'):
        print("❌ Error: app.py not found!")
        print("Please run this script from the lending_app directory.")
        sys.exit(1)
    
    # Create database tables
    print("📊 Initializing database...")
    with app.app_context():
        db.create_all()
        print("✅ Database initialized successfully")
    
    print()
    print("🚀 Starting the application...")
    print("📍 Application will be available at: http://localhost:8080")
    print()
    print("👤 Default Admin Login:")
    print("   Username: admin")
    print("   Password: admin123")
    print()
    print("💡 Tips:")
    print("   - Register new customer accounts from the homepage")
    print("   - Admins can create loans and manage interest rates")
    print("   - Customers can make payments and track their loans")
    print()
    print("🛑 Press Ctrl+C to stop the application")
    print("=" * 60)
    print()
    
    # Start the Flask application
    try:
        app.run(debug=True, host='0.0.0.0', port=8080)
    except KeyboardInterrupt:
        print("\n👋 Application stopped by user")
    except Exception as e:
        print(f"\n❌ Error starting application: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

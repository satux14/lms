#!/usr/bin/env python3
"""
Version Manager for Lending Management System
Helps create version tags and manage releases
"""

import subprocess
import sys
import re
from datetime import datetime

def run_command(command):
    """Run a shell command and return the output"""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def get_current_version():
    """Get the current version tag"""
    stdout, stderr, code = run_command("git describe --tags --abbrev=0")
    if code == 0 and stdout:
        return stdout
    return "v0.0.0"

def get_next_version(current_version, version_type):
    """Calculate the next version number"""
    # Remove 'v' prefix and split version
    version = current_version.lstrip('v')
    parts = version.split('.')
    
    if len(parts) != 3:
        return "v1.0.0"
    
    major, minor, patch = map(int, parts)
    
    if version_type == "major":
        return f"v{major + 1}.0.0"
    elif version_type == "minor":
        return f"v{major}.{minor + 1}.0"
    elif version_type == "patch":
        return f"v{major}.{minor}.{patch + 1}"
    else:
        return f"v{major}.{minor}.{patch + 1}"

def create_version_tag(version, message):
    """Create a new version tag"""
    tag_message = f"{version} - {message}\n\nCreated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    # Create the tag
    stdout, stderr, code = run_command(f'git tag -a {version} -m "{tag_message}"')
    
    if code == 0:
        print(f"✅ Created tag: {version}")
        print(f"📝 Message: {message}")
        return True
    else:
        print(f"❌ Error creating tag: {stderr}")
        return False

def show_version_info():
    """Show current version information"""
    current_version = get_current_version()
    stdout, stderr, code = run_command("git log --oneline -5")
    
    print("🏦 Lending Management System - Version Info")
    print("=" * 50)
    print(f"📌 Current Version: {current_version}")
    print(f"📅 Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n📋 Recent Commits:")
    if code == 0:
        for line in stdout.split('\n'):
            if line:
                print(f"   {line}")
    print("\n🏷️  Available Tags:")
    stdout, stderr, code = run_command("git tag -l")
    if code == 0 and stdout:
        for tag in sorted(stdout.split('\n')):
            if tag:
                print(f"   {tag}")

def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("🏦 Lending Management System - Version Manager")
        print("=" * 50)
        print("Usage:")
        print("  python3 version_manager.py info                    # Show version info")
        print("  python3 version_manager.py patch <message>         # Create patch version (1.0.0 -> 1.0.1)")
        print("  python3 version_manager.py minor <message>         # Create minor version (1.0.0 -> 1.1.0)")
        print("  python3 version_manager.py major <message>         # Create major version (1.0.0 -> 2.0.0)")
        print("  python3 version_manager.py custom <version> <message>  # Create custom version")
        print("\nExamples:")
        print("  python3 version_manager.py patch 'Fixed interest calculation bug'")
        print("  python3 version_manager.py minor 'Added new filtering features'")
        print("  python3 version_manager.py major 'Complete UI redesign'")
        return
    
    command = sys.argv[1].lower()
    
    if command == "info":
        show_version_info()
        return
    
    if command in ["patch", "minor", "major"]:
        if len(sys.argv) < 3:
            print("❌ Error: Please provide a message for the version")
            print("Example: python3 version_manager.py patch 'Fixed bug in payment processing'")
            return
        
        message = " ".join(sys.argv[2:])
        current_version = get_current_version()
        next_version = get_next_version(current_version, command)
        
        print(f"📌 Current Version: {current_version}")
        print(f"🆕 Next Version: {next_version}")
        print(f"📝 Message: {message}")
        
        confirm = input("\n🤔 Create this version tag? (y/N): ").lower()
        if confirm in ['y', 'yes']:
            if create_version_tag(next_version, message):
                print(f"\n🎉 Successfully created version {next_version}")
                print("💡 To push to remote repository, run: git push origin --tags")
            else:
                print(f"\n❌ Failed to create version {next_version}")
        else:
            print("❌ Version creation cancelled")
    
    elif command == "custom":
        if len(sys.argv) < 4:
            print("❌ Error: Please provide version and message")
            print("Example: python3 version_manager.py custom v1.5.0 'Special release'")
            return
        
        version = sys.argv[2]
        message = " ".join(sys.argv[3:])
        
        # Validate version format
        if not re.match(r'^v?\d+\.\d+\.\d+$', version):
            print("❌ Error: Version must be in format v1.0.0 or 1.0.0")
            return
        
        if not version.startswith('v'):
            version = f"v{version}"
        
        print(f"🆕 Custom Version: {version}")
        print(f"📝 Message: {message}")
        
        confirm = input("\n🤔 Create this version tag? (y/N): ").lower()
        if confirm in ['y', 'yes']:
            if create_version_tag(version, message):
                print(f"\n🎉 Successfully created version {version}")
                print("💡 To push to remote repository, run: git push origin --tags")
            else:
                print(f"\n❌ Failed to create version {version}")
        else:
            print("❌ Version creation cancelled")
    
    else:
        print(f"❌ Unknown command: {command}")
        print("Run 'python3 version_manager.py' for usage information")

if __name__ == "__main__":
    main()

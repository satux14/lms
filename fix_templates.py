#!/usr/bin/env python3
"""
Fix template URLs to include instance_name parameter
"""

import os
import re
from pathlib import Path

def fix_template_urls(file_path):
    """Fix URL patterns in a template file"""
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Fix admin routes
    patterns = [
        (r"url_for\('admin_dashboard'\)", "url_for('admin_dashboard', instance_name=instance_name)"),
        (r"url_for\('admin_loans'\)", "url_for('admin_loans', instance_name=instance_name)"),
        (r"url_for\('admin_payments'\)", "url_for('admin_payments', instance_name=instance_name)"),
        (r"url_for\('admin_users'\)", "url_for('admin_users', instance_name=instance_name)"),
        (r"url_for\('admin_create_loan'\)", "url_for('admin_create_loan', instance_name=instance_name)"),
        (r"url_for\('admin_create_user'\)", "url_for('admin_create_user', instance_name=instance_name)"),
        (r"url_for\('admin_add_payment'\)", "url_for('admin_add_payment', instance_name=instance_name)"),
        (r"url_for\('admin_edit_payment'\)", "url_for('admin_edit_payment', instance_name=instance_name)"),
        (r"url_for\('admin_edit_loan'\)", "url_for('admin_edit_loan', instance_name=instance_name)"),
        (r"url_for\('admin_view_loan'\)", "url_for('admin_view_loan', instance_name=instance_name)"),
        (r"url_for\('admin_interest_rate'\)", "url_for('admin_interest_rate', instance_name=instance_name)"),
        (r"url_for\('admin_backup'\)", "url_for('admin_backup', instance_name=instance_name)"),
        (r"url_for\('customer_dashboard'\)", "url_for('customer_dashboard', instance_name=instance_name)"),
        (r"url_for\('customer_loan_detail'\)", "url_for('customer_loan_detail', instance_name=instance_name)"),
        (r"url_for\('customer_make_payment'\)", "url_for('customer_make_payment', instance_name=instance_name)"),
        (r"url_for\('customer_edit_notes'\)", "url_for('customer_edit_notes', instance_name=instance_name)"),
    ]
    
    for pattern, replacement in patterns:
        content = re.sub(pattern, replacement, content)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed: {file_path}")

def main():
    """Fix all template files"""
    templates_dir = Path("templates")
    
    # Fix all HTML files
    for html_file in templates_dir.rglob("*.html"):
        fix_template_urls(html_file)
    
    print("All templates fixed!")

if __name__ == "__main__":
    main()

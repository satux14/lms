"""
Internationalization (i18n) Configuration Module
================================================

This module provides internationalization support for the lending management system.
It's designed to be modular and can be easily disabled by not importing it in app_multi.py

Supported Languages:
- English (en) - Default
- Tamil (ta) - தமிழ்

To disable i18n:
1. Comment out the import in app_multi.py
2. Remove the init_i18n() call
3. The app will fall back to English strings
"""

from flask_babel import Babel, lazy_gettext as _l
from flask import request, session

# Supported languages
LANGUAGES = {
    'en': 'English',
    'ta': 'தமிழ்'  # Tamil
}

DEFAULT_LANGUAGE = 'en'

babel = None

def get_locale():
    """
    Determine the best language to use for the current request
    Priority:
    1. User's saved preference (from database)
    2. Session language
    3. Browser's accept-language header
    4. Default language
    """
    # Check if user is logged in and has a language preference
    from flask_login import current_user
    if current_user and current_user.is_authenticated:
        if hasattr(current_user, 'language_preference') and current_user.language_preference:
            return current_user.language_preference
    
    # Check session
    if 'language' in session:
        return session.get('language')
    
    # Check browser preferences
    return request.accept_languages.best_match(list(LANGUAGES.keys())) or DEFAULT_LANGUAGE


def init_i18n(app):
    """
    Initialize internationalization support for the Flask app
    
    Args:
        app: Flask application instance
    
    Returns:
        Babel instance
    """
    global babel
    
    # Configure Babel
    app.config['BABEL_DEFAULT_LOCALE'] = DEFAULT_LANGUAGE
    app.config['BABEL_SUPPORTED_LOCALES'] = list(LANGUAGES.keys())
    app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations'
    
    # Compile translations if .po files exist
    try:
        import os
        from babel.messages.pofile import read_po
        from babel.messages.mofile import write_mo
        
        translations_dir = os.path.join(os.path.dirname(__file__), 'translations')
        if os.path.exists(translations_dir):
            # Find all .po files and compile them to .mo
            compiled_count = 0
            for root, dirs, files in os.walk(translations_dir):
                for file in files:
                    if file.endswith('.po'):
                        po_path = os.path.join(root, file)
                        mo_path = po_path[:-3] + '.mo'  # Replace .po with .mo
                        try:
                            with open(po_path, 'rb') as po_file:
                                catalog = read_po(po_file)
                            with open(mo_path, 'wb') as mo_file:
                                write_mo(mo_file, catalog)
                            compiled_count += 1
                        except Exception as e:
                            print(f"⚠️  Failed to compile {po_path}: {e}")
            
            if compiled_count > 0:
                print(f"✅ Compiled {compiled_count} translation file(s)")
    except ImportError:
        # Try subprocess method if babel API not available
        try:
            import subprocess
            import sys
            translations_dir = os.path.join(os.path.dirname(__file__), 'translations')
            if os.path.exists(translations_dir):
                result = subprocess.run(
                    ['pybabel', 'compile', '-d', translations_dir, '-D', 'messages'],
                    capture_output=True,
                    text=True,
                    cwd=os.path.dirname(__file__)
                )
                if result.returncode == 0:
                    print("✅ Translations compiled successfully")
                else:
                    print(f"⚠️  Translation compilation warning: {result.stderr}")
        except Exception as e:
            print(f"⚠️  Could not compile translations: {e}")
    except Exception as e:
        # If compilation fails, Flask-Babel will try to compile on-demand
        print(f"⚠️  Could not compile translations at startup: {e}")
        print("   Translations will be compiled on-demand by Flask-Babel")
    
    # Initialize Babel with locale_selector
    babel = Babel(app, locale_selector=get_locale)
    
    # Add context processor to make i18n variables available in templates
    @app.context_processor
    def inject_i18n():
        from flask_babel import gettext, lazy_gettext
        from datetime import timedelta
        return {
            'gettext': gettext,
            '_': gettext,
            'lazy_gettext': lazy_gettext,
            'current_language': get_current_language(),
            'supported_languages': LANGUAGES,
            'timedelta': timedelta  # Make timedelta available in templates
        }
    
    return babel


def get_supported_languages():
    """
    Get dictionary of supported languages
    
    Returns:
        dict: Language codes and names
    """
    return LANGUAGES.copy()


def get_current_language():
    """
    Get the current language code
    
    Returns:
        str: Current language code (e.g., 'en', 'ta')
    """
    try:
        return get_locale()
    except:
        return DEFAULT_LANGUAGE


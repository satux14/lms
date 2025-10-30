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


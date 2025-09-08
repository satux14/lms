"""
Multi-Instance Lending Management System
======================================

This is the main application that handles multiple instances (prod, dev, testing).
It routes requests to the appropriate instance based on the URL path.

URL Structure:
- /prod/... - Production instance
- /dev/... - Development instance  
- /testing/... - Testing instance
- /... - Default to production instance

Author: Lending Management System
Version: 1.0.1
"""

from flask import Flask, request, redirect, url_for, render_template, g
from werkzeug.wsgi import DispatcherMiddleware
from app_factory import create_app
from instance_manager import InstanceManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_multi_instance_app():
    """Create the main multi-instance application"""
    
    # Create Flask app for routing
    main_app = Flask(__name__)
    main_app.config['SECRET_KEY'] = 'multi-instance-lending-system'
    
    # Initialize instance manager
    instance_manager = InstanceManager(main_app)
    
    # Create individual instance apps
    instance_apps = {}
    for instance_name in instance_manager.VALID_INSTANCES:
        instance_apps[instance_name] = create_app(instance_name)
        logger.info(f"Created {instance_name} instance")
    
    @main_app.route('/')
    def index():
        """Main index page - show instance selection"""
        instances_info = instance_manager.get_all_instances_info()
        return render_template('instance_selector.html', instances_info=instances_info)
    
    @main_app.route('/<instance_name>/')
    def instance_index(instance_name):
        """Redirect to instance login"""
        if instance_name in instance_manager.VALID_INSTANCES:
            return redirect(f'/{instance_name}/login')
        else:
            return redirect('/')
    
    @main_app.route('/<instance_name>/<path:path>')
    def instance_route(instance_name, path):
        """Route to specific instance"""
        if instance_name in instance_manager.VALID_INSTANCES:
            # Set current instance in g object
            g.current_instance = instance_name
            
            # Get the instance app
            instance_app = instance_apps[instance_name]
            
            # Create a new request context for the instance app
            with instance_app.test_request_context(f'/{path}', method=request.method):
                # Copy request data
                for key, value in request.form.items():
                    instance_app.request.form[key] = value
                
                # Handle the request
                return instance_app.full_dispatch_request()
        else:
            return redirect('/')
    
    # Create dispatcher middleware
    dispatcher = DispatcherMiddleware(main_app, {
        '/prod': instance_apps['prod'],
        '/dev': instance_apps['dev'],
        '/testing': instance_apps['testing']
    })
    
    return dispatcher

# Create the application
app = create_multi_instance_app()

if __name__ == '__main__':
    # For development, run the main app
    from werkzeug.serving import run_simple
    run_simple('localhost', 8080, app, use_reloader=True, use_debugger=True)

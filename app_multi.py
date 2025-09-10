"""
Multi-Instance Lending Management System
======================================

This is a simplified multi-instance application that handles prod, dev, and testing instances
in a single Flask app with URL-based routing.

URL Structure:
- /prod/... - Production instance
- /dev/... - Development instance  
- /testing/... - Testing instance
- /... - Default to production instance

Author: Lending Management System
Version: 1.0.1
"""

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, g, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
import uuid
import secrets
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

# Instance configuration
DEFAULT_INSTANCE = 'prod'
VALID_INSTANCES = ['prod', 'dev', 'testing']

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions without database URI first
db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'login_redirect'

# We'll initialize with app later after setting the correct database URI

@login_manager.user_loader
def load_user(user_id):
    try:
        # Get current instance from g or default to prod
        instance = getattr(g, 'current_instance', 'prod')
        
        # Ensure database manager is initialized
        if not db_manager.initialized:
            db_manager.initialize_all_databases()
        
        user = db_manager.get_query_for_instance(instance, User).get(int(user_id))
        return user
    except Exception as e:
        # If there's any error, return None (user not found)
        return None

# Database Models (same as original)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

class InterestRate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rate = db.Column(db.Numeric(10, 4), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

class Loan(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    loan_name = db.Column(db.String(100), nullable=False)
    principal_amount = db.Column(db.Numeric(15, 2), nullable=False)
    remaining_principal = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 4), nullable=False)
    payment_frequency = db.Column(db.String(20), nullable=False)
    loan_type = db.Column(db.String(20), nullable=False, default='regular')
    admin_notes = db.Column(db.Text, nullable=True)
    customer_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationships
    customer = db.relationship('User', backref='loans')
    payments = db.relationship('Payment', backref='loan', lazy=True, order_by='Payment.payment_date.desc()')

class Payment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)
    payment_type = db.Column(db.String(20), nullable=False)
    interest_amount = db.Column(db.Numeric(15, 2), default=0)
    principal_amount = db.Column(db.Numeric(15, 2), default=0)
    transaction_id = db.Column(db.String(100), nullable=True)
    payment_method = db.Column(db.String(20), nullable=True)
    proof_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.String(20), default='pending')

class PendingInterest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    loan_id = db.Column(db.Integer, db.ForeignKey('loan.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    month_year = db.Column(db.String(7), nullable=False)
    is_paid = db.Column(db.Boolean, default=False)

# Instance management

def get_current_instance():
    """Get current instance from URL path"""
    try:
        path_parts = request.path.strip('/').split('/')
        if path_parts and path_parts[0] in VALID_INSTANCES:
            return path_parts[0]
        return DEFAULT_INSTANCE
    except:
        return DEFAULT_INSTANCE

def get_database_uri(instance=None):
    """Get database URI for specific instance"""
    if instance is None:
        instance = get_current_instance()
    
    if instance not in VALID_INSTANCES:
        instance = DEFAULT_INSTANCE
    
    # Create instance directory (singular)
    instance_dir = Path("instance") / instance
    instance_dir.mkdir(parents=True, exist_ok=True)
    
    # Create database directory
    db_dir = instance_dir / "database"
    db_dir.mkdir(exist_ok=True)
    
    db_path = db_dir / f"lending_app_{instance}.db"
    return f"sqlite:///{db_path.absolute()}"

def get_uploads_folder(instance=None):
    """Get uploads folder for specific instance"""
    if instance is None:
        instance = get_current_instance()
    
    if instance not in VALID_INSTANCES:
        instance = DEFAULT_INSTANCE
    
    instances_dir = Path("instances")
    instance_dir = instances_dir / instance
    uploads_dir = instance_dir / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    
    return str(uploads_dir)

def configure_app_for_instance(instance):
    """Configure app for specific instance"""
    app.config['SQLALCHEMY_DATABASE_URI'] = get_database_uri(instance)
    app.config['UPLOAD_FOLDER'] = get_uploads_folder(instance)
    app.config['INSTANCE_NAME'] = instance

# Custom database manager for proper instance isolation
class DatabaseManager:
    def __init__(self):
        self.databases = {}
        self.engines = {}
        self.sessions = {}
        self.initialized = False
    
    def initialize_all_databases(self):
        """Initialize all database connections for all instances"""
        if self.initialized:
            return
        
        print("Initializing database connections for all instances...")
        
        for instance in VALID_INSTANCES:
            print(f"  Initializing {instance} database...")
            
            # Configure the database URI
            instance_uri = get_database_uri(instance)
            
            # Create engine for this instance
            engine = create_engine(instance_uri)
            self.engines[instance] = engine
            
            # Create session for this instance
            session = sessionmaker(bind=engine)()
            self.sessions[instance] = session
            
            # Create tables using the engine
            with engine.connect() as conn:
                # Import the models to ensure they're registered
                from app_multi import User, Loan, Payment
                
                # Create all tables
                db.metadata.create_all(engine)
        
        self.initialized = True
        print("All database connections initialized successfully!")
    
    
    def get_engine_for_instance(self, instance):
        """Get engine for specific instance"""
        if not self.initialized:
            self.initialize_all_databases()
        
        if instance not in self.engines:
            raise ValueError(f"Engine for instance '{instance}' not found")
        
        return self.engines[instance]
    
    def get_session_for_instance(self, instance):
        """Get session for specific instance"""
        if not self.initialized:
            self.initialize_all_databases()
        
        if instance not in self.sessions:
            raise ValueError(f"Session for instance '{instance}' not found")
        
        return self.sessions[instance]
    
    
    def get_query_for_instance(self, instance, model_class):
        """Get query object for specific instance and model"""
        if not self.initialized:
            self.initialize_all_databases()
        
        if instance not in self.sessions:
            raise ValueError(f"Session for instance '{instance}' not found")
        
        session = self.sessions[instance]
        return session.query(model_class)
    
    def add_to_instance(self, instance, obj):
        """Add object to specific instance database"""
        if not self.initialized:
            self.initialize_all_databases()
        
        if instance not in self.sessions:
            raise ValueError(f"Session for instance '{instance}' not found")
        
        session = self.sessions[instance]
        session.add(obj)
        session.commit()
        return obj

# Global database manager
db_manager = DatabaseManager()

# Custom database initialization function
def init_database_for_instance(instance):
    """Initialize database for specific instance"""
    instance_uri = get_database_uri(instance)
    app.config['SQLALCHEMY_DATABASE_URI'] = instance_uri
    
    # Create all tables
    with app.app_context():
        db.create_all()

# Initialize app
def init_app():
    """Initialize the application"""
    # Configure for default instance first
    configure_app_for_instance(DEFAULT_INSTANCE)
    
    # Initialize database and login manager with the configured app
    db.init_app(app)
    login_manager.init_app(app)
    
    # Initialize all database connections
    db_manager.initialize_all_databases()
    
    # Create default data for all instances
    with app.app_context():
        for instance in VALID_INSTANCES:
            # Set the instance in g for create_default_data
            g.current_instance = instance
            create_default_data(instance)
    
    return app

def create_default_data(instance):
    """Create default data for instance"""
    # Create default admin user if it doesn't exist
    User_query = db_manager.get_query_for_instance(instance, User)
    if not User_query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email=f'admin@{instance}.lendingapp.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db_manager.add_to_instance(instance, admin)
        
        # Create default interest rate
        default_rate = InterestRate(rate=Decimal('0.21'))  # 21%
        db_manager.add_to_instance(instance, default_rate)
        
        print(f"Default admin user created for {instance}: username='admin', password='admin123'")

# Helper functions
def get_current_instance_from_g():
    """Get current instance from Flask g object"""
    return getattr(g, 'current_instance', 'prod')

def get_user_query():
    """Get User query for current instance"""
    instance = get_current_instance_from_g()
    return db_manager.get_query_for_instance(instance, User)

def get_loan_query():
    """Get Loan query for current instance"""
    instance = get_current_instance_from_g()
    return db_manager.get_query_for_instance(instance, Loan)

def get_payment_query():
    """Get Payment query for current instance"""
    instance = get_current_instance_from_g()
    return db_manager.get_query_for_instance(instance, Payment)

def get_interest_rate_query():
    """Get InterestRate query for current instance"""
    instance = get_current_instance_from_g()
    return db_manager.get_query_for_instance(instance, InterestRate)

def add_to_current_instance(obj):
    """Add object to current instance database"""
    instance = get_current_instance_from_g()
    return db_manager.add_to_instance(instance, obj)

def commit_current_instance():
    """Commit current instance database"""
    instance = get_current_instance_from_g()
    session = db_manager.get_session_for_instance(instance)
    session.commit()

def calculate_daily_interest(principal, annual_rate):
    """Calculate daily interest amount"""
    try:
        daily_rate = annual_rate / 365
        return Decimal(str(principal)) * Decimal(str(daily_rate))
    except (InvalidOperation, TypeError):
        return Decimal('0')

def calculate_monthly_interest(principal, annual_rate):
    """Calculate monthly interest amount"""
    try:
        monthly_rate = annual_rate / 12
        return Decimal(str(principal)) * Decimal(str(monthly_rate))
    except (InvalidOperation, TypeError):
        return Decimal('0')

def calculate_interest_for_period(principal, annual_rate, start_date, end_date):
    """Calculate interest for a specific time period"""
    try:
        days = (end_date - start_date).days
        if days <= 0:
            return Decimal('0')
        
        daily_rate = annual_rate / 365
        return Decimal(str(principal)) * Decimal(str(daily_rate)) * Decimal(str(days))
    except (InvalidOperation, TypeError):
        return Decimal('0')

def calculate_accumulated_interest(loan, as_of_date=None):
    """Calculate total accumulated interest for a loan"""
    try:
        if as_of_date is None:
            as_of_date = date.today()
        
        if loan.loan_type == 'interest_only':
            # For interest-only loans, calculate interest on original principal
            total_interest = calculate_interest_for_period(
                loan.principal_amount, 
                loan.interest_rate, 
                loan.created_at.date(), 
                as_of_date
            )
            
            # Subtract verified interest payments
            verified_interest_payments = get_payment_query().with_entities(db.func.sum(Payment.interest_amount)).filter_by(
                loan_id=loan.id, 
                status='verified'
            ).scalar() or 0
            
            return total_interest - Decimal(str(verified_interest_payments))
        else:
            # For regular loans, accumulated interest is the interest on remaining principal
            # from the last payment date (or loan creation) to today
            last_payment = get_payment_query().filter_by(
                loan_id=loan.id, 
                status='verified'
            ).order_by(Payment.payment_date.desc()).first()
            
            if last_payment:
                start_date = last_payment.payment_date
            else:
                start_date = loan.created_at.date()
            
            # Calculate interest on remaining principal from start_date to today
            accumulated_interest = calculate_interest_for_period(
                loan.remaining_principal, 
                loan.interest_rate, 
                start_date, 
                as_of_date
            )
            
            return accumulated_interest
    except Exception as e:
        print(f"Error calculating accumulated interest: {e}")
        return Decimal('0')

def process_payment(loan, payment_amount, payment_date=None, transaction_id=None, 
                   payment_method=None, proof_filename=None):
    """Process a payment for a loan"""
    try:
        if payment_date is None:
            payment_date = datetime.utcnow()
        
        payment_amount = Decimal(str(payment_amount))
        
        if loan.loan_type == 'interest_only':
            # For interest-only loans, calculate total pending interest
            total_pending_interest = calculate_accumulated_interest(loan, payment_date.date())
            
            # Allow small rounding differences (within 0.01)
            if payment_amount > total_pending_interest + Decimal('0.01'):
                raise ValueError(f"Payment amount (₹{payment_amount}) exceeds pending interest (₹{total_pending_interest:.2f}) for interest-only loan. Maximum allowed: ₹{total_pending_interest:.2f}")
            
            # All payment goes to interest
            interest_amount = payment_amount
            principal_amount = Decimal('0')
        else:
            # For regular loans, calculate immediate interest due
            if loan.payment_frequency == 'daily':
                interest_due = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
            else:  # monthly
                interest_due = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
            
            if payment_amount >= interest_due:
                interest_amount = interest_due
                principal_amount = payment_amount - interest_due
            else:
                interest_amount = payment_amount
                principal_amount = Decimal('0')
        
        # Create payment record
        payment = Payment(
            loan_id=loan.id,
            amount=payment_amount,
            payment_date=payment_date,
            payment_type='both' if principal_amount > 0 else 'interest',
            interest_amount=interest_amount,
            principal_amount=principal_amount,
            transaction_id=transaction_id,
            payment_method=payment_method,
            proof_filename=proof_filename,
            status='pending'  # All payments start as pending
        )
        
        add_to_current_instance(payment)
        
        return payment
        
    except Exception as e:
        # Rollback is handled by the instance-specific session
        raise e

def verify_payment(payment_id):
    """Verify a payment and update loan balance"""
    try:
        payment = get_payment_query().filter_by(id=payment_id).first()
        if not payment:
            return  # Payment not found
        loan = payment.loan
        
        if payment.status == 'verified':
            return  # Already verified
        
        # Update payment status
        payment.status = 'verified'
        
        # Update loan balance (only for regular loans)
        if loan.loan_type != 'interest_only':
            loan.remaining_principal -= payment.principal_amount
            if loan.remaining_principal < 0:
                loan.remaining_principal = Decimal('0')
        
        commit_current_instance()
        
    except Exception as e:
        # Rollback is handled by the instance-specific session
        raise e

# Routes
@app.before_request
def before_request():
    """Configure app for current instance before each request"""
    instance = get_current_instance()
    g.current_instance = instance
    
    # Just store the instance in g - don't modify the global db object
    # The helper functions will handle instance-specific database access
    if instance not in VALID_INSTANCES:
        flash('Invalid instance', 'error')
        return redirect('/')

@app.context_processor
def inject_current_user():
    """Make current_user available in all templates"""
    from flask_login import current_user
    return dict(current_user=current_user)

@app.route('/')
def index():
    """Default route - redirect to production instance"""
    return redirect(url_for('login', instance_name='prod'))

@app.route('/instances')
def instances():
    """Instance selector page - show all instances"""
    instances_info = {}
    for instance in VALID_INSTANCES:
        instances_info[instance] = {
            'name': instance,
            'database_exists': Path(f"instances/{instance}/database/lending_app_{instance}.db").exists(),
            'database_size': 0
        }
        
        db_path = Path(f"instances/{instance}/database/lending_app_{instance}.db")
        if db_path.exists():
            instances_info[instance]['database_size'] = db_path.stat().st_size
    
    return render_template('instance_selector.html', instances_info=instances_info)

@app.route('/login_redirect')
def login_redirect():
    """Redirect to login for current instance"""
    next_url = request.args.get('next', '')
    if next_url:
        # Extract instance from next URL
        if next_url.startswith('/'):
            next_url = next_url[1:]  # Remove leading slash
        path_parts = next_url.split('/')
        if path_parts and path_parts[0] in VALID_INSTANCES:
            instance = path_parts[0]
        else:
            instance = DEFAULT_INSTANCE
    else:
        instance = get_current_instance()
    return redirect(url_for('login', instance_name=instance))

@app.route('/<instance_name>/')
def instance_index(instance_name):
    """Redirect to instance login"""
    if instance_name in VALID_INSTANCES:
        return redirect(f'/{instance_name}/login')
    else:
        return redirect('/')

@app.route('/<instance_name>/login', methods=['GET', 'POST'])
def login(instance_name):
    """User login for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_query().filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            try:
                # Ensure we're in the correct app context
                from flask import current_app
                if not hasattr(current_app, 'login_manager'):
                    print("Warning: login_manager not found in current_app")
                    flash('Login system not properly initialized. Please try again.', 'error')
                    return render_template('login.html', instance_name=instance_name)
                
                login_user(user)
            except Exception as e:
                print(f"Error during login_user: {e}")
                import traceback
                traceback.print_exc()
                flash('Login failed. Please try again.', 'error')
                return render_template('login.html', instance_name=instance_name)
            next_page = request.args.get('next')
            if user.is_admin:
                return redirect(next_page) if next_page else redirect(url_for('admin_dashboard', instance_name=instance_name))
            else:
                return redirect(next_page) if next_page else redirect(url_for('customer_dashboard', instance_name=instance_name))
        else:
            flash('Invalid username or password')
    
    return render_template('login.html', instance_name=instance_name)

@app.route('/<instance_name>/logout')
@login_required
def logout(instance_name):
    """User logout"""
    logout_user()
    return redirect(url_for('login', instance_name=instance_name))

@app.route('/<instance_name>/register', methods=['GET', 'POST'])
def register(instance_name):
    """User registration for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form.get('email', '')  # Email is optional
        password = request.form['password']
        
        if get_user_query().filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html', instance_name=instance_name)
        
        user = User(
            username=username,
            email=email if email else None,
            password_hash=generate_password_hash(password),
            is_admin=False
        )
        
        add_to_current_instance(user)
        
        flash('Registration successful! Please login.')
        return redirect(url_for('login', instance_name=instance_name))
    
    return render_template('register.html', instance_name=instance_name)

# Admin routes
@app.route('/<instance_name>/admin')
@login_required
def admin_dashboard(instance_name):
    """Admin dashboard for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    # Get statistics
    total_loans = get_loan_query().count()
    total_principal = sum(loan.principal_amount for loan in get_loan_query().all())
    total_interest_earned = sum(payment.interest_amount for payment in get_payment_query().filter_by(status='verified').all())
    total_users = get_user_query().count()
    
    return render_template('admin/dashboard.html', 
                         total_loans=total_loans,
                         total_principal=total_principal,
                         total_interest_earned=total_interest_earned,
                         total_users=total_users,
                         instance_name=instance_name)

# Admin Interest Rate route
@app.route('/<instance_name>/admin/interest-rate')
@login_required
def admin_interest_rate(instance_name):
    """Admin interest rate page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    # This page is now informational only since each loan has its own rate
    return render_template('admin/interest_rate.html', instance_name=instance_name)

# Admin Loans route
@app.route('/<instance_name>/admin/loans')
@login_required
def admin_loans(instance_name):
    """Admin loans page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    # Get filter parameters
    loan_type = request.args.get('loan_type', '')
    frequency = request.args.get('frequency', '')
    customer_id = request.args.get('customer', '')
    loan_name = request.args.get('loan_name', '')
    min_rate = request.args.get('min_rate', '')
    max_rate = request.args.get('max_rate', '')
    status = request.args.get('status', '')
    
    # Build query
    query = get_loan_query()
    
    if loan_type:
        query = query.filter(Loan.loan_type == loan_type)
    if frequency:
        query = query.filter(Loan.payment_frequency == frequency)
    if customer_id:
        query = query.filter(Loan.customer_id == customer_id)
    if loan_name:
        query = query.filter(Loan.loan_name.contains(loan_name))
    if min_rate:
        # Convert percentage to decimal for comparison
        min_rate_decimal = float(min_rate) / 100
        query = query.filter(Loan.interest_rate >= min_rate_decimal)
    if max_rate:
        # Convert percentage to decimal for comparison
        max_rate_decimal = float(max_rate) / 100
        query = query.filter(Loan.interest_rate <= max_rate_decimal)
    if status:
        if status == 'active':
            query = query.filter(Loan.is_active == True)
        elif status == 'paid_off':
            query = query.filter(Loan.is_active == False)
    
    # Get sorting parameters
    sort_by = request.args.get('sort', 'created_at')
    sort_order = request.args.get('order', 'desc')
    
    if sort_by == 'customer':
        if sort_order == 'asc':
            query = query.join(User).order_by(User.username.asc())
        else:
            query = query.join(User).order_by(User.username.desc())
    elif sort_by == 'loan_name':
        if sort_order == 'asc':
            query = query.order_by(Loan.loan_name.asc())
        else:
            query = query.order_by(Loan.loan_name.desc())
    elif sort_by == 'principal':
        if sort_order == 'asc':
            query = query.order_by(Loan.principal_amount.asc())
        else:
            query = query.order_by(Loan.principal_amount.desc())
    elif sort_by == 'rate':
        if sort_order == 'asc':
            query = query.order_by(Loan.interest_rate.asc())
        else:
            query = query.order_by(Loan.interest_rate.desc())
    else:  # created_at
        if sort_order == 'asc':
            query = query.order_by(Loan.created_at.asc())
        else:
            query = query.order_by(Loan.created_at.desc())
    
    loans = query.all()
    customers = get_user_query().filter_by(is_admin=False).all()
    
    return render_template('admin/loans.html', 
                         loans=loans, 
                         customers=customers,
                         loan_type=loan_type,
                         frequency=frequency,
                         customer_id=customer_id,
                         loan_name=loan_name,
                         min_rate=min_rate,
                         max_rate=max_rate,
                         status=status,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         instance_name=instance_name)

# Admin Users route
@app.route('/<instance_name>/admin/users')
@login_required
def admin_users(instance_name):
    """Admin users page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    users = get_user_query().all()
    total_loans = sum(len(user.loans) for user in users)
    admin_count = sum(1 for user in users if user.is_admin)
    customer_count = len(users) - admin_count
    
    return render_template('admin/users.html', 
                         users=users, 
                         total_loans=total_loans,
                         admin_count=admin_count,
                         customer_count=customer_count,
                         instance_name=instance_name)

# Admin Create User route
@app.route('/<instance_name>/admin/create-user', methods=['GET', 'POST'])
@login_required
def admin_create_user(instance_name):
    """Admin create user page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    if request.method == 'POST':
        username = request.form['username']
        email = request.form.get('email', '')  # Email is optional
        password = request.form['password']
        is_admin = 'is_admin' in request.form
        
        if get_user_query().filter_by(username=username).first():
            flash('Username already exists')
            return render_template('admin/create_user.html', instance_name=instance_name)
        
        user = User(
            username=username,
            email=email if email else None,
            password_hash=generate_password_hash(password),
            is_admin=is_admin
        )
        add_to_current_instance(user)
        
        flash(f'User {username} created successfully')
        return redirect(url_for('admin_users', instance_name=instance_name))
    
    return render_template('admin/create_user.html', instance_name=instance_name)

# Admin Create Loan route
@app.route('/<instance_name>/admin/create-loan', methods=['GET', 'POST'])
@login_required
def admin_create_loan(instance_name):
    """Admin create loan page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    if request.method == 'POST':
        customer_id = request.form['customer_id']
        loan_name = request.form['loan_name']
        principal_amount = Decimal(request.form['principal'])
        interest_rate = Decimal(request.form['interest_rate']) / 100
        payment_frequency = request.form['payment_frequency']
        loan_type = request.form['loan_type']
        admin_notes = request.form.get('admin_notes', '')
        customer_notes = request.form.get('customer_notes', '')
        # Handle custom creation date if provided
        custom_created_date = request.form.get('loan_created_date')
        custom_created_time = request.form.get('loan_created_time')
        
        if custom_created_date:
            try:
                if custom_created_time:
                    # Combine date and time
                    created_at_str = f"{custom_created_date} {custom_created_time}"
                    created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M')
                else:
                    # Use date only, set time to 00:00
                    created_at = datetime.strptime(custom_created_date, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Using current date.', 'warning')
                created_at = datetime.utcnow()
        elif custom_created_time:
            try:
                # If only time is provided, use current date with specified time
                time_obj = datetime.strptime(custom_created_time, '%H:%M').time()
                created_at = datetime.utcnow().replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
            except ValueError:
                flash('Invalid time format. Using current date/time.', 'warning')
                created_at = datetime.utcnow()
        else:
            created_at = datetime.utcnow()
        
        loan = Loan(
            customer_id=customer_id,
            loan_name=loan_name,
            principal_amount=principal_amount,
            remaining_principal=principal_amount,
            interest_rate=interest_rate,
            payment_frequency=payment_frequency,
            loan_type=loan_type,
            admin_notes=admin_notes,
            customer_notes=customer_notes,
            created_at=created_at
        )
        add_to_current_instance(loan)
        
        flash('Loan created successfully')
        return redirect(url_for('admin_loans', instance_name=instance_name))
    
    customers = get_user_query().filter_by(is_admin=False).all()
    return render_template('admin/create_loan.html', 
                         customers=customers,
                         instance_name=instance_name)

# Admin Payments route
@app.route('/<instance_name>/admin/payments')
@login_required
def admin_payments(instance_name):
    """Admin payments page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    # Get filter parameters
    customer_filter = request.args.get('customer', '')
    loan_filter = request.args.get('loan', '')
    status_filter = request.args.get('status', '')
    payment_method = request.args.get('payment_method', '')
    
    # Build query
    # Get the current instance session for complex queries
    instance = get_current_instance_from_g()
    session = db_manager.get_session_for_instance(instance)
    query = session.query(Payment, Loan, User).join(Loan, Payment.loan_id == Loan.id).join(User, Loan.customer_id == User.id)
    
    if customer_filter:
        query = query.filter(User.username.contains(customer_filter))
    if loan_filter:
        query = query.filter(Loan.loan_name.contains(loan_filter))
    if status_filter:
        query = query.filter(Payment.status == status_filter)
    if payment_method:
        query = query.filter(Payment.payment_method == payment_method)
    
    # Get sorting parameters
    sort_by = request.args.get('sort', 'payment_date')
    sort_order = request.args.get('order', 'desc')
    
    if sort_by == 'customer':
        if sort_order == 'asc':
            query = query.order_by(User.username.asc())
        else:
            query = query.order_by(User.username.desc())
    elif sort_by == 'loan':
        if sort_order == 'asc':
            query = query.order_by(Loan.loan_name.asc())
        else:
            query = query.order_by(Loan.loan_name.desc())
    elif sort_by == 'amount':
        if sort_order == 'asc':
            query = query.order_by(Payment.amount.asc())
        else:
            query = query.order_by(Payment.amount.desc())
    else:  # payment_date
        if sort_order == 'asc':
            query = query.order_by(Payment.payment_date.asc())
        else:
            query = query.order_by(Payment.payment_date.desc())
    
    payments = query.all()
    
    # Calculate total interest paid (verified payments only)
    total_interest_paid = get_payment_query().filter_by(status='verified').with_entities(db.func.sum(Payment.interest_amount)).scalar() or 0
    
    # Calculate filtered totals
    filtered_principal = sum(payment.principal_amount for payment, loan, user in payments)
    filtered_interest = sum(payment.interest_amount for payment, loan, user in payments)
    filtered_total = sum(payment.amount for payment, loan, user in payments)
    
    # Get unique customers and loans for filters
    customers = [user.username for user in get_user_query().filter_by(is_admin=False).all()]
    loans = [loan.loan_name for loan in get_loan_query().all()]
    
    # Handle Excel export
    if request.args.get('export') == 'excel':
        from backup_multi import MultiInstanceBackupManager
        backup_manager = MultiInstanceBackupManager(app)
        return backup_manager.export_to_excel(instance_name)
    
    return render_template('admin/payments.html', 
                         payments=payments,
                         total_interest_paid=total_interest_paid,
                         filtered_principal=filtered_principal,
                         filtered_interest=filtered_interest,
                         filtered_total=filtered_total,
                         customers=customers,
                         loans=loans,
                         customer_filter=customer_filter,
                         loan_filter=loan_filter,
                         status_filter=status_filter,
                         payment_method=payment_method,
                         sort_by=sort_by,
                         sort_order=sort_order,
                         instance_name=instance_name)

# Admin Add Payment route
@app.route('/<instance_name>/admin/add-payment', methods=['GET', 'POST'])
@app.route('/<instance_name>/admin/add-payment/<int:loan_id>', methods=['GET', 'POST'])
@login_required
def admin_add_payment(instance_name, loan_id=None):
    """Admin add payment page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    if request.method == 'POST':
        loan_id = request.form['loan_id']
        amount = Decimal(request.form['amount'])
        payment_method = request.form['payment_method']
        transaction_id = request.form.get('transaction_id', '')
        payment_date_str = request.form.get('payment_date')
        
        # Parse payment date
        if payment_date_str:
            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format')
                return render_template('admin/add_payment.html', 
                                     loans=get_loan_query().all(),
                                     selected_loan_id=loan_id,
                                     instance_name=instance_name)
        else:
            payment_date = datetime.utcnow()
        
        loan = get_loan_query().get(loan_id)
        if not loan:
            flash('Loan not found')
            return redirect(url_for('admin_payments', instance_name=instance_name))
        
        # Process payment using the process_payment function
        try:
            payment = process_payment(
                loan=loan,
                payment_amount=amount,
                payment_date=payment_date,
                transaction_id=transaction_id,
                payment_method=payment_method,
                proof_filename=None
            )
        except ValueError as e:
            flash(str(e))
            return redirect(url_for('admin_add_payment', instance_name=instance_name, loan_id=loan_id))
        
        flash('Payment added successfully. It will be verified by admin.')
        return redirect(url_for('admin_payments', instance_name=instance_name))
    
    loans = get_loan_query().all()
    return render_template('admin/add_payment.html', 
                         loans=loans,
                         selected_loan_id=loan_id,
                         instance_name=instance_name)

# Admin Backup route
@app.route('/<instance_name>/admin/backup')
@login_required
def admin_backup(instance_name):
    """Admin backup page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    from backup_multi import MultiInstanceBackupManager
    backup_manager = MultiInstanceBackupManager(app)
    backup_info = backup_manager.get_backup_info(instance_name)
    
    # Calculate total size in MB
    total_size_mb = 0
    if backup_info and 'instances' in backup_info and instance_name in backup_info['instances']:
        total_size_mb = backup_info['instances'][instance_name].get('total_size', 0) / (1024 * 1024)
    
    # Get database size for current instance
    db_size_mb = backup_manager.get_instance_database_size(instance_name) / (1024 * 1024)
    
    return render_template('admin/backup.html', 
                         backup_info=backup_info,
                         total_size_mb=total_size_mb,
                         db_size_mb=db_size_mb,
                         instance_name=instance_name)

# Admin Edit Loan route
@app.route('/<instance_name>/admin/edit-loan/<int:loan_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_loan(instance_name, loan_id):
    """Admin edit loan page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
    
    if request.method == 'POST':
        loan.loan_name = request.form['loan_name']
        loan.principal_amount = Decimal(request.form['principal'])
        # remaining_principal is calculated automatically, not edited directly
        loan.interest_rate = Decimal(request.form['interest_rate']) / 100
        loan.payment_frequency = request.form['payment_frequency']
        loan.loan_type = request.form['loan_type']
        loan.admin_notes = request.form.get('admin_notes', '')
        loan.customer_notes = request.form.get('customer_notes', '')
        
        # Handle custom creation date if provided
        custom_created_date = request.form.get('loan_created_date')
        custom_created_time = request.form.get('loan_created_time')
        
        if custom_created_date:
            try:
                if custom_created_time:
                    # Combine date and time
                    created_at_str = f"{custom_created_date} {custom_created_time}"
                    loan.created_at = datetime.strptime(created_at_str, '%Y-%m-%d %H:%M')
                else:
                    # Use date only, set time to 00:00
                    loan.created_at = datetime.strptime(custom_created_date, '%Y-%m-%d')
            except ValueError:
                flash('Invalid date format. Using current date.', 'warning')
                # Keep existing created_at if date is invalid
        elif custom_created_time:
            # If only time is provided, update the time part of existing date
            try:
                time_obj = datetime.strptime(custom_created_time, '%H:%M').time()
                loan.created_at = loan.created_at.replace(hour=time_obj.hour, minute=time_obj.minute, second=0, microsecond=0)
            except ValueError:
                flash('Invalid time format. Time not updated.', 'warning')
        
        commit_current_instance()
        flash('Loan updated successfully')
        return redirect(url_for('admin_loans', instance_name=instance_name))
    
    # Get payment history for this loan
    payments = get_payment_query().filter_by(loan_id=loan_id).order_by(Payment.payment_date.desc()).all()
    
    return render_template('admin/edit_loan.html', 
                         loan=loan,
                         payments=payments,
                         instance_name=instance_name)

# Admin View Loan route
@app.route('/<instance_name>/admin/loan/<int:loan_id>')
@login_required
def admin_view_loan(instance_name, loan_id):
    """Admin view loan details page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
    
    # Calculate interest information
    daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
    monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
    accumulated_interest = calculate_accumulated_interest(loan)
    
    # Get payment history
    payments = get_payment_query().filter_by(loan_id=loan_id).order_by(Payment.payment_date.desc()).all()
    
    # Calculate verified amounts
    verified_payments = [p for p in payments if p.status == 'verified']
    verified_principal = sum(payment.principal_amount for payment in verified_payments)
    verified_interest = sum(payment.interest_amount for payment in verified_payments)
    
    # Calculate pending amounts
    pending_payments = [p for p in payments if p.status == 'pending']
    pending_principal = sum(payment.principal_amount for payment in pending_payments)
    pending_interest = sum(payment.interest_amount for payment in pending_payments)
    pending_total = pending_principal + pending_interest
    
    # Calculate days active
    days_active = (date.today() - loan.created_at.date()).days
    
    return render_template('admin/view_loan.html', 
                         loan=loan,
                         daily_interest=daily_interest,
                         monthly_interest=monthly_interest,
                         accumulated_interest=accumulated_interest,
                         verified_principal=verified_principal,
                         verified_interest=verified_interest,
                         pending_principal=pending_principal,
                         pending_interest=pending_interest,
                         pending_total=pending_total,
                         payments=payments,
                         days_active=days_active,
                         current_date=date.today(),
                         instance_name=instance_name)

# Admin Edit Payment route
@app.route('/<instance_name>/admin/edit-payment/<int:payment_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_payment(instance_name, payment_id):
    """Admin edit payment page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    payment = get_payment_query().filter_by(id=payment_id).first() or abort(404)
    loan = payment.loan  # Get the loan associated with this payment
    
    if request.method == 'POST':
        payment.amount = Decimal(request.form['amount'])
        payment.payment_method = request.form['payment_method']
        payment.transaction_id = request.form.get('transaction_id', '')
        payment.status = request.form['status']
        
        # Parse payment date
        payment_date_str = request.form.get('payment_date')
        if payment_date_str:
            try:
                payment.payment_date = datetime.strptime(payment_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format')
                return render_template('admin/edit_payment.html', 
                                     payment=payment,
                                     loan=loan,
                                     instance_name=instance_name)
        
        commit_current_instance()
        flash('Payment updated successfully')
        return redirect(url_for('admin_payments', instance_name=instance_name))
    
    return render_template('admin/edit_payment.html', 
                         payment=payment,
                         loan=loan,
                         instance_name=instance_name)

# Admin Create Backup route
@app.route('/<instance_name>/admin/backup/create', methods=['GET', 'POST'])
@login_required
def admin_create_backup(instance_name):
    """Admin create backup for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    from backup_multi import MultiInstanceBackupManager
    backup_manager = MultiInstanceBackupManager(app)
    
    try:
        if request.method == 'POST':
            backup_type = request.form.get('backup_type', 'full')
            
            if backup_type == 'full':
                backup_path = backup_manager.create_full_backup(instance_name)
                if backup_path:
                    flash(f'Full backup created successfully for {instance_name}: {backup_path.name}')
                else:
                    flash(f'Full backup failed for {instance_name}')
            elif backup_type == 'database':
                backup_path = backup_manager.create_database_backup(instance_name)
                if backup_path:
                    flash(f'Database backup created successfully for {instance_name}: {backup_path.name}')
                else:
                    flash(f'Database backup failed for {instance_name}')
            elif backup_type == 'excel':
                backup_path = backup_manager.export_to_excel(instance_name)
                if backup_path:
                    flash(f'Excel export created successfully for {instance_name}: {backup_path.name}')
                else:
                    flash(f'Excel export failed for {instance_name}')
            else:
                flash(f'Invalid backup type: {backup_type}')
        else:
            # GET request - redirect to backup page
            return redirect(url_for('admin_backup', instance_name=instance_name))
            
    except Exception as e:
        flash(f'Backup failed for {instance_name}: {str(e)}')
    
    return redirect(url_for('admin_backup', instance_name=instance_name))

# Admin Cleanup Backups route
@app.route('/<instance_name>/admin/backup/cleanup', methods=['POST'])
@login_required
def admin_cleanup_backups(instance_name):
    """Admin cleanup old backups for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    from backup_multi import MultiInstanceBackupManager
    backup_manager = MultiInstanceBackupManager(app)
    
    try:
        days = int(request.form.get('days', 30))
        cleaned_count = backup_manager.cleanup_old_backups(instance_name, days)
        flash(f'Cleaned up {cleaned_count} backup files older than {days} days for {instance_name}')
    except Exception as e:
        flash(f'Cleanup failed for {instance_name}: {str(e)}')
    
    return redirect(url_for('admin_backup', instance_name=instance_name))

# Admin Download Backup route
@app.route('/<instance_name>/admin/backup/download/<filename>')
@login_required
def admin_download_backup(instance_name, filename):
    """Admin download backup file for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    from backup_multi import MultiInstanceBackupManager
    backup_manager = MultiInstanceBackupManager(app)
    
    try:
        return backup_manager.download_backup(instance_name, filename)
    except Exception as e:
        flash(f'Download failed for {instance_name}: {str(e)}')
        return redirect(url_for('admin_backup', instance_name=instance_name))

# Admin Delete Backup route
@app.route('/<instance_name>/admin/backup/delete/<filename>', methods=['POST'])
@login_required
def admin_delete_backup(instance_name, filename):
    """Admin delete backup file for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    from backup_multi import MultiInstanceBackupManager
    backup_manager = MultiInstanceBackupManager(app)
    
    try:
        success = backup_manager.delete_backup_file(instance_name, filename)
        if success:
            flash(f'Backup file deleted successfully: {filename}')
        else:
            flash(f'Failed to delete backup file: {filename}')
    except Exception as e:
        flash(f'Delete failed for {instance_name}: {str(e)}')
    
    return redirect(url_for('admin_backup', instance_name=instance_name))

# Customer routes
@app.route('/<instance_name>/customer')
@login_required
def customer_dashboard(instance_name):
    """Customer dashboard for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard', instance_name=instance_name))
    
    # Get customer's loans
    loans = get_loan_query().filter_by(customer_id=current_user.id).all()
    
    loan_data = []
    for loan in loans:
        daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
        monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
        accumulated_interest = calculate_accumulated_interest(loan)
        
        # Calculate pending payments for this specific loan
        pending_payments = get_payment_query().filter_by(loan_id=loan.id, status='pending').all()
        pending_principal = sum(payment.principal_amount for payment in pending_payments)
        pending_interest = sum(payment.interest_amount for payment in pending_payments)
        pending_total = sum(payment.amount for payment in pending_payments)
        
        # Calculate verified payments for this specific loan
        verified_payments = get_payment_query().filter_by(loan_id=loan.id, status='verified').all()
        verified_principal = sum(payment.principal_amount for payment in verified_payments)
        verified_interest = sum(payment.interest_amount for payment in verified_payments)
        
        loan_data.append({
            'loan': loan,
            'daily_interest': daily_interest,
            'monthly_interest': monthly_interest,
            'accumulated_interest': accumulated_interest,
            'pending_principal': pending_principal,
            'pending_interest': pending_interest,
            'pending_total': pending_total,
            'verified_principal': verified_principal,
            'verified_interest': verified_interest
        })
    
    return render_template('customer/dashboard.html',
                         loan_data=loan_data,
                         instance_name=instance_name)

# Customer Loan Detail route
@app.route('/<instance_name>/customer/loan/<int:loan_id>')
@login_required
def customer_loan_detail(instance_name, loan_id):
    """Customer loan detail page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard', instance_name=instance_name))
    
    loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
    
    # Check if loan belongs to current user
    if loan.customer_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    # Calculate interest information
    daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
    monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
    accumulated_interest = calculate_accumulated_interest(loan)
    
    # Get payment history
    payments = get_payment_query().filter_by(loan_id=loan_id).order_by(Payment.payment_date.desc()).all()
    
    # Calculate total interest paid for this loan
    total_interest_paid = sum(payment.interest_amount for payment in payments if payment.status == 'verified')
    
    # Calculate verified principal paid for this loan
    verified_principal = sum(payment.principal_amount for payment in payments if payment.status == 'verified')
    
    # Calculate pending amounts for this loan
    pending_principal = sum(payment.principal_amount for payment in payments if payment.status == 'pending')
    pending_interest = sum(payment.interest_amount for payment in payments if payment.status == 'pending')
    pending_total = pending_principal + pending_interest
    
    # Calculate days active
    days_active = (date.today() - loan.created_at.date()).days
    
    # Calculate previous principal and interest for each payment
    # We need to calculate what the principal and interest were before each payment
    payments_with_previous = []
    current_principal = loan.principal_amount
    current_interest_paid = 0
    
    # Process payments in chronological order (oldest first)
    payments_chronological = sorted(payments, key=lambda p: p.payment_date)
    
    for payment in payments_chronological:
        # Store the previous amounts before this payment
        previous_principal = current_principal
        previous_interest_paid = current_interest_paid
        
        # Update current amounts after this payment (only if verified)
        if payment.status == 'verified':
            current_principal -= payment.principal_amount
            current_interest_paid += payment.interest_amount
        
        # Add payment with previous amounts
        payments_with_previous.append({
            'payment': payment,
            'previous_principal': previous_principal,
            'previous_interest_paid': previous_interest_paid
        })
    
    # Reverse to show newest first
    payments_with_previous.reverse()
    
    return render_template('customer/loan_detail.html', 
                         loan=loan,
                         daily_interest=daily_interest,
                         monthly_interest=monthly_interest,
                         accumulated_interest=accumulated_interest,
                         total_interest_paid=total_interest_paid,
                         verified_principal=verified_principal,
                         pending_principal=pending_principal,
                         pending_interest=pending_interest,
                         pending_total=pending_total,
                         payments=payments_with_previous,
                         days_active=days_active,
                         current_date=date.today(),
                         instance_name=instance_name)

# Customer Make Payment route
@app.route('/<instance_name>/customer/loan/<int:loan_id>/payment', methods=['GET', 'POST'])
@login_required
def customer_make_payment(instance_name, loan_id):
    """Customer make payment page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard', instance_name=instance_name))
    
    loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
    
    # Check if loan belongs to current user
    if loan.customer_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    if request.method == 'POST':
        amount = Decimal(request.form['amount'])
        payment_method = request.form['payment_method']
        transaction_id = request.form.get('transaction_id', '')
        payment_date_str = request.form.get('payment_date')
        
        # Parse payment date
        if payment_date_str:
            try:
                payment_date = datetime.strptime(payment_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format')
                return redirect(url_for('customer_loan_detail', instance_name=instance_name, loan_id=loan_id))
        else:
            payment_date = datetime.utcnow()
        
        # Process payment using the process_payment function
        try:
            payment = process_payment(
                loan=loan,
                payment_amount=amount,
                payment_date=payment_date,
                transaction_id=transaction_id,
                payment_method=payment_method,
                proof_filename=None
            )
        except ValueError as e:
            flash(str(e))
            return redirect(url_for('customer_loan_detail', instance_name=instance_name, loan_id=loan_id))
        
        flash('Payment submitted successfully. It will be verified by admin.')
        return redirect(url_for('customer_loan_detail', instance_name=instance_name, loan_id=loan_id))
    
    # Calculate interest information
    daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
    monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
    accumulated_interest = calculate_accumulated_interest(loan)
    
    return render_template('customer/make_payment.html', 
                         loan=loan,
                         daily_interest=daily_interest,
                         monthly_interest=monthly_interest,
                         accumulated_interest=accumulated_interest,
                         instance_name=instance_name)

# Customer Edit Notes route
@app.route('/<instance_name>/customer/loan/<int:loan_id>/edit-notes', methods=['GET', 'POST'])
@login_required
def customer_edit_notes(instance_name, loan_id):
    """Customer edit notes page for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if current_user.is_admin:
        return redirect(url_for('admin_dashboard', instance_name=instance_name))
    
    loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
    
    # Check if loan belongs to current user
    if loan.customer_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    if request.method == 'POST':
        customer_notes = request.form.get('customer_notes', '')
        loan.customer_notes = customer_notes
        commit_current_instance()
        
        flash('Notes updated successfully')
        return redirect(url_for('customer_loan_detail', instance_name=instance_name, loan_id=loan_id))
    
    return render_template('customer/edit_notes.html', 
                         loan=loan,
                         instance_name=instance_name)

# Password Management Routes

# Change Password route
@app.route('/<instance_name>/change-password', methods=['GET', 'POST'])
@login_required
def change_password(instance_name):
    """Change password for current user"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Verify current password
        if not check_password_hash(current_user.password_hash, current_password):
            flash('Current password is incorrect', 'error')
            return render_template('change_password.html', instance_name=instance_name)
        
        # Validate new password
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('change_password.html', instance_name=instance_name)
        
        if len(new_password) < 1:
            flash('Password cannot be empty', 'error')
            return render_template('change_password.html', instance_name=instance_name)
        
        # Update password
        current_user.password_hash = generate_password_hash(new_password)
        commit_current_instance()
        
        flash('Password changed successfully', 'success')
        return redirect(url_for('admin_dashboard' if current_user.is_admin else 'customer_dashboard', instance_name=instance_name))
    
    return render_template('change_password.html', instance_name=instance_name)

# Forgot Password route
@app.route('/<instance_name>/forgot-password', methods=['GET', 'POST'])
def forgot_password(instance_name):
    """Forgot password - send reset email"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if request.method == 'POST':
        email = request.form['email']
        
        # Find user by email
        user = get_user_query().filter_by(email=email).first()
        
        if user:
            # Generate reset token
            reset_token = secrets.token_urlsafe(32)
            user.reset_token = reset_token
            user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
            commit_current_instance()
            
            # Send reset email (simplified - in production, use proper email service)
            try:
                send_password_reset_email(user.email, reset_token, instance_name)
                flash('Password reset instructions have been sent to your email', 'success')
            except Exception as e:
                flash('Error sending email. Please contact administrator.', 'error')
        else:
            flash('No account found with that email address', 'error')
    
    return render_template('forgot_password.html', instance_name=instance_name)

# Reset Password route
@app.route('/<instance_name>/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(instance_name, token):
    """Reset password with token"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    # Find user by token
    user = get_user_query().filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash('Invalid or expired reset token', 'error')
        return redirect(url_for('login', instance_name=instance_name))
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Validate passwords
        if new_password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('reset_password.html', token=token, instance_name=instance_name)
        
        if len(new_password) < 1:
            flash('Password cannot be empty', 'error')
            return render_template('reset_password.html', token=token, instance_name=instance_name)
        
        # Update password and clear reset token
        user.password_hash = generate_password_hash(new_password)
        user.reset_token = None
        user.reset_token_expires = None
        commit_current_instance()
        
        flash('Password reset successfully. Please log in with your new password.', 'success')
        return redirect(url_for('login', instance_name=instance_name))
    
    return render_template('reset_password.html', token=token, instance_name=instance_name)

# Admin Reset User Password route
@app.route('/<instance_name>/admin/reset-user-password/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_reset_user_password(instance_name, user_id):
    """Admin reset any user's password"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied', 'error')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    user = get_user_query().filter_by(id=user_id).first()
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin_users', instance_name=instance_name))
    
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        
        # Validate passwords
        if new_password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('admin/reset_user_password.html', user=user, instance_name=instance_name)
        
        if len(new_password) < 1:
            flash('Password cannot be empty', 'error')
            return render_template('admin/reset_user_password.html', user=user, instance_name=instance_name)
        
        # Update password
        user.password_hash = generate_password_hash(new_password)
        commit_current_instance()
        
        flash(f'Password reset successfully for user {user.username}', 'success')
        return redirect(url_for('admin_users', instance_name=instance_name))
    
    return render_template('admin/reset_user_password.html', user=user, instance_name=instance_name)

# Email helper function
def send_password_reset_email(email, token, instance_name):
    """Send password reset email (simplified implementation)"""
    # In production, use proper email service like SendGrid, AWS SES, etc.
    # For now, we'll just print the reset link to console
    reset_url = f"http://127.0.0.1:8080/{instance_name}/reset-password/{token}"
    
    print(f"\n=== PASSWORD RESET EMAIL ===")
    print(f"To: {email}")
    print(f"Subject: Password Reset Request")
    print(f"Reset Link: {reset_url}")
    print(f"=============================\n")
    
    # In production, replace this with actual email sending:
    # msg = MIMEMultipart()
    # msg['From'] = "noreply@lendingapp.com"
    # msg['To'] = email
    # msg['Subject'] = "Password Reset Request"
    # 
    # body = f"""
    # You requested a password reset for your account.
    # 
    # Click the link below to reset your password:
    # {reset_url}
    # 
    # This link will expire in 1 hour.
    # 
    # If you didn't request this, please ignore this email.
    # """
    # 
    # msg.attach(MIMEText(body, 'plain'))
    # 
    # server = smtplib.SMTP('smtp.gmail.com', 587)
    # server.starttls()
    # server.login("your-email@gmail.com", "your-password")
    # text = msg.as_string()
    # server.sendmail("noreply@lendingapp.com", email, text)
    # server.quit()

# Initialize the app only when run directly
if __name__ == '__main__':
    init_app()
    app.run(debug=True, port=8080)

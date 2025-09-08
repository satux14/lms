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

from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, g
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from datetime import datetime, date, timedelta
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import os
import uuid
from pathlib import Path

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-this-in-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lending_app.db'  # Default database
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login_redirect'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Models (same as original)
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(120), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

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
VALID_INSTANCES = ['prod', 'dev', 'testing']
DEFAULT_INSTANCE = 'prod'

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
    
    # Create instances directory
    instances_dir = Path("instances")
    instances_dir.mkdir(exist_ok=True)
    
    # Create instance directory
    instance_dir = instances_dir / instance
    instance_dir.mkdir(exist_ok=True)
    
    # Create database directory
    db_dir = instance_dir / "database"
    db_dir.mkdir(exist_ok=True)
    
    db_path = db_dir / f"lending_app_{instance}.db"
    return f"sqlite:///{db_path}"

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

# Initialize app
def init_app():
    """Initialize the application"""
    # Configure for default instance first
    configure_app_for_instance(DEFAULT_INSTANCE)
    
    # Create all instance directories and databases
    for instance in VALID_INSTANCES:
        configure_app_for_instance(instance)
        with app.app_context():
            db.create_all()
            create_default_data(instance)

def create_default_data(instance):
    """Create default data for instance"""
    # Create default admin user if it doesn't exist
    if not User.query.filter_by(username='admin').first():
        admin = User(
            username='admin',
            email=f'admin@{instance}.lendingapp.com',
            password_hash=generate_password_hash('admin123'),
            is_admin=True
        )
        db.session.add(admin)
        
        # Create default interest rate
        default_rate = InterestRate(rate=Decimal('0.21'))  # 21%
        db.session.add(default_rate)
        
        db.session.commit()
        print(f"Default admin user created for {instance}: username='admin', password='admin123'")

# Helper functions (same as original)
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
        
        # Calculate interest from loan creation to as_of_date
        total_interest = calculate_interest_for_period(
            loan.remaining_principal, 
            loan.interest_rate, 
            loan.created_at.date(), 
            as_of_date
        )
        
        # Subtract verified interest payments
        verified_interest_payments = db.session.query(db.func.sum(Payment.interest_amount)).filter_by(
            loan_id=loan.id, 
            status='verified'
        ).scalar() or 0
        
        return total_interest - Decimal(str(verified_interest_payments))
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
            
            if payment_amount > total_pending_interest:
                raise ValueError(f"Payment amount (₹{payment_amount}) exceeds pending interest (₹{total_pending_interest}) for interest-only loan")
            
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
        
        db.session.add(payment)
        db.session.commit()
        
        return payment
        
    except Exception as e:
        db.session.rollback()
        raise e

def verify_payment(payment_id):
    """Verify a payment and update loan balance"""
    try:
        payment = Payment.query.get_or_404(payment_id)
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
        
        db.session.commit()
        
    except Exception as e:
        db.session.rollback()
        raise e

# Routes
@app.before_request
def before_request():
    """Configure app for current instance before each request"""
    instance = get_current_instance()
    configure_app_for_instance(instance)
    g.current_instance = instance

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
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
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
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('register.html', instance_name=instance_name)
        
        user = User(
            username=username,
            email=email if email else None,
            password_hash=generate_password_hash(password),
            is_admin=False
        )
        
        db.session.add(user)
        db.session.commit()
        
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
    total_loans = Loan.query.count()
    total_principal = sum(loan.principal_amount for loan in Loan.query.all())
    total_interest_earned = sum(payment.interest_amount for payment in Payment.query.filter_by(status='verified').all())
    total_users = User.query.count()
    
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
    
    # Build query
    query = Loan.query
    
    if loan_type:
        query = query.filter(Loan.loan_type == loan_type)
    if frequency:
        query = query.filter(Loan.payment_frequency == frequency)
    if customer_id:
        query = query.filter(Loan.customer_id == customer_id)
    if loan_name:
        query = query.filter(Loan.loan_name.contains(loan_name))
    if min_rate:
        query = query.filter(Loan.interest_rate >= float(min_rate))
    if max_rate:
        query = query.filter(Loan.interest_rate <= float(max_rate))
    
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
    customers = User.query.filter_by(is_admin=False).all()
    
    return render_template('admin/loans.html', 
                         loans=loans, 
                         customers=customers,
                         loan_type=loan_type,
                         frequency=frequency,
                         customer_id=customer_id,
                         loan_name=loan_name,
                         min_rate=min_rate,
                         max_rate=max_rate,
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
    
    users = User.query.all()
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
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists')
            return render_template('admin/create_user.html', instance_name=instance_name)
        
        user = User(
            username=username,
            email=email if email else None,
            password_hash=generate_password_hash(password),
            is_admin=is_admin
        )
        db.session.add(user)
        db.session.commit()
        
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
        principal_amount = Decimal(request.form['principal_amount'])
        interest_rate = Decimal(request.form['interest_rate'])
        payment_frequency = request.form['payment_frequency']
        loan_type = request.form['loan_type']
        admin_notes = request.form.get('admin_notes', '')
        customer_notes = request.form.get('customer_notes', '')
        custom_created_at = request.form.get('custom_created_at')
        
        # Parse custom creation date if provided
        if custom_created_at:
            try:
                created_at = datetime.strptime(custom_created_at, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format')
                return render_template('admin/create_loan.html', 
                                     customers=User.query.filter_by(is_admin=False).all(),
                                     instance_name=instance_name)
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
        db.session.add(loan)
        db.session.commit()
        
        flash('Loan created successfully')
        return redirect(url_for('admin_loans', instance_name=instance_name))
    
    customers = User.query.filter_by(is_admin=False).all()
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
    query = db.session.query(Payment, Loan, User).join(Loan, Payment.loan_id == Loan.id).join(User, Loan.customer_id == User.id)
    
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
    
    # Calculate total interest paid
    total_interest_paid = db.session.query(db.func.sum(Payment.interest_amount)).scalar() or 0
    
    # Get unique customers and loans for filters
    customers = User.query.filter_by(is_admin=False).all()
    loans = Loan.query.all()
    
    # Handle Excel export
    if request.args.get('export') == 'excel':
        from backup import BackupManager
        backup_manager = BackupManager(instance_name)
        return backup_manager.export_to_excel()
    
    return render_template('admin/payments.html', 
                         payments=payments,
                         total_interest_paid=total_interest_paid,
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
                                     loans=Loan.query.all(),
                                     selected_loan_id=loan_id,
                                     instance_name=instance_name)
        else:
            payment_date = datetime.utcnow()
        
        loan = Loan.query.get(loan_id)
        if not loan:
            flash('Loan not found')
            return redirect(url_for('admin_payments', instance_name=instance_name))
        
        # Process payment similar to customer payment
        payment = Payment(
            loan_id=loan_id,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            payment_date=payment_date,
            status='pending'  # All payments start as pending
        )
        db.session.add(payment)
        db.session.commit()
        
        flash('Payment added successfully. It will be verified by admin.')
        return redirect(url_for('admin_payments', instance_name=instance_name))
    
    loans = Loan.query.all()
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
    
    from backup import BackupManager
    backup_manager = BackupManager(instance_name)
    backup_info = backup_manager.get_backup_info()
    
    # Calculate total size in MB
    if backup_info and 'total_size' in backup_info:
        total_size_mb = backup_info['total_size'] / (1024 * 1024)
    else:
        total_size_mb = 0
    
    return render_template('admin/backup.html', 
                         backup_info=backup_info,
                         total_size_mb=total_size_mb,
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
    
    loan = Loan.query.get_or_404(loan_id)
    
    if request.method == 'POST':
        loan.loan_name = request.form['loan_name']
        loan.principal_amount = Decimal(request.form['principal_amount'])
        loan.remaining_principal = Decimal(request.form['remaining_principal'])
        loan.interest_rate = Decimal(request.form['interest_rate'])
        loan.payment_frequency = request.form['payment_frequency']
        loan.loan_type = request.form['loan_type']
        loan.admin_notes = request.form.get('admin_notes', '')
        loan.customer_notes = request.form.get('customer_notes', '')
        
        db.session.commit()
        flash('Loan updated successfully')
        return redirect(url_for('admin_loans', instance_name=instance_name))
    
    # Get payment history for this loan
    payments = Payment.query.filter_by(loan_id=loan_id).order_by(Payment.payment_date.desc()).all()
    
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
    
    loan = Loan.query.get_or_404(loan_id)
    
    # Calculate interest information
    daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
    monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
    accumulated_interest = calculate_accumulated_interest(loan)
    
    # Get payment history
    payments = Payment.query.filter_by(loan_id=loan_id).order_by(Payment.payment_date.desc()).all()
    
    # Calculate days active
    days_active = (date.today() - loan.created_at.date()).days
    
    return render_template('admin/view_loan.html', 
                         loan=loan,
                         daily_interest=daily_interest,
                         monthly_interest=monthly_interest,
                         accumulated_interest=accumulated_interest,
                         payments=payments,
                         days_active=days_active,
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
    
    payment = Payment.query.get_or_404(payment_id)
    
    if request.method == 'POST':
        payment.amount = Decimal(request.form['amount'])
        payment.payment_method = request.form['payment_method']
        payment.transaction_id = request.form.get('transaction_id', '')
        payment.status = request.form['payment_status']
        
        # Parse payment date
        payment_date_str = request.form.get('payment_date')
        if payment_date_str:
            try:
                payment.payment_date = datetime.strptime(payment_date_str, '%Y-%m-%dT%H:%M')
            except ValueError:
                flash('Invalid date format')
                return render_template('admin/edit_payment.html', 
                                     payment=payment,
                                     instance_name=instance_name)
        
        db.session.commit()
        flash('Payment updated successfully')
        return redirect(url_for('admin_payments', instance_name=instance_name))
    
    return render_template('admin/edit_payment.html', 
                         payment=payment,
                         instance_name=instance_name)

# Admin Create Backup route
@app.route('/<instance_name>/admin/backup/create')
@login_required
def admin_create_backup(instance_name):
    """Admin create backup for specific instance"""
    if instance_name not in VALID_INSTANCES:
        return redirect('/')
    
    if not current_user.is_admin:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    from backup import BackupManager
    backup_manager = BackupManager(instance_name)
    
    try:
        backup_manager.create_full_backup()
        flash('Backup created successfully')
    except Exception as e:
        flash(f'Backup failed: {str(e)}')
    
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
    
    from backup import BackupManager
    backup_manager = BackupManager(instance_name)
    
    try:
        days = int(request.form.get('days', 30))
        backup_manager.cleanup_old_backups(days)
        flash(f'Cleaned up backups older than {days} days')
    except Exception as e:
        flash(f'Cleanup failed: {str(e)}')
    
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
    
    from backup import BackupManager
    backup_manager = BackupManager(instance_name)
    
    try:
        return backup_manager.download_backup(filename)
    except Exception as e:
        flash(f'Download failed: {str(e)}')
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
    loans = Loan.query.filter_by(customer_id=current_user.id).all()
    
    loan_data = []
    for loan in loans:
        daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
        monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
        accumulated_interest = calculate_accumulated_interest(loan)
        
        # Calculate pending payments for this specific loan
        pending_payments = Payment.query.filter_by(loan_id=loan.id, status='pending').all()
        pending_principal = sum(payment.principal_amount for payment in pending_payments)
        pending_interest = sum(payment.interest_amount for payment in pending_payments)
        pending_total = sum(payment.amount for payment in pending_payments)
        
        # Calculate verified payments for this specific loan
        verified_payments = Payment.query.filter_by(loan_id=loan.id, status='verified').all()
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
    
    loan = Loan.query.get_or_404(loan_id)
    
    # Check if loan belongs to current user
    if loan.customer_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    # Calculate interest information
    daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
    monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
    accumulated_interest = calculate_accumulated_interest(loan)
    
    # Get payment history
    payments = Payment.query.filter_by(loan_id=loan_id).order_by(Payment.payment_date.desc()).all()
    
    # Calculate days active
    days_active = (date.today() - loan.created_at.date()).days
    
    return render_template('customer/loan_detail.html', 
                         loan=loan,
                         daily_interest=daily_interest,
                         monthly_interest=monthly_interest,
                         accumulated_interest=accumulated_interest,
                         payments=payments,
                         days_active=days_active,
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
    
    loan = Loan.query.get_or_404(loan_id)
    
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
        
        # Process payment
        payment = Payment(
            loan_id=loan_id,
            amount=amount,
            payment_method=payment_method,
            transaction_id=transaction_id,
            payment_date=payment_date,
            status='pending'  # All payments start as pending
        )
        db.session.add(payment)
        db.session.commit()
        
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
    
    loan = Loan.query.get_or_404(loan_id)
    
    # Check if loan belongs to current user
    if loan.customer_id != current_user.id:
        flash('Access denied')
        return redirect(url_for('customer_dashboard', instance_name=instance_name))
    
    if request.method == 'POST':
        customer_notes = request.form.get('customer_notes', '')
        loan.customer_notes = customer_notes
        db.session.commit()
        
        flash('Notes updated successfully')
        return redirect(url_for('customer_loan_detail', instance_name=instance_name, loan_id=loan_id))
    
    return render_template('customer/edit_notes.html', 
                         loan=loan,
                         instance_name=instance_name)

# Initialize the app only when run directly
if __name__ == '__main__':
    init_app()
    app.run(debug=True, port=8080)

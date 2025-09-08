"""
Application Factory for Multi-Instance Lending Management System
==============================================================

This module creates Flask applications for different instances (prod, dev, testing).
Each instance has its own database and configuration.

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
from instance_manager import InstanceManager

# Global objects
db = SQLAlchemy()
login_manager = LoginManager()

# Database Models (same as original app.py)
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

def create_app(instance_name='prod'):
    """Create Flask application for specific instance"""
    
    app = Flask(__name__)
    
    # Initialize instance manager
    instance_manager = InstanceManager(app)
    
    # Configure app based on instance
    app.config['SECRET_KEY'] = f'your-secret-key-change-this-in-production-{instance_name}'
    app.config['SQLALCHEMY_DATABASE_URI'] = instance_manager.get_database_uri(instance_name)
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # File upload configuration
    app.config['UPLOAD_FOLDER'] = instance_manager.get_uploads_folder(instance_name)
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    
    # Create upload directory if it doesn't exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    
    # Store instance info in app config
    app.config['INSTANCE_NAME'] = instance_name
    app.config['INSTANCE_MANAGER'] = instance_manager
    
    # Register blueprints and routes
    register_routes(app, instance_manager)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        create_default_data(app, instance_name)
    
    return app

def register_routes(app, instance_manager):
    """Register all routes for the application"""
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Helper functions (same as original app.py)
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
    @app.route('/')
    def index():
        """Redirect to login"""
        return redirect(url_for('login'))
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """User login"""
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            user = User.query.filter_by(username=username).first()
            
            if user and check_password_hash(user.password_hash, password):
                login_user(user)
                next_page = request.args.get('next')
                if user.is_admin:
                    return redirect(next_page) if next_page else redirect(url_for('admin_dashboard'))
                else:
                    return redirect(next_page) if next_page else redirect(url_for('customer_dashboard'))
            else:
                flash('Invalid username or password')
        
        instance_name = app.config['INSTANCE_NAME']
        return render_template('login.html', instance_name=instance_name)
    
    @app.route('/logout')
    @login_required
    def logout():
        """User logout"""
        logout_user()
        return redirect(url_for('login'))
    
    @app.route('/register', methods=['GET', 'POST'])
    def register():
        """User registration"""
        if request.method == 'POST':
            username = request.form['username']
            email = request.form.get('email', '')  # Email is optional
            password = request.form['password']
            
            if User.query.filter_by(username=username).first():
                flash('Username already exists')
                return render_template('register.html')
            
            user = User(
                username=username,
                email=email if email else None,
                password_hash=generate_password_hash(password),
                is_admin=False
            )
            
            db.session.add(user)
            db.session.commit()
            
            flash('Registration successful! Please login.')
            return redirect(url_for('login'))
        
        instance_name = app.config['INSTANCE_NAME']
        return render_template('register.html', instance_name=instance_name)
    
    # Admin routes
    @app.route('/admin')
    @login_required
    def admin_dashboard():
        """Admin dashboard"""
        if not current_user.is_admin:
            flash('Access denied')
            return redirect(url_for('customer_dashboard'))
        
        # Get statistics
        total_loans = Loan.query.count()
        total_principal = sum(loan.principal_amount for loan in Loan.query.all())
        total_interest_earned = sum(payment.interest_amount for payment in Payment.query.filter_by(status='verified').all())
        total_users = User.query.count()
        
        instance_name = app.config['INSTANCE_NAME']
        return render_template('admin/dashboard.html', 
                             total_loans=total_loans,
                             total_principal=total_principal,
                             total_interest_earned=total_interest_earned,
                             total_users=total_users,
                             instance_name=instance_name)
    
    # Customer routes
    @app.route('/customer')
    @login_required
    def customer_dashboard():
        """Customer dashboard"""
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard'))
        
        # Get customer's loans
        loans = Loan.query.filter_by(customer_id=current_user.id).all()
        
        loan_data = []
        for loan in loans:
            daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
            monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
            accumulated_interest = calculate_accumulated_interest(loan)
            
            loan_data.append({
                'loan': loan,
                'daily_interest': daily_interest,
                'monthly_interest': monthly_interest,
                'accumulated_interest': accumulated_interest
            })
        
        # Calculate pending payments
        pending_payments = Payment.query.join(Loan).filter(
            Loan.customer_id == current_user.id,
            Payment.status == 'pending'
        ).all()
        
        pending_principal = sum(payment.principal_amount for payment in pending_payments)
        pending_interest = sum(payment.interest_amount for payment in pending_payments)
        pending_total = sum(payment.amount for payment in pending_payments)
        
        instance_name = app.config['INSTANCE_NAME']
        return render_template('customer/dashboard.html',
                             loan_data=loan_data,
                             pending_payments=pending_payments,
                             pending_principal=pending_principal,
                             pending_interest=pending_interest,
                             pending_total=pending_total,
                             instance_name=instance_name)
    
    # Add more routes as needed...
    # (This is a simplified version - you would include all the routes from the original app.py)

def create_default_data(app, instance_name):
    """Create default data for the instance"""
    with app.app_context():
        # Create default admin user if it doesn't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(
                username='admin',
                email=f'admin@{instance_name}.lendingapp.com',
                password_hash=generate_password_hash('admin123'),
                is_admin=True
            )
            db.session.add(admin)
            
            # Create default interest rate
            default_rate = InterestRate(rate=Decimal('0.21'))  # 21%
            db.session.add(default_rate)
            
            db.session.commit()
            print(f"Default admin user created for {instance_name}: username='admin', password='admin123'")

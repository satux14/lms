"""
Payment Processing Module
=========================

This module handles all payment-related functionality including:
- Payment processing
- Razorpay integration
- Payment routes
"""

from flask import request, redirect, url_for, flash, jsonify, render_template, abort, g
from flask_login import login_required, current_user
from datetime import datetime
from decimal import Decimal
import hmac
import hashlib
import json
import uuid

# Import from app_multi - these will be set when register_payment_routes is called
app = None
db = None
razorpay_client = None

# These will be imported from app_multi
VALID_INSTANCES = None
Payment = None
Loan = None
get_payment_query = None
get_loan_query = None
add_to_current_instance = None
commit_current_instance = None
calculate_accumulated_interest = None
calculate_daily_interest = None
calculate_monthly_interest = None
verify_payment = None


def register_payment_routes(flask_app, flask_db, valid_instances, 
                           payment_model, loan_model, payment_query_func, loan_query_func,
                           add_instance_func, commit_instance_func, verify_payment_func,
                           calc_accumulated_func, calc_daily_func, calc_monthly_func):
    """Register payment routes with Flask app"""
    global app, db, VALID_INSTANCES
    global Payment, Loan, get_payment_query, get_loan_query
    global add_to_current_instance, commit_current_instance, verify_payment
    global calculate_accumulated_interest, calculate_daily_interest, calculate_monthly_interest
    
    app = flask_app
    db = flask_db
    VALID_INSTANCES = valid_instances
    Payment = payment_model
    Loan = loan_model
    get_payment_query = payment_query_func
    get_loan_query = loan_query_func
    add_to_current_instance = add_instance_func
    commit_current_instance = commit_instance_func
    verify_payment = verify_payment_func
    calculate_accumulated_interest = calc_accumulated_func
    calculate_daily_interest = calc_daily_func
    calculate_monthly_interest = calc_monthly_func
    
    # Register routes
    register_routes()


def register_routes():
    """Register all payment routes"""
    
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
        interest_data = calculate_accumulated_interest(loan)
        accumulated_interest_daily = interest_data['daily']
        accumulated_interest_monthly = interest_data['monthly']
        
        # Get payment history
        payments = get_payment_query().filter_by(loan_id=loan_id).order_by(Payment.payment_date.desc()).all()
        
        # Calculate total interest paid for this loan
        total_interest_paid = sum(payment.interest_amount for payment in payments if payment.status == 'verified')
        
        # Calculate verified principal paid for this loan
        verified_principal = sum(payment.principal_amount for payment in payments if payment.status == 'verified')
        
        # Calculate pending amounts for this loan
        pending_principal = sum(payment.principal_amount for payment in payments if payment.status == 'pending')
        pending_interest = sum(payment.interest_amount for payment in payments if payment.status == 'pending')
        
        return render_template('customer/loan_detail.html',
                             loan=loan,
                             daily_interest=daily_interest,
                             monthly_interest=monthly_interest,
                             accumulated_interest_daily=accumulated_interest_daily,
                             accumulated_interest_monthly=accumulated_interest_monthly,
                             payments=payments,
                             total_interest_paid=total_interest_paid,
                             verified_principal=verified_principal,
                             pending_principal=pending_principal,
                             pending_interest=pending_interest,
                             instance_name=instance_name)

    @app.route('/<instance_name>/customer/loan/<int:loan_id>/gpay/initiate', methods=['POST'])
    @login_required
    def gpay_initiate_payment(instance_name, loan_id):
        """Initiate Google Pay UPI payment - returns payment request configuration"""
        if instance_name not in VALID_INSTANCES:
            return jsonify({'error': 'Invalid instance'}), 400
        
        merchant_vpa = app.config.get('GOOGLE_PAY_MERCHANT_VPA', '')
        if not merchant_vpa:
            return jsonify({'error': 'Google Pay not configured'}), 500
        
        loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
        
        # Check loan ownership
        if loan.customer_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            amount = Decimal(request.json.get('amount', 0))
            
            if amount <= 0:
                return jsonify({'error': 'Invalid amount'}), 400
            
            # Validate amount based on loan type
            if loan.loan_type == 'interest_only':
                interest_data = calculate_accumulated_interest(loan)
                max_amount = interest_data['daily']
                if amount > max_amount + Decimal('0.01'):
                    return jsonify({'error': f'Amount exceeds pending interest (₹{max_amount:.2f})'}), 400
            else:
                if amount > loan.remaining_principal:
                    return jsonify({'error': f'Amount exceeds remaining principal (₹{loan.remaining_principal:.2f})'}), 400
            
            # Generate unique transaction reference ID
            transaction_ref = f'LOAN{loan_id}_{uuid.uuid4().hex[:8].upper()}'
            
            # Create callback URL for payment verification
            callback_url = app.config.get('GOOGLE_PAY_CALLBACK_URL', '')
            if not callback_url:
                callback_url = request.url_root.rstrip('/') + f'/{instance_name}/customer/loan/{loan_id}/gpay/callback'
            
            # Return Google Pay UPI configuration
            return jsonify({
                'merchant_vpa': merchant_vpa,
                'merchant_name': app.config.get('GOOGLE_PAY_MERCHANT_NAME', 'The SRS Consulting'),
                'merchant_code': app.config.get('GOOGLE_PAY_MERCHANT_CODE', '0000'),
                'transaction_ref': transaction_ref,
                'amount': str(amount),
                'currency': 'INR',
                'callback_url': callback_url,
                'loan_id': loan_id,
                'loan_name': loan.loan_name
            })
            
        except Exception as e:
            print(f"Error initiating Google Pay payment: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/<instance_name>/customer/loan/<int:loan_id>/gpay/callback', methods=['POST', 'GET'])
    @login_required
    def gpay_payment_callback(instance_name, loan_id):
        """Handle Google Pay UPI payment callback/verification"""
        if instance_name not in VALID_INSTANCES:
            return jsonify({'error': 'Invalid instance'}), 400
        
        loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
        
        # Check loan ownership
        if loan.customer_id != current_user.id:
            return jsonify({'error': 'Access denied'}), 403
        
        try:
            # Get payment details from request
            transaction_ref = request.args.get('tr') or request.form.get('tr') or request.json.get('tr') if request.is_json else None
            upi_transaction_id = request.args.get('txnId') or request.form.get('txnId') or (request.json.get('txnId') if request.is_json else None)
            amount_str = request.args.get('am') or request.form.get('am') or (request.json.get('am') if request.is_json else None)
            status = request.args.get('status') or request.form.get('status') or (request.json.get('status') if request.is_json else None)
            
            if not transaction_ref or not upi_transaction_id:
                return jsonify({'error': 'Missing transaction details'}), 400
            
            # Check if payment already exists
            existing_payment = get_payment_query().filter_by(
                transaction_id=upi_transaction_id
            ).first()
            
            if existing_payment:
                return jsonify({
                    'status': 'already_processed',
                    'payment_id': existing_payment.id
                }), 200
            
            # If status indicates success, create payment entry
            if status == 'SUCCESS' or status == 'success':
                amount = Decimal(amount_str) if amount_str else None
                if not amount:
                    return jsonify({'error': 'Amount not provided'}), 400
                
                # Create payment entry (status will be verified after manual/admin verification)
                payment = process_payment(
                    loan=loan,
                    payment_amount=amount,
                    payment_date=datetime.utcnow(),
                    transaction_id=upi_transaction_id,
                    payment_method='gpay',
                    razorpay_order_id=transaction_ref
                )
                
                return jsonify({
                    'status': 'success',
                    'payment_id': payment.id,
                    'message': 'Payment received. It will be verified shortly.'
                }), 200
            else:
                return jsonify({
                    'status': 'failed',
                    'message': 'Payment was not successful'
                }), 400
            
        except Exception as e:
            print(f"Error processing Google Pay callback: {e}")
            return jsonify({'error': str(e)}), 500

    # Razorpay webhook removed - using direct Google Pay UPI integration
    # @app.route('/<instance_name>/razorpay/webhook', methods=['POST'])
    def _deprecated_razorpay_webhook(instance_name):
        """Handle Razorpay webhook events"""
        if instance_name not in VALID_INSTANCES:
            return jsonify({'error': 'Invalid instance'}), 400
        
        try:
            # Get webhook payload and signature
            payload = request.data.decode('utf-8')
            signature = request.headers.get('X-Razorpay-Signature', '')
            
            # Verify webhook signature
            if not verify_razorpay_webhook_signature(payload, signature):
                print("⚠️  Invalid webhook signature")
                return jsonify({'error': 'Invalid signature'}), 400
            
            # Parse webhook payload
            webhook_data = json.loads(payload)
            event = webhook_data.get('event')
            
            # Handle payment.captured event
            if event == 'payment.captured':
                payment_data = webhook_data.get('payload', {}).get('payment', {}).get('entity', {})
                order_data = webhook_data.get('payload', {}).get('order', {}).get('entity', {})
                
                payment_id = payment_data.get('id')
                order_id = order_data.get('id')
                amount = Decimal(payment_data.get('amount', 0)) / 100  # Convert from paise
                order_amount = Decimal(order_data.get('amount', 0)) / 100  # Convert from paise
                signature_payment = payment_data.get('signature', '')
                
                # Validate payment amount matches order amount
                if abs(amount - order_amount) > Decimal('0.01'):  # Allow small rounding differences
                    print(f"⚠️  Amount mismatch: payment={amount}, order={order_amount}")
                    return jsonify({'error': 'Amount mismatch'}), 400
                
                # Get loan from order notes
                notes = order_data.get('notes', {})
                loan_id = notes.get('loan_id')
                
                if not loan_id:
                    print("⚠️  No loan_id in order notes")
                    return jsonify({'error': 'Invalid order'}), 400
                
                # Get loan
                loan = get_loan_query().filter_by(id=loan_id).first()
                if not loan:
                    print(f"⚠️  Loan {loan_id} not found")
                    return jsonify({'error': 'Loan not found'}), 404
                
                # Check if payment already processed
                existing_payment = get_payment_query().filter_by(razorpay_payment_id=payment_id).first()
                if existing_payment:
                    print(f"⚠️  Payment {payment_id} already processed")
                    return jsonify({'status': 'already_processed'}), 200
                
                # Validate amount against loan constraints
                try:
                    if loan.loan_type == 'interest_only':
                        interest_data = calculate_accumulated_interest(loan)
                        max_amount = interest_data['daily']
                        if amount > max_amount + Decimal('0.01'):
                            print(f"⚠️  Amount {amount} exceeds pending interest {max_amount}")
                            return jsonify({'error': 'Amount exceeds pending interest'}), 400
                    else:
                        if amount > loan.remaining_principal + Decimal('0.01'):
                            print(f"⚠️  Amount {amount} exceeds remaining principal {loan.remaining_principal}")
                            return jsonify({'error': 'Amount exceeds remaining principal'}), 400
                except Exception as e:
                    print(f"⚠️  Error validating amount: {e}")
                    return jsonify({'error': 'Amount validation failed'}), 400
                
                # Process payment
                try:
                    payment = process_razorpay_payment(
                        loan=loan,
                        payment_amount=amount,
                        razorpay_order_id=order_id,
                        razorpay_payment_id=payment_id,
                        razorpay_signature=signature_payment
                    )
                    print(f"✅ Payment {payment_id} processed successfully for loan {loan_id}")
                    return jsonify({'status': 'success', 'payment_id': payment.id}), 200
                except Exception as e:
                    print(f"❌ Error processing payment: {e}")
                    return jsonify({'error': str(e)}), 500
            
            # Return success for other events (we only care about payment.captured)
            return jsonify({'status': 'ignored'}), 200
            
        except Exception as e:
            print(f"❌ Webhook error: {e}")
            return jsonify({'error': str(e)}), 500

    @app.route('/<instance_name>/customer/payment/manual')
    @login_required
    def customer_manual_payment(instance_name):
        """Manual payment entry page for failed/cancelled payments"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard', instance_name=instance_name))
        
        loan_id = request.args.get('loan_id', type=int)
        if not loan_id:
            flash('Invalid loan ID')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
        
        # Check loan ownership
        if loan.customer_id != current_user.id:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        # Calculate interest information
        daily_interest = calculate_daily_interest(loan.remaining_principal, loan.interest_rate)
        monthly_interest = calculate_monthly_interest(loan.remaining_principal, loan.interest_rate)
        interest_data = calculate_accumulated_interest(loan)
        accumulated_interest_daily = interest_data['daily']
        accumulated_interest_monthly = interest_data['monthly']
        
        return render_template('customer/manual_payment.html',
                             loan=loan,
                             daily_interest=daily_interest,
                             monthly_interest=monthly_interest,
                             accumulated_interest_daily=accumulated_interest_daily,
                             accumulated_interest_monthly=accumulated_interest_monthly,
                             instance_name=instance_name)

    @app.route('/<instance_name>/customer/payment/success')
    @login_required
    def customer_payment_success(instance_name):
        """Payment success confirmation page"""
        if instance_name not in VALID_INSTANCES:
            return redirect('/')
        
        if current_user.is_admin:
            return redirect(url_for('admin_dashboard', instance_name=instance_name))
        
        payment_id = request.args.get('payment_id')
        transaction_ref = request.args.get('transaction_ref')
        order_id = request.args.get('order_id')
        signature = request.args.get('signature')
        loan_id = request.args.get('loan_id', type=int)
        
        payment = None
        
        # Try to find payment by transaction reference (Google Pay)
        if transaction_ref:
            payment = get_payment_query().filter_by(razorpay_order_id=transaction_ref).first()
        
        # Try to find payment by Razorpay payment ID (backward compatibility)
        if not payment and payment_id:
            payment = get_payment_query().filter_by(razorpay_payment_id=payment_id).first()
        
        # If not found, try order ID
        if not payment and order_id:
            payment = get_payment_query().filter_by(razorpay_order_id=order_id).first()
        
        # Get loan ID from payment or request
        if payment:
            loan_id = payment.loan_id
        elif not loan_id:
            flash('Invalid payment information')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        loan = get_loan_query().filter_by(id=loan_id).first() or abort(404)
        
        # Check loan ownership
        if loan.customer_id != current_user.id:
            flash('Access denied')
            return redirect(url_for('customer_dashboard', instance_name=instance_name))
        
        return render_template('customer/payment_success.html',
                             payment=payment,
                             loan_id=loan_id,
                             instance_name=instance_name)


def process_payment(loan, payment_amount, payment_date=None, transaction_id=None, 
                   payment_method=None, proof_filename=None, razorpay_order_id=None,
                   razorpay_payment_id=None, razorpay_signature=None, payment_initiated_at=None):
    """Process a payment for a loan"""
    try:
        if payment_date is None:
            payment_date = datetime.utcnow()
        
        payment_amount = Decimal(str(payment_amount))
        
        if loan.loan_type == 'interest_only':
            # For interest-only loans, calculate total pending interest
            interest_data = calculate_accumulated_interest(loan, payment_date.date())
            accumulated_interest = interest_data['daily']  # Use daily calculation for interest-only loans
            
            # Get total pending interest from all pending payments
            pending_interest = get_payment_query().with_entities(db.func.sum(Payment.interest_amount)).filter_by(
                loan_id=loan.id, 
                status='pending'
            ).scalar() or 0
            pending_interest = Decimal(str(pending_interest))
            
            total_pending_interest = accumulated_interest + pending_interest
            
            # Allow small rounding differences (within 0.01)
            if payment_amount > total_pending_interest + Decimal('0.01'):
                raise ValueError(f"Payment amount (₹{payment_amount}) exceeds pending interest (₹{total_pending_interest:.2f}) for interest-only loan. Maximum allowed: ₹{total_pending_interest:.2f}")
            
            # All payment goes to interest
            interest_amount = payment_amount
            principal_amount = Decimal('0')
        else:
            # For regular loans, calculate accumulated interest first
            interest_data = calculate_accumulated_interest(loan, payment_date.date())
            accumulated_interest = interest_data['daily']  # Use daily calculation for payment processing
            
            if payment_amount >= accumulated_interest:
                # Payment covers all accumulated interest, remainder goes to principal
                interest_amount = accumulated_interest
                principal_amount = payment_amount - accumulated_interest
            else:
                # Payment only covers part of accumulated interest
                interest_amount = payment_amount
                principal_amount = Decimal('0')
        
        # Determine payment type
        if loan.loan_type == 'interest_only':
            payment_type = 'interest'
        elif principal_amount > 0:
            payment_type = 'both'
        else:
            payment_type = 'interest'
        
        # Create payment record
        payment = Payment(
            loan_id=loan.id,
            amount=payment_amount,
            payment_date=payment_date,
            payment_type=payment_type,
            interest_amount=interest_amount,
            principal_amount=principal_amount,
            transaction_id=transaction_id,
            payment_method=payment_method,
            proof_filename=proof_filename,
            status='pending',  # All payments start as pending
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            payment_initiated_at=payment_initiated_at
        )
        
        add_to_current_instance(payment)
        
        # Log payment creation
        try:
            from flask import g
            instance_name = getattr(g, 'current_instance', 'prod')
            from lms_logging import get_logging_manager
            from lms_metrics import get_metrics_manager
            
            username = None
            try:
                from flask_login import current_user
                if hasattr(current_user, 'username'):
                    username = current_user.username
            except:
                pass
            
            logging_mgr = get_logging_manager(instance_name)
            metrics_mgr = get_metrics_manager(instance_name)
            
            logging_mgr.log_payment('add_payment', loan.id, payment.id, payment_amount, username)
            metrics_mgr.record_payment(username or 'anonymous', float(payment_amount), status='pending')
        except Exception as log_error:
            # Don't fail payment if logging fails
            print(f"[ERROR] Failed to log payment: {log_error}")
        
        return payment
        
    except Exception as e:
        # Rollback is handled by the instance-specific session
        raise e


def verify_razorpay_signature(order_id, payment_id, signature):
    """Verify Razorpay payment signature"""
    if not app.config['RAZORPAY_KEY_SECRET']:
        return False
    
    message = f"{order_id}|{payment_id}"
    generated_signature = hmac.new(
        app.config['RAZORPAY_KEY_SECRET'].encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(generated_signature, signature)


def verify_razorpay_webhook_signature(payload, signature):
    """Verify Razorpay webhook signature"""
    if not app.config['RAZORPAY_WEBHOOK_SECRET']:
        return False
    
    generated_signature = hmac.new(
        app.config['RAZORPAY_WEBHOOK_SECRET'].encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(generated_signature, signature)


def process_razorpay_payment(loan, payment_amount, razorpay_order_id, razorpay_payment_id, razorpay_signature, payment_date=None):
    """Process Razorpay payment from webhook - creates verified payment entry"""
    try:
        # Verify signature
        if not verify_razorpay_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
            raise ValueError("Invalid payment signature")
        
        # Check if payment already exists
        existing_payment = get_payment_query().filter_by(
            razorpay_payment_id=razorpay_payment_id
        ).first()
        
        if existing_payment:
            raise ValueError("Payment already processed")
        
        if payment_date is None:
            payment_date = datetime.utcnow()
        
        payment_amount = Decimal(str(payment_amount))
        
        # Calculate interest and principal amounts
        if loan.loan_type == 'interest_only':
            interest_data = calculate_accumulated_interest(loan, payment_date.date())
            accumulated_interest = interest_data['daily']
            
            pending_interest = get_payment_query().with_entities(db.func.sum(Payment.interest_amount)).filter_by(
                loan_id=loan.id, 
                status='pending'
            ).scalar() or 0
            pending_interest = Decimal(str(pending_interest))
            
            total_pending_interest = accumulated_interest + pending_interest
            
            if payment_amount > total_pending_interest + Decimal('0.01'):
                raise ValueError(f"Payment amount exceeds pending interest")
            
            interest_amount = payment_amount
            principal_amount = Decimal('0')
            payment_type = 'interest'
        else:
            interest_data = calculate_accumulated_interest(loan, payment_date.date())
            accumulated_interest = interest_data['daily']
            
            if payment_amount >= accumulated_interest:
                interest_amount = accumulated_interest
                principal_amount = payment_amount - accumulated_interest
            else:
                interest_amount = payment_amount
                principal_amount = Decimal('0')
            
            if principal_amount > 0:
                payment_type = 'both'
            else:
                payment_type = 'interest'
        
        # Create payment record with verified status
        payment = Payment(
            loan_id=loan.id,
            amount=payment_amount,
            payment_date=payment_date,
            payment_type=payment_type,
            interest_amount=interest_amount,
            principal_amount=principal_amount,
            transaction_id=razorpay_payment_id,
            payment_method='gpay',
            proof_filename=None,
            status='verified',  # Razorpay payments are auto-verified
            razorpay_order_id=razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
            payment_initiated_at=None
        )
        
        add_to_current_instance(payment)
        
        # Immediately verify payment to update loan balance
        commit_current_instance()
        verify_payment(payment.id)
        
        return payment
        
    except Exception as e:
        raise e


# 🏦 Lending Management System

A comprehensive web application for managing loans, payments, and customer accounts for small lending firms.

## 🚀 Features

### Admin Features
- **Dashboard**: Overview of all loans, payments, and customers
- **Loan Management**: Create, edit, and manage loans with custom interest rates
- **Payment Management**: View, verify, and manage all payments
- **User Management**: Create and manage customer and admin accounts
- **Advanced Filtering**: Filter loans by type, frequency, customer, status, name, and interest rate range
- **Sorting**: Sort loans by any column (ID, name, customer, type, principal, remaining, interest rate, frequency, created date)
- **Excel Export**: Export payment data to Excel files
- **Interest Rate Management**: Set custom interest rates per loan

### Customer Features
- **Dashboard**: View all personal loans and payment status
- **Loan Details**: Detailed view of individual loans with payment history
- **Payment Processing**: Make payments with proof upload and transaction tracking
- **Payment Methods**: Support for Cash, GPay, UPI, PhonePe
- **Notes Management**: Add and edit personal loan notes
- **Payment History**: Complete transaction history with status tracking

### Loan Types
- **Regular Loans**: Customers can pay both interest and principal
- **Interest-Only Loans**: Customers can only pay interest, principal remains fixed

### Payment Features
- **Verification Workflow**: All payments require admin verification
- **Proof Upload**: JPEG attachment support for payment proof
- **Transaction Tracking**: Transaction ID field for payment tracking
- **Payment Status**: Pending, Verified, Rejected status tracking
- **Date/Time Picker**: Backdate payments for historical entries

## 🛠️ Technology Stack

- **Backend**: Flask (Python)
- **Database**: SQLite with SQLAlchemy ORM
- **Frontend**: Bootstrap 5, HTML5, CSS3, JavaScript
- **Authentication**: Flask-Login with password hashing
- **File Handling**: Werkzeug secure file uploads
- **Excel Export**: openpyxl library
- **Currency**: Indian Rupees (₹) support

## 📋 Requirements

- Python 3.7+
- Flask
- SQLAlchemy
- Flask-Login
- Werkzeug
- openpyxl

## 🚀 Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd lending_app
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize database**
   ```bash
   python3 demo.py
   ```

5. **Run the application**
   ```bash
   python3 run.py
   ```

6. **Access the application**
   - Open browser and go to: `http://localhost:8080`
   - Default admin login:
     - Username: `admin`
     - Password: `admin123`

## 📁 Project Structure

```
lending_app/
├── app.py                 # Main Flask application
├── run.py                 # Application runner
├── demo.py                # Database initialization and sample data
├── requirements.txt       # Python dependencies
├── README.md             # This file
├── .gitignore            # Git ignore rules
├── templates/            # HTML templates
│   ├── base.html         # Base template
│   ├── admin/            # Admin templates
│   │   ├── dashboard.html
│   │   ├── loans.html
│   │   ├── payments.html
│   │   ├── create_loan.html
│   │   ├── edit_loan.html
│   │   ├── add_payment.html
│   │   ├── edit_payment.html
│   │   ├── users.html
│   │   ├── create_user.html
│   │   └── interest_rate.html
│   ├── customer/         # Customer templates
│   │   ├── dashboard.html
│   │   └── loan_detail.html
│   ├── login.html        # Login page
│   └── register.html     # Registration page
├── static/               # Static files (CSS, JS, images)
└── uploads/              # File uploads directory
```

## 🔧 Configuration

### Database
- Default: SQLite database (`lending_app.db`)
- Location: Project root directory
- Auto-created on first run

### File Uploads
- Directory: `uploads/`
- Supported formats: JPEG images for payment proof
- Maximum file size: Configurable in Flask settings

### Security
- Password hashing: Werkzeug PBKDF2
- Session management: Flask-Login
- File security: Secure filename handling

## 📊 Database Schema

### Users Table
- `id`: Primary key
- `username`: Unique username
- `email`: Optional email address
- `password_hash`: Hashed password
- `is_admin`: Boolean admin flag
- `created_at`: Account creation timestamp

### Loans Table
- `id`: Primary key
- `customer_id`: Foreign key to Users
- `loan_name`: Descriptive loan name
- `principal_amount`: Original loan amount
- `remaining_principal`: Current remaining balance
- `interest_rate`: Annual interest rate (decimal)
- `payment_frequency`: 'daily' or 'monthly'
- `loan_type`: 'regular' or 'interest_only'
- `is_active`: Boolean active flag
- `created_at`: Loan creation timestamp
- `admin_notes`: Admin-only notes
- `customer_notes`: Customer-visible notes

### Payments Table
- `id`: Primary key
- `loan_id`: Foreign key to Loans
- `amount`: Total payment amount
- `payment_date`: Payment date and time
- `payment_type`: 'interest', 'principal', or 'both'
- `interest_amount`: Interest portion of payment
- `principal_amount`: Principal portion of payment
- `transaction_id`: Optional transaction reference
- `payment_method`: Payment method used
- `proof_filename`: Uploaded proof file name
- `status`: 'pending', 'verified', or 'rejected'

## 🏷️ Version History

### v1.0.0 - Initial Release
- Basic loan management system
- Admin and customer interfaces
- Payment processing with verification workflow
- Interest calculation for regular and interest-only loans
- Advanced filtering and sorting capabilities
- Excel export functionality
- File upload support for payment proof

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Check the documentation
- Review the code comments

## 🔮 Future Enhancements

- [ ] Email notifications for payment confirmations
- [ ] SMS integration for payment reminders
- [ ] Advanced reporting and analytics
- [ ] Multi-currency support
- [ ] API endpoints for mobile app integration
- [ ] Automated interest calculation scheduling
- [ ] Loan document management
- [ ] Customer communication portal
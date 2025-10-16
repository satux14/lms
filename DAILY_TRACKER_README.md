# Daily Tracker Management System

## Overview

The Daily Tracker Management System is a comprehensive feature that allows administrators to create and manage investment tracking files for users. Each tracker is stored as an Excel file with automated calculations and formulas, making it easy to track daily investments, payments, and returns.

## Features

### Admin Features

1. **Create Daily Trackers**
   - Create trackers for any user
   - Choose from 3 tracker types: 50K Reinvest, 1L Enhanced, or No Reinvest
   - Set investment amount, scheme period, and start date
   - Auto-generate unique Excel files with username

2. **View All Trackers**
   - See all created trackers in one place
   - Filter by user, type, or status
   - Quick access to view or edit any tracker

3. **View Tracker Details**
   - See complete tracker information
   - View all parameters and summary data
   - Display all daily entries in a table format
   - See cumulative calculations and balances

4. **Add/Edit Entries**
   - Add daily payment entries
   - Update payment modes and transaction details
   - Add notes for any day
   - Excel formulas automatically calculate cumulative and balance

### User Features

1. **View Own Tracker**
   - Users can see their daily tracker from their dashboard
   - View all payment history
   - See summary information (total payments, cumulative, balance)
   - Track pending payments

2. **Dashboard Integration**
   - If a user has a tracker, they see a prominent card on their dashboard
   - Quick link to view full tracker details
   - Displays key information at a glance

## Tracker Types

### 1. 50K Reinvest Tracker
- Designed for ₹50,000 reinvestment strategy
- Default per day payment: ₹500
- Columns: Day, Date, Daily Payments, Cumulative, Payment Mode, Balance, Withdrawn, Notes
- Auto-calculates balance after withdrawals
- Suitable for 100-day schemes

### 2. 1L Enhanced Tracker
- Enhanced strategy with ₹1L (₹1,00,000) investment
- Default per day payment: ₹1,000
- Additional columns: Reinvest, Reinvest From, Pocket Money, Total Invested
- Tracks reinvestment sources and pocket money
- Ideal for long-term investment tracking (200+ days)

### 3. No Reinvest Tracker
- Simple tracking without reinvestment
- Default per day payment: ₹3,000
- Columns: Day, Date, Daily Payments, Transaction Details, Payment Mode, Cumulative, Balance, Withdrawn, Notes
- Focuses on straightforward payment tracking
- Best for fixed-return investments

## File Structure

```
lending_app/
├── daily-trackers/
│   ├── template/
│   │   └── DailyTrackerTemplate.xlsx  # Master template with all 3 sheet types
│   └── tracker_manager.py             # Core Excel operations module
├── instances/
│   ├── prod/
│   │   └── daily-trackers/            # Production tracker files
│   ├── dev/
│   │   └── daily-trackers/            # Development tracker files
│   └── testing/
│       └── daily-trackers/            # Testing tracker files
└── templates/
    ├── admin/
    │   ├── daily_trackers.html        # List all trackers
    │   ├── create_daily_tracker.html  # Create new tracker
    │   ├── view_daily_tracker.html    # View tracker details
    │   └── add_tracker_entry.html     # Add/edit entries
    └── customer/
        └── daily_tracker.html         # User view their tracker
```

## Database Schema

### DailyTracker Model

```python
id                  # Primary key
user_id             # Foreign key to User
tracker_name        # Name of the tracker
tracker_type        # '50K', '1L', or 'No Reinvest'
investment          # Initial investment amount
scheme_period       # Duration in days
start_date          # Start date of the tracker
filename            # Unique Excel filename
created_at          # Creation timestamp
updated_at          # Last update timestamp
is_active           # Active status
```

## Multi-Instance Support

The Daily Tracker system is fully multi-instance aware:

- Each instance (prod, dev, testing) has its own `daily-trackers` folder
- Files are created under `instances/{instance_name}/daily-trackers/`
- Database entries are isolated per instance
- All queries use the instance-aware database manager

## Excel Operations

### tracker_manager.py Functions

1. **create_tracker_file()**
   - Creates a new Excel file from template
   - Fills in parameters (tracker name, investment, dates)
   - Removes unused sheets
   - Saves to instance-specific directory

2. **get_tracker_data()**
   - Reads all data from an Excel tracker
   - Extracts parameters and data rows
   - Returns structured dictionary

3. **update_tracker_entry()**
   - Updates a specific day's entry
   - Handles all column types based on tracker type
   - Preserves Excel formulas

4. **get_tracker_summary()**
   - Calculates summary information
   - Returns total days, payments, balance, cumulative, pending

## URL Routes

### Admin Routes
- `/<instance>/admin/daily-trackers` - List all trackers
- `/<instance>/admin/daily-trackers/create` - Create new tracker
- `/<instance>/admin/daily-trackers/<id>` - View tracker details
- `/<instance>/admin/daily-trackers/<id>/add-entry` - Add/edit entry

### User Routes
- `/<instance>/customer/daily-tracker` - View own tracker

## Usage Examples

### Creating a Tracker (Admin)

1. Navigate to "Daily Trackers" > "Create Tracker"
2. Select the user from dropdown
3. Enter tracker name (e.g., "John's Investment Q4 2024")
4. Choose tracker type (50K, 1L, or No Reinvest)
5. Enter investment amount (e.g., 50000)
6. Set scheme period in days (e.g., 100)
7. Select start date
8. Click "Create Tracker"

Result: A unique Excel file is created with the format `tracker_{username}_{timestamp}.xlsx`

### Adding an Entry (Admin)

1. Go to tracker view page
2. Click "Add Entry"
3. Select the day number (0 = start date, 1 = first day, etc.)
4. Enter daily payment amount
5. Select payment mode (Cash, Bank Transfer, UPI, etc.)
6. Add any notes
7. Click "Save Entry"

Result: The Excel file is updated with the new entry, and all formulas recalculate automatically.

### Viewing Tracker (User)

1. User logs in and sees their dashboard
2. If they have a tracker, a prominent card is displayed
3. Click "View My Tracker"
4. See all details: parameters, summary, and daily entries
5. Only days with payments are highlighted for easy viewing

## Excel Template Structure

The template (`DailyTrackerTemplate.xlsx`) contains 3 sheets:

### Sheet Structure
- **Row 1**: Title with emoji and tracker type
- **Row 3**: Tracker Name (editable)
- **Rows 5-11**: Parameters section (Investment, Scheme Period, Per Day Payment, Start Date, etc.)
- **Row 12**: Column headers
- **Row 13+**: Data rows (Day 0, Day 1, Day 2, ...)

### Formulas
- **Date**: Auto-calculated from start date + day number
- **Cumulative**: Running total of all payments
- **Balance**: Cumulative minus withdrawals (for applicable types)
- **Total Invested**: Tracks reinvestment amounts (1L type only)

## Best Practices

1. **Naming Convention**: Use descriptive tracker names that include user name and period
2. **Start Date**: Can be past, present, or future date
3. **Scheme Period**: Set realistic periods (100-200 days typical)
4. **Regular Updates**: Add entries regularly to keep tracker current
5. **Backup**: The Excel files are stored in instance directories - backup regularly

## Troubleshooting

### Tracker Not Showing for User
- Check that tracker is marked as `is_active=True`
- Verify user_id matches the logged-in user
- Ensure the Excel file exists in the instance directory

### Excel File Not Found
- Check the instance directory: `instances/{instance}/daily-trackers/`
- Verify filename in database matches actual file
- Ensure file permissions allow read/write

### Calculations Not Working
- Excel formulas are in the template - don't manually edit formula cells
- When adding entries, only update input cells (daily payment, notes, etc.)
- The file opens with `data_only=True` to read calculated values

## Future Enhancements

Potential improvements:
1. Export tracker to PDF
2. Email tracker reports to users
3. Bulk entry import from CSV
4. Tracker analytics and charts
5. Notifications for pending payments
6. Archive old trackers
7. Duplicate tracker for new period

## Technical Notes

- Uses `openpyxl` library for Excel operations
- Thread-safe file operations
- Instance-aware database queries
- Flask-Login protected routes
- Bootstrap 5 for responsive UI
- Font Awesome icons

## Support

For issues or questions about the Daily Tracker system, contact your system administrator.

## Version History

- **v1.0.0** (2024-10-16): Initial release
  - Create, view, and edit daily trackers
  - Three tracker types supported
  - Multi-instance aware
  - Full admin and user interfaces


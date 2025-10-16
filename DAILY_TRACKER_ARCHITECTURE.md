# Daily Tracker Architecture

## Overview: Hybrid Database + Excel File System

The Daily Tracker system uses a **hybrid approach** combining database and Excel files for optimal performance and flexibility.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADMIN CREATES TRACKER                     │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────┐
        │  1. Admin fills form:                           │
        │     - User: john                                │
        │     - Tracker Name: "John's Q4 Investment"      │
        │     - Type: 50K Reinvest                        │
        │     - Investment: ₹50,000                       │
        │     - Period: 100 days                          │
        │     - Start Date: 2024-10-16                    │
        └─────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │  2. System creates PHYSICAL EXCEL FILE:                  │
        │                                                           │
        │  File: instances/prod/daily-trackers/                   │
        │        tracker_john_20241016_143025.xlsx                 │
        │                                                           │
        │  Content:                                                 │
        │  ┌────────────────────────────────────────────────────┐ │
        │  │ 🎯 INVESTMENT TRACKER - ₹50K REINVESTMENT STRATEGY│ │
        │  │                                                    │ │
        │  │ Tracker Name: John's Q4 Investment                │ │
        │  │                                                    │ │
        │  │ PARAMETERS                                         │ │
        │  │ Investment: ₹50,000                               │ │
        │  │ Scheme Period: 100 (Days)                         │ │
        │  │ Start Date: 2024-10-16                            │ │
        │  │                                                    │ │
        │  │ Day | Date | Payments | Cumulative | Balance     │ │
        │  │  0  |10/16 |          |            |              │ │
        │  │  1  |10/17 |          |  =F13+C14  |  =F13+C14... │ │
        │  │  2  |10/18 |          |  =F14+C15  |  =F14+C15... │ │
        │  │ ... (with Excel formulas)                         │ │
        │  └────────────────────────────────────────────────────┘ │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │  3. System creates DATABASE RECORD:                      │
        │                                                           │
        │  daily_tracker table:                                    │
        │  ┌────────────────────────────────────────────────────┐ │
        │  │ id: 1                                              │ │
        │  │ user_id: 5 (john)                                  │ │
        │  │ tracker_name: "John's Q4 Investment"               │ │
        │  │ tracker_type: "50K"                                │ │
        │  │ investment: 50000.00                               │ │
        │  │ scheme_period: 100                                 │ │
        │  │ start_date: 2024-10-16                             │ │
        │  │ filename: "tracker_john_20241016_143025.xlsx" ◄────┼─┐
        │  │ is_active: true                                    │ │
        │  └────────────────────────────────────────────────────┘ │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  └──────┐
                                         │ Links to Excel file
                                         ▼

┌─────────────────────────────────────────────────────────────────┐
│                      ADMIN ADDS DAILY ENTRY                      │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────┐
        │  1. Admin selects:                              │
        │     - Day: 1                                     │
        │     - Payment: ₹500                             │
        │     - Mode: UPI                                  │
        │     - Notes: "Daily payment received"            │
        └─────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │  2. System UPDATES the EXCEL FILE:                       │
        │                                                           │
        │  Opens: tracker_john_20241016_143025.xlsx                │
        │                                                           │
        │  Updates Row 14 (Day 1):                                 │
        │  ┌────────────────────────────────────────────────────┐ │
        │  │ Day | Date | Payments | Mode | Cumulative |Balance│ │
        │  │  0  |10/16 |          |      |            |       │ │
        │  │  1  |10/17 |  ₹500   | UPI  |  ₹500      | ₹500  │ │◄─ Updated!
        │  │  2  |10/18 |          |      |            |       │ │
        │  │                                                    │ │
        │  │ (Excel formulas auto-calculate Cumulative/Balance)│ │
        │  └────────────────────────────────────────────────────┘ │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │  3. System UPDATES DATABASE:                             │
        │     - Sets updated_at = now()                            │
        │     (No entry-level data stored in database)             │
        └──────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                    USER VIEWS THEIR TRACKER                      │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌─────────────────────────────────────────────────┐
        │  1. User logs in as "john"                       │
        └─────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │  2. System QUERIES DATABASE:                             │
        │     SELECT * FROM daily_tracker                          │
        │     WHERE user_id = 5 AND is_active = true               │
        │                                                           │
        │     Returns: tracker_john_20241016_143025.xlsx           │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │  3. System READS EXCEL FILE:                             │
        │     - Opens tracker_john_20241016_143025.xlsx            │
        │     - Reads all parameters                               │
        │     - Reads all daily entries                            │
        │     - Calculates summary (total payments, balance, etc.) │
        └──────────────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────┐
        │  4. System DISPLAYS to user:                             │
        │                                                           │
        │  ┌────────────────────────────────────────────────────┐ │
        │  │ 📊 John's Q4 Investment                            │ │
        │  │                                                    │ │
        │  │ Summary:                                           │ │
        │  │ • Days with Payments: 1                           │ │
        │  │ • Total Payments: ₹500                            │ │
        │  │ • Balance: ₹500                                   │ │
        │  │ • Pending: ₹0                                     │ │
        │  │                                                    │ │
        │  │ Daily Entries:                                     │ │
        │  │ Day 1 | 10/17 | ₹500 | UPI | ₹500 | ₹500         │ │
        │  └────────────────────────────────────────────────────┘ │
        └──────────────────────────────────────────────────────────┘
```

## Why This Hybrid Approach?

### 🗄️ Database Stores (Metadata):
- **Tracker ownership** (which user)
- **Tracker metadata** (name, type, investment, period)
- **File location** (filename)
- **Status** (active/inactive)
- **Timestamps** (created, updated)

**Benefits:**
- ✅ Fast queries ("show me all trackers for user X")
- ✅ Easy filtering/searching
- ✅ Track which users have trackers
- ✅ Can show tracker info without opening Excel

### 📊 Excel Files Store (Actual Data):
- **All daily entries** (day-by-day payments)
- **Payment modes, notes, transaction details**
- **Formulas** (auto-calculate cumulative, balance)
- **Full tracker calculations**

**Benefits:**
- ✅ Preserves Excel formulas from template
- ✅ Users can download and work offline
- ✅ Can open in Excel for manual review
- ✅ Formulas auto-calculate on update
- ✅ Can add 100s of rows without database bloat

## File Structure

```
lending_app/
├── daily-trackers/
│   ├── template/
│   │   └── DailyTrackerTemplate.xlsx      # Master template (3 sheets)
│   └── tracker_manager.py                 # Excel operations
│
└── instances/
    ├── prod/
    │   └── daily-trackers/                # Production Excel files
    │       ├── tracker_john_20241016_143025.xlsx
    │       ├── tracker_sarah_20241016_150132.xlsx
    │       └── tracker_mike_20241017_093045.xlsx
    │
    ├── dev/
    │   └── daily-trackers/                # Development Excel files
    │
    └── testing/
        └── daily-trackers/                # Testing Excel files
```

## Data Flow Summary

### Creating Tracker:
1. Admin submits form
2. **Excel file created** from template (with formulas)
3. **Database record created** (with filename)
4. File stored in `instances/{instance}/daily-trackers/`

### Adding Entry:
1. Admin submits entry form
2. **Excel file opened** and updated
3. Excel formulas **auto-recalculate**
4. **Database timestamp** updated

### Viewing Tracker:
1. Query database for tracker metadata
2. **Read Excel file** for actual data
3. Calculate summary from Excel data
4. Display to user

## Key Functions

### tracker_manager.py:

```python
create_tracker_file()     # Creates new Excel file from template
get_tracker_data()        # Reads all data from Excel file
update_tracker_entry()    # Updates specific day in Excel file
get_tracker_summary()     # Calculates summary from Excel data
```

### app_multi.py:

```python
admin_create_daily_tracker()   # Creates Excel + DB record
admin_view_daily_tracker()     # Reads Excel file to display
admin_add_tracker_entry()      # Updates Excel file
customer_daily_tracker()       # User views their Excel data
```

## Example: Complete Data for One Tracker

### In Database:
```sql
SELECT * FROM daily_tracker WHERE id = 1;

id: 1
user_id: 5
tracker_name: "John's Q4 Investment"
tracker_type: "50K"
investment: 50000.00
scheme_period: 100
start_date: 2024-10-16
filename: "tracker_john_20241016_143025.xlsx"
created_at: 2024-10-16 14:30:25
updated_at: 2024-10-16 15:45:12
is_active: true
```

### In Excel File (tracker_john_20241016_143025.xlsx):
```
Row 3: Tracker Name: John's Q4 Investment
Row 6: Investment: 50000
Row 7: Scheme Period: 100 (Days)
Row 10: Start Date: 2024-10-16

Row 13: Day 0 | 2024-10-16 |        |     |        |        |
Row 14: Day 1 | 2024-10-17 | 500    | UPI | 500    | 500    |
Row 15: Day 2 | 2024-10-18 | 500    | UPI | 1000   | 1000   |
Row 16: Day 3 | 2024-10-19 | 500    | Cash| 1500   | 1500   |
... (up to Day 100)
```

## Advantages of This Approach

1. **Best of Both Worlds**
   - Database: Fast queries, relationships, metadata
   - Excel: Formulas, formatting, downloadable

2. **Scalability**
   - Database stays small (only metadata)
   - Excel files handle large datasets efficiently

3. **User Flexibility**
   - Users can download Excel files
   - Admins can manually review/edit files
   - System can programmatically update files

4. **Data Integrity**
   - Excel formulas ensure calculations are correct
   - Database ensures files are properly tracked
   - Each file is unique and versioned

5. **Multi-Instance Isolation**
   - Each instance has separate Excel directories
   - Each instance has separate database records
   - No file conflicts between instances

## Backup Strategy

Both components should be backed up:

```bash
# Backup database (includes metadata)
cp instance/prod/database/lending_app_prod.db backups/

# Backup Excel files (includes actual data)
tar -czf daily_trackers_backup.tar.gz instances/prod/daily-trackers/
```

---

**This hybrid approach gives you the power of a database with the flexibility of Excel!**


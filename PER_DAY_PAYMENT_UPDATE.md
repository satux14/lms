# Per Day Payment Feature Update

## What's New

The admin can now **set a custom Per Day Payment amount** when creating a daily tracker, instead of using fixed defaults.

## Changes Made

### 1. Database Model Updated
- Added `per_day_payment` column to `DailyTracker` model
- Stores the daily payment amount set by admin

### 2. Create Tracker Form Updated
- New field: **Per Day Payment** (required)
- Auto-suggests default values when tracker type is selected:
  - **50K Reinvest**: ₹500
  - **1L Enhanced**: ₹1,000
  - **No Reinvest**: ₹3,000
- Admin can override with any custom amount

### 3. Excel File Updated
- The `per_day_payment` value is written to the Excel template
- Excel formulas use this value for calculations

### 4. Smart Auto-Fill
When admin selects a tracker type, the Per Day Payment field automatically fills with the suggested amount, but can be changed to any value.

## Migration Steps

### If You're Setting Up Fresh (No Existing Trackers)

Just run the main migration:

```bash
cd /Users/skumarraju/Documents/Work/progs/lending_app
python3 migrate_daily_tracker.py
```

The `per_day_payment` column will be included automatically.

### If You Already Have Trackers

Run this additional migration to add the column:

```bash
cd /Users/skumarraju/Documents/Work/progs/lending_app
python3 migrate_per_day_payment.py
```

This will:
- Add the `per_day_payment` column to existing tables
- Set default values for existing trackers based on their type
- Keep all existing data intact

## Using the Feature

### Creating a Tracker:

1. Navigate to **Admin → Daily Trackers → Create Tracker**
2. Fill in user, tracker name, type, investment, period
3. **Select Tracker Type** - the Per Day Payment field auto-fills with suggestion
4. **Modify Per Day Payment** if needed (e.g., change ₹500 to ₹750)
5. Select start date
6. Click "Create Tracker"

### Result:

The Excel file will use your custom Per Day Payment value for all calculations.

## Examples

### Example 1: Custom 50K Tracker
```
User: John
Tracker Type: 50K Reinvest
Investment: ₹50,000
Per Day Payment: ₹750 (custom, instead of default ₹500)
Period: 100 days
```

Excel file will calculate based on ₹750/day.

### Example 2: Custom 1L Tracker
```
User: Sarah
Tracker Type: 1L Enhanced
Investment: ₹3,00,000
Per Day Payment: ₹1,500 (custom, instead of default ₹1,000)
Period: 200 days
```

Excel file will calculate based on ₹1,500/day.

## Benefits

✅ **Flexibility**: Set any daily payment amount  
✅ **Smart Defaults**: Auto-suggests standard amounts  
✅ **Customizable**: Easy to override for special cases  
✅ **Accurate**: Excel formulas use exact value provided  

## UI Flow

```
1. Select Tracker Type: "50K Reinvest"
   ↓
2. Per Day Payment auto-fills: "500"
   ↓
3. Admin can change to: "750" (or any amount)
   ↓
4. Create Tracker
   ↓
5. Excel file created with ₹750 per day payment
```

## Database Schema Update

```sql
ALTER TABLE daily_tracker 
ADD COLUMN per_day_payment NUMERIC(15, 2) NOT NULL;
```

Existing trackers get defaults:
- 50K trackers → ₹500
- 1L trackers → ₹1,000
- No Reinvest trackers → ₹3,000

## Files Modified

1. `app_multi.py` - Added `per_day_payment` to DailyTracker model and route
2. `daily-trackers/tracker_manager.py` - Updated to accept and use per_day_payment
3. `templates/admin/create_daily_tracker.html` - Added per_day_payment field with auto-fill
4. `migrate_per_day_payment.py` - New migration script for existing installations

## Backward Compatibility

✅ Fully backward compatible  
✅ Existing trackers keep their default values  
✅ New trackers can use custom values  
✅ Excel templates work with both old and new trackers  

---

**Your tracker creation just got more flexible!** 🎉


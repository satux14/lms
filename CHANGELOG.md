# Changelog

All notable changes to the Lending Management System (LMS) will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Release management system with automated scripts
- Comprehensive validation before releases
- Rollback functionality for emergency situations

### Changed
- Centralized version management with VERSION file

## [2.1.0] - 2024-09-11

### Added
- Interest information to admin loans view (Interest Rate, Interest Paid columns)
- Loan close/delete functionality with safe database migration
- Payment delete functionality for admins
- Comprehensive database migration system with automatic backups
- Principal Payment Progress labels for better UI clarity

### Changed
- Removed Daily Payment Loans summary card for cleaner UI
- Removed redundant action buttons (Calculate Interest, Payment History)
- Updated admin loans view with better information display
- Improved payment processing logic for regular loans
- Enhanced accumulated interest calculation accuracy

### Fixed
- Fixed admin loans sorting error (TypeError resolution)
- Fixed payment processing logic to prioritize accumulated interest
- Fixed accumulated interest calculation to always calculate from loan creation date
- Fixed payment allocation for regular loans

### Security
- Added safe database migration with automatic backups
- Implemented rollback capability for database changes

## [2.0.0-multi-instance-backup] - 2024-09-10

### Added
- Multi-instance architecture (prod, dev, testing)
- Instance-specific database management
- URL-based instance routing
- Instance selection in admin interface

### Changed
- Restructured application for multi-instance support
- Updated all routes to include instance_name parameter
- Modified database queries to use instance-specific connections

## [2.0] - 2024-09-10

### Added
- Docker support with Dockerfile and docker-compose.yml
- Password management system (change, recovery, admin reset)
- Interest calculation with 360-day year constant
- Support for interest-free loans (0% interest rate)
- Payment progress tracking for principal payments

### Changed
- Standardized sidebar menus across all admin templates
- Removed demo account credentials from homepage
- Removed PROD instance badge from header
- Removed user registration from homepage (admin-only user creation)
- Updated interest calculation from 365 to 360 days

### Fixed
- Fixed AttributeError: 'Query' object has no attribute 'get_or_404'
- Fixed interest rate conversion (60.00% instead of 6000.00%)
- Fixed loan creation date handling in edit loan functionality
- Fixed customer selection dropdown to show both name and email
- Fixed payment amount input validation

## [1.0.1] - 2024-09-09

### Fixed
- Minor bug fixes and improvements
- Enhanced error handling

## [1.0.0] - 2024-09-09

### Added
- Initial release of Lending Management System
- User authentication and authorization
- Loan management functionality
- Payment processing system
- Admin and customer interfaces
- Interest calculation system
- Database management with SQLite

---

## Release Types

- **Major** (X.0.0): Breaking changes, major new features, architecture changes
- **Minor** (X.Y.0): New features, enhancements, UI improvements
- **Patch** (X.Y.Z): Bug fixes, security patches, performance improvements

## How to Use This Changelog

- **Added** for new features
- **Changed** for changes in existing functionality
- **Deprecated** for soon-to-be removed features
- **Removed** for now removed features
- **Fixed** for any bug fixes
- **Security** for security improvements

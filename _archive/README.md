# Archive Directory

This directory contains legacy files preserved during the transition from Flask-only architecture to React frontend + Flask API architecture.

## Contents

### legacy-frontend/
Contains the original frontend assets from the Flask-based web application:

- **static/**: Static assets (JavaScript, CSS, images) that were served directly by Flask
  - `js/project.js`: Project-specific JavaScript functionality
  - `js/shared.js`: Shared JavaScript utilities and components

**Note:** No `templates/` directory was found during archival - the original Flask app may have used a different templating approach or served content programmatically.

## Why These Files Are Preserved

These files are archived (not deleted) for the following reasons:

1. **Reference**: Contains implementation patterns and business logic from the original frontend
2. **Migration Safety**: Allows reverting changes if needed during the React transition
3. **Code Reuse**: JavaScript utilities and functions may be adaptable for the new React frontend
4. **Documentation**: Serves as historical reference for how features were originally implemented

## Transition Notes

- **Date Archived**: 2026-01-06
- **Original Location**: `web/static/` and `web/templates/` (templates not found)
- **Reason**: Migrating to React frontend architecture
- **Status**: Flask API (`web/app.py`) remains active and unchanged

## Do Not Modify

These files should be considered read-only archives. Any needed functionality should be re-implemented in the new React frontend located in `/frontend/`.
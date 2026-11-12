# Demo User Accounts - EPI Platform

This document lists all demo/test user accounts for the Enterprise Procurement Intelligence platform.

## Quick Reference

| Role | Email | Password | Name |
|------|-------|----------|------|
| **Admin** | admin@epi.local | admin-local-password | Platform Administrator |
| **Buyer** | buyer@epi.local | buyer123 | Sarah Johnson |
| **Supplier** | supplier@epi.local | supplier123 | TechCorp Supplier Account |
| **Reader** | reader@epi.local | reader123 | John Viewer |

## Creating Demo Users

### Automatic Setup
Run the setup script to create all demo users at once:

```bash
cd backend
python scripts/create_demo_users.py
```

This will:
- Create users for all 4 roles (admin, buyer, supplier, reader)
- Skip any users that already exist
- Display user IDs and confirmation

### Manual Creation
Create individual users via CLI:

```bash
cd backend
python -m app.cli create-user \
  --email "your-email@example.com" \
  --password "YourPassword123" \
  --name "Your Name" \
  --role "buyer"
```

## Role Permissions

### Admin
- **Full system access**
- Manage users and tenants
- Access all documents and data
- Configure system settings
- View audit logs

**Use for**: System administration, platform management

### Buyer
- **Procurement team member**
- Upload and manage procurement documents
- Search and query the knowledge base
- Create and view contract analyses
- Access supplier information
- Generate reports

**Use for**: Day-to-day procurement operations, RFP management

### Supplier
- **Vendor/supplier account**
- View published opportunities
- Submit proposals (if enabled)
- Access awarded contracts
- Limited document access

**Use for**: Supplier portal testing, vendor interactions

### Reader
- **Read-only access**
- View documents and analyses
- Search the knowledge base
- Cannot upload or modify data
- Cannot create reports

**Use for**: Stakeholder visibility, compliance auditing

## Testing Scenarios

### Scenario 1: Document Upload & Analysis
```
User: buyer@epi.local
Flow: Login → Upload Contract → Wait for Processing → View Analysis
```

### Scenario 2: Knowledge Base Search
```
User: buyer@epi.local or reader@epi.local
Flow: Login → Navigate to Search → Query → View Results → Explore Graph
```

### Scenario 3: Admin Management
```
User: admin@epi.local
Flow: Login → Admin Panel → Create Users → View Stats
```

### Scenario 4: Supplier View
```
User: supplier@epi.local
Flow: Login → View Opportunities → Check Contract Status
```

## API Testing

### Login Example
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "buyer@epi.local",
    "password": "buyer123"
  }'
```

### Using Access Token
```bash
# Save token from login response
export TOKEN="eyJ..."

# Make authenticated request
curl -X GET http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer $TOKEN"
```

## Production Deployment

### Render Backend
The production backend on Render only has:
- **admin@epi.local** (auto-created via `BOOTSTRAP_ADMIN_EMAIL` environment variable)

To add demo users to production:
1. Connect to production database
2. Run `create_demo_users.py` against production DB URL
3. Or use CLI to create individual users

### Security Note
⚠️ **Never use these test passwords in production!**

For production:
- Use strong, unique passwords
- Enable MFA if available
- Rotate credentials regularly
- Follow your organization's security policy

## Troubleshooting

### User Already Exists
If you see "User already exists" error:
- User is already registered in the system
- Use the existing credentials to log in
- Or create a new user with a different email

### Cannot Create User
Check that:
- Database is initialized (`python -m app.cli initdb`)
- Database file exists at `backend/var/epi.db` (for SQLite)
- Password meets minimum requirements (8 characters)

### Login Fails
Verify:
- Email is spelled correctly (case-sensitive)
- Password matches exactly
- User was created in the correct tenant
- Backend server is running

## Resetting Demo Users

To start fresh:

```bash
# Stop backend server first

# Delete database (SQLite)
rm backend/var/epi.db

# Recreate schema
cd backend
python -m app.cli initdb

# Recreate demo users
python scripts/create_demo_users.py
```

## Default Tenant

All demo users are created in the default tenant:
- **Tenant Slug**: `acme-procurement`
- **Tenant Name**: "Acme Procurement"

Change this via environment variables:
```bash
DEFAULT_TENANT_SLUG=your-tenant-slug
```

---

**Last Updated**: November 13, 2026  
**Version**: 1.0

# Authentication Architecture - Role-Based Access Control

## Overview

The Dynamic Meeting Assistant backend supports **two separate applications** with role-based authentication:

1. **Client App** (Meeting Assistant) - Regular users with `role='user'`
2. **Admin App** (Dashboard) - Admin users with `role='admin'`

Both apps share the same backend but use **completely separate authentication flows** and endpoints.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            BACKEND SERVER                                 │
│                          (Single Flask App)                               │
├──────────────────────────────────────────────────────────────────────────┤
│                                                                            │
│  ┌─────────────────────────────────┐    ┌──────────────────────────────┐│
│  │   CLIENT APP ENDPOINTS          │    │    ADMIN APP ENDPOINTS       ││
│  │   /api/auth/*                   │    │    /api/admin/auth/*         ││
│  │                                 │    │                              ││
│  │  📦 DATA STORAGE/RETRIEVAL ONLY │    │  🔐 FULL AUTHENTICATION      ││
│  │                                 │    │                              ││
│  │  ❌ NO OAuth verification       │    │  ✅ Email + Password verify  ││
│  │  ❌ NO token verification       │    │  ✅ Bcrypt hash comparison   ││
│  │  ❌ NO authentication logic     │    │  ✅ JWT generation           ││
│  │                                 │    │  ✅ JWT verification         ││
│  │  ✅ Store user in database      │    │  ✅ Role-based access        ││
│  │  ✅ Fetch user from database    │    │  ✅ Session management       ││
│  │  ✅ Update user data            │    │                              ││
│  │  ✅ CRUD operations             │    │  • role='admin'              ││
│  │                                 │    │  • password_hash             ││
│  │  • role='user'                  │    │  • auth_provider:            ││
│  │  • firebase_uid                 │    │    'admin_email'             ││
│  │  • auth_provider:               │    │                              ││
│  │    'google_oauth'               │    │                              ││
│  └─────────────────────────────────┘    └──────────────────────────────┘│
│              │                                        │                   │
│              │                                        │                   │
│              │    ┌──────────────────────────────┐   │                   │
│              └────►  PostgreSQL (Neon) Database  ◄───┘                   │
│                   │                              │                        │
│                   │  users table:                │                        │
│                   │  ├─ id (UUID)                │                        │
│                   │  ├─ email (unique)           │                        │
│                   │  ├─ name                     │                        │
│                   │  ├─ role ('user' | 'admin')  │                        │
│                   │  ├─ firebase_uid (clients)   │                        │
│                   │  ├─ password_hash (admins)   │                        │
│                   │  ├─ auth_provider            │                        │
│                   │  └─ ... other fields         │                        │
│                   └──────────────────────────────┘                        │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │  IMPORTANT:                                                         │  │
│  │  • Client endpoints = Data management ONLY (no auth verification)  │  │
│  │  • Admin endpoints = Full authentication + data management         │  │
│  │  • OAuth for clients happens in FRONTEND (Firebase)                │  │
│  │  • Authentication for admins happens in BACKEND (Flask)            │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└──────────────────────────────────────────────────────────────────────────┘

FRONTEND (Client App)                    FRONTEND (Admin App)
─────────────────────                    ────────────────────
🔥 Firebase SDK                          📝 Login Form
🔥 Google OAuth (popup/redirect)         📝 Email + Password input
🔥 Authentication happens HERE           
                                         
↓ After auth success                    ↓ Submit credentials
                                         
Send user data to backend                Send credentials to backend
(firebase_uid, email, name)              (email, password)
                                         
Backend stores in database               Backend verifies & generates JWT
Backend returns user record              Backend returns JWT token
```

---

## Quick Comparison

| Feature | Client App | Admin App |
|---------|-----------|-----------|
| **Authentication Method** | ✅ Google Sign-In ONLY | ✅ Email + Password ONLY |
| **OAuth Handled By** | 🔥 **FRONTEND (Firebase)** | ❌ N/A |
| **Backend Role** | 📦 **Data storage/retrieval ONLY** | 🔐 **Full authentication** |
| **Backend Verifies Auth** | ❌ **NO** - Firebase handles it | ✅ **YES** - Every request |
| **User Role** | `role='user'` | `role='admin'` |
| **Auth Provider** | Firebase + Google OAuth (frontend) | Backend Email/Password |
| **Password Storage** | ❌ None (Google handles it) | ✅ Bcrypt hashed (backend) |
| **Session Management** | Firebase tokens (frontend) | JWT tokens (backend) |
| **Token Verification** | ❌ Backend doesn't verify | ✅ Backend verifies JWT |
| **Endpoints** | `/api/auth/*` (data only) | `/api/admin/auth/*` (auth + data) |
| **Primary Use** | Meeting management | System administration |
| **Calendar Integration** | ✅ Automatic | ❌ Not needed |
| **Can Access Meetings** | ✅ Own meetings only | ❌ No access (privacy) |
| **Can Manage Users** | ❌ No | ✅ Yes |
| **Can View Statistics** | ❌ No | ✅ Yes |

---

## 1. Client App Authentication (Regular Users)

### Endpoints: `/api/auth/*`

### User Role: `role='user'`

### Authentication Method:
- ✅ **Google Sign-In ONLY** (via Firebase Authentication)
- ❌ Email/Password NOT supported (use Google Sign-In instead)
- ❌ Other OAuth providers NOT supported

**Why Google Sign-In Only?**
- Simplified user experience (one-click sign-in)
- No password management needed
- Secure authentication handled by Google
- Automatic calendar integration
- Better user experience for meeting management app

### Key Endpoints:

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/auth/verify` | POST | Verify/create user account | No |
| `/api/auth/user/<identifier>` | GET | Get user profile | No |
| `/api/auth/user/<firebase_uid>` | PUT | Update user profile | No |
| `/api/auth/user/<firebase_uid>/notifications` | GET/PUT | Manage notifications | No |
| `/api/auth/google-oauth` | POST | Google OAuth verification | No |

### Features Available to Client Users:
- ✅ Upload meeting recordings
- ✅ View meeting transcripts and summaries
- ✅ Manage tasks extracted from meetings
- ✅ View timeline of meeting events
- ✅ Google Calendar integration
- ✅ Notification preferences
- ✅ Profile management
- ❌ **NO ACCESS** to admin dashboard
- ❌ **NO ACCESS** to user management
- ❌ **NO ACCESS** to system-wide statistics

### Security Rules:
1. All new users created via `/api/auth/verify` get `role='user'` automatically
2. Admin accounts **cannot** authenticate through client endpoints (403 Forbidden)
3. Client users **cannot** access admin endpoints (403 Forbidden)
4. Firebase UID is used as the primary identifier for client users

---

## 2. Admin App Authentication (Admin Users)

### Endpoints: `/api/admin/auth/*`

### User Role: `role='admin'`

### Authentication Method:
- ✅ **Email + Password ONLY** (Stored with bcrypt hash)
- ✅ **JWT Tokens** (For session management)
- ❌ Google Sign-In NOT supported (use Email + Password instead)
- ❌ Firebase Auth NOT supported

**Why Email + Password Only?**
- Traditional admin login experience
- No dependency on external OAuth providers
- Works in any environment (including internal networks)
- Full control over admin account creation
- Separate from client authentication for security

### Key Endpoints:

| Endpoint | Method | Description | Auth Required |
|----------|--------|-------------|---------------|
| `/api/admin/auth/login` | POST | Admin login | No |
| `/api/admin/auth/verify-token` | POST | Verify JWT token | No |
| `/api/admin/auth/logout` | POST | Admin logout | Yes (JWT) |
| `/api/admin/auth/profile` | GET | Get admin profile | Yes (JWT) |

### Features Available to Admin Users:
- ✅ View all users in the system
- ✅ Manage user accounts (promote/demote, activate/deactivate)
- ✅ View and manage reported issues
- ✅ View payment transactions
- ✅ Send system notifications
- ✅ View system-wide statistics
- ✅ Access admin dashboard
- ❌ **NO ACCESS** to individual user meetings (privacy)
- ❌ **NO ACCESS** to user meeting content (privacy)

### Security Rules:
1. Admin accounts must be created manually or via environment variables
2. Admin login requires email + password (not Firebase)
3. JWT tokens are used for session management
4. Admin actions are logged in `admin_logs` table
5. Admins cannot demote themselves
6. Default admin account from `.env` file: `ADMIN_EMAIL` + `ADMIN_PASSWORD`

---

## 3. Database Schema

### Users Table

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    
    -- Role-based access control
    role VARCHAR(50) DEFAULT 'user',  -- 'user' or 'admin'
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Client app authentication
    firebase_uid VARCHAR(255) UNIQUE,
    google_oauth_id VARCHAR(255) UNIQUE,
    google_access_token TEXT,
    google_refresh_token TEXT,
    google_token_expires_at TIMESTAMP,
    google_calendar_enabled BOOLEAN DEFAULT FALSE,
    
    -- Admin authentication
    password_hash VARCHAR(255),  -- For admin email/password login
    last_login_at TIMESTAMP,
    
    -- Common fields
    auth_provider VARCHAR(50) DEFAULT 'firebase',  -- 'firebase', 'google_oauth', 'admin_email'
    email_notifications BOOLEAN DEFAULT TRUE,
    in_app_notifications BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Admin Logs Table

```sql
CREATE TABLE admin_logs (
    id UUID PRIMARY KEY,
    admin_email VARCHAR(255) NOT NULL,
    action VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50),
    resource_id VARCHAR(255),
    details TEXT,
    ip_address VARCHAR(45),
    user_agent TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 4. Middleware & Decorators

### New Authentication Middleware (`backend/middleware/auth.py`)

```python
from middleware.auth import (
    require_auth,          # Generic auth with role check
    require_user_auth,     # Client users only
    require_admin_auth,    # Admin users only
    require_any_auth,      # Any authenticated user
    optional_auth,         # Optional authentication
    get_current_user,      # Get current user info
    is_admin,              # Check if current user is admin
    is_user                # Check if current user is regular user
)
```

### Usage Examples:

```python
# Protect endpoint for client users only
@app.route('/api/meetings')
@require_user_auth()
def get_meetings():
    user = get_current_user()
    # user['role'] == 'user'
    pass

# Protect endpoint for admins only
@app.route('/api/admin/users')
@require_admin_auth()
def get_all_users():
    user = get_current_user()
    # user['role'] == 'admin'
    pass

# Allow both users and admins
@app.route('/api/health')
@require_any_auth()
def health_check():
    user = get_current_user()
    # user['role'] can be 'user' or 'admin'
    pass
```

---

## 5. Frontend Integration

### Client App (frontend/)

**Authentication Method:** ✅ **Google Sign-In ONLY** (OAuth handled by Firebase in Frontend)

**Authentication Flow:**
1. **FRONTEND**: User clicks "Sign in with Google" button
2. **FRONTEND**: Firebase opens Google Sign-In popup/redirect
3. **FRONTEND**: User authenticates with Google account (OAuth happens here)
4. **FRONTEND**: Firebase returns authenticated user with Firebase UID
5. **FRONTEND → BACKEND**: Frontend calls `/api/auth/verify` with Firebase UID + email + name
6. **BACKEND**: Backend creates/updates user record in PostgreSQL with `role='user'`
7. **BACKEND → FRONTEND**: Backend returns user data from database
8. **FRONTEND**: User can access client app features (meetings, tasks, calendar)

**Important:**
- 🔥 **OAuth is handled entirely by Firebase in the FRONTEND**
- 🔥 **Backend does NOT handle OAuth** - it only stores/retrieves user data
- 🔥 **Backend endpoints are for data management ONLY** (CRUD operations)
- 🔥 **No authentication verification in backend** - Firebase handles that

**Key Points:**
- ✅ One-click sign-in with Google (handled by Firebase)
- ✅ OAuth flow managed by Firebase SDK (frontend)
- ✅ Backend only stores user records in PostgreSQL
- ✅ Backend endpoints fetch/update user data from database
- ✅ No password to remember
- ✅ Automatic calendar integration
- ❌ Backend does NOT verify OAuth tokens
- ❌ Email/Password login NOT available

**API Base URL:** `https://dynamicmeetassistbackend-1.onrender.com/api/`

**Backend Endpoints (Data Management Only):**
- `/api/auth/verify` - Store/update user in database (NOT OAuth verification)
- `/api/auth/user/<id>` - Fetch user data from database
- `/api/meetings` - CRUD operations for user's meetings
- `/api/tasks` - CRUD operations for user's tasks
- `/api/calendar` - Calendar data operations

### Admin App (admin-app/)

**Authentication Method:** ✅ **Email + Password ONLY** (Full authentication in Backend)

**Authentication Flow:**
1. **FRONTEND**: Admin enters email + password in login form
2. **FRONTEND → BACKEND**: Frontend calls `/api/admin/auth/login` with credentials
3. **BACKEND**: Backend verifies email exists in database
4. **BACKEND**: Backend compares password with bcrypt hash
5. **BACKEND**: Backend checks if user has `role='admin'`
6. **BACKEND**: Backend generates JWT token with user info
7. **BACKEND → FRONTEND**: Backend returns JWT token + user data
8. **FRONTEND**: Frontend stores JWT token in localStorage/sessionStorage
9. **FRONTEND → BACKEND**: All subsequent requests include `Authorization: Bearer <token>` header
10. **BACKEND**: Backend verifies JWT token on every request
11. **FRONTEND**: Admin can access admin dashboard features

**Important:**
- 🔐 **Full authentication handled by BACKEND**
- 🔐 **Backend verifies credentials** (email + password hash comparison)
- 🔐 **Backend generates and verifies JWT tokens**
- 🔐 **Backend enforces role-based access control**
- 🔐 **Every admin request is authenticated by backend**

**Key Points:**
- ✅ Traditional email/password login (backend verification)
- ✅ Secure password hashing (bcrypt in backend)
- ✅ JWT token-based sessions (backend generates/verifies)
- ✅ Backend enforces authentication on every request
- ✅ No dependency on external OAuth
- ❌ Google Sign-In NOT available

**API Base URL:** `https://dynamicmeetassistbackend-1.onrender.com/api/admin/`

**Backend Endpoints (Full Authentication + Data):**
- `/api/admin/auth/login` - Verify credentials & generate JWT
- `/api/admin/auth/verify-token` - Verify JWT token validity
- `/api/admin/auth/logout` - Invalidate session
- `/api/admin/users` - User management (requires JWT)
- `/api/admin/issues` - Issue management (requires JWT)
- `/api/admin/payments` - Payment management (requires JWT)
- `/api/admin/notifications` - Notification management (requires JWT)

---

## 6. Security Best Practices

### Client App Security:
1. ✅ Google Sign-In ONLY - no password management needed
2. ✅ Firebase handles all authentication security
3. ✅ Google OAuth for secure authentication
4. ✅ No passwords stored in database for client users
5. ✅ Firebase UID as unique identifier
6. ✅ Users can only access their own data
7. ✅ Admin accounts blocked from client endpoints
8. ✅ Automatic calendar integration with proper scopes

### Admin App Security:
1. ✅ Email + Password ONLY - traditional admin login
2. ✅ Passwords hashed with bcrypt (cost factor 12)
3. ✅ JWT tokens for session management
4. ✅ Token expiration (configurable, default 24 hours)
5. ✅ Admin actions logged with IP and user agent
6. ✅ Role-based access control
7. ✅ Prevent self-demotion (admins can't demote themselves)
8. ✅ Secure headers (CSP, HSTS, X-Frame-Options, etc.)
9. ✅ No external OAuth dependencies

### General Security:
1. ✅ CORS configured per environment
2. ✅ Rate limiting on all endpoints
3. ✅ Input validation and sanitization
4. ✅ SQL injection prevention (parameterized queries)
5. ✅ XSS prevention
6. ✅ CSRF protection
7. ✅ Secure session management

---

## 7. Environment Variables

### Required for Client App:
```env
# Firebase Configuration
FIREBASE_API_KEY=your_firebase_api_key
FIREBASE_AUTH_DOMAIN=your_project.firebaseapp.com
FIREBASE_PROJECT_ID=your_project_id

# Google OAuth (for calendar)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

### Required for Admin App:
```env
# Default Admin Account
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=secure_admin_password
ADMIN_NAME=System Administrator

# JWT Configuration
JWT_SECRET_KEY=your_jwt_secret_key
JWT_EXPIRATION_HOURS=24
```

### Common:
```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/dbname

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Environment
FLASK_ENV=development
```

---

## 8. API Response Format

### Success Response:
```json
{
  "success": true,
  "message": "Operation successful",
  "data": {
    "user": {
      "id": "uuid",
      "email": "user@example.com",
      "name": "John Doe",
      "role": "user"
    }
  }
}
```

### Error Response:
```json
{
  "success": false,
  "error": "Error type",
  "message": "Human-readable error message"
}
```

---

## 9. Migration Guide

### For Existing Users:

If you have existing users in the database without a `role` field:

```sql
-- Add role column if it doesn't exist
ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(50) DEFAULT 'user';

-- Set all existing users to 'user' role
UPDATE users SET role = 'user' WHERE role IS NULL;

-- Promote specific users to admin
UPDATE users SET role = 'admin', auth_provider = 'admin_email' 
WHERE email = 'admin@example.com';
```

---

## 10. Testing

### Test Client Authentication:
```bash
# Register/login client user
curl -X POST https://dynamicmeetassistbackend-1.onrender.com/api/auth/verify \
  -H "Content-Type: application/json" \
  -d '{
    "firebase_uid": "test_uid",
    "email": "user@example.com",
    "name": "Test User"
  }'
```

### Test Admin Authentication:
```bash
# Admin login
curl -X POST https://dynamicmeetassistbackend-1.onrender.com/api/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "admin_password"
  }'
```

---

## 11. Troubleshooting

### Issue: "Admin accounts must use admin login endpoint"
**Solution:** Admin users cannot use `/api/auth/verify`. Use `/api/admin/auth/login` instead.

### Issue: "Access denied - This endpoint requires admin role"
**Solution:** Regular users cannot access admin endpoints. Check user role in database.

### Issue: "Invalid or expired token"
**Solution:** JWT token expired. Admin needs to log in again.

### Issue: User created with wrong role
**Solution:** Check which endpoint was used. `/api/auth/verify` creates users, `/api/admin/auth/login` is for existing admins.

---

## Summary

✅ **Two separate authentication systems** for client and admin apps
✅ **Role-based access control** with 'user' and 'admin' roles
✅ **Secure authentication** with Firebase (client) and JWT (admin)
✅ **Complete separation** of concerns and permissions
✅ **Comprehensive logging** of admin actions
✅ **Privacy protection** - admins can't access user meeting content
✅ **Scalable architecture** - easy to add more roles in the future

For questions or issues, refer to the specific route files:
- Client auth: `backend/routes/auth.py`
- Admin auth: `backend/routes/admin_auth.py`
- Middleware: `backend/middleware/auth.py`

# Platform Diagnostic Report

**Generated:** 2026-01-08 16:10:50
**Platform:** Internal Platform (maurinventuresinternal.com)

---

## 1. Backend Connectivity

### Database (PostgreSQL/RDS)
✅ **Database Connection:** SUCCESSFUL

- `VIDEOS COUNT`: 179
- `USERS COUNT`: 1
- `CONVERSATIONS COUNT`: 0

### AWS S3
❌ **S3 Connection:** FAILED
- Error: No module named 'config.credentials'

### AI APIs
- **ANTHROPIC_API_KEY:** ❌ NOT SET
- **OPENAI_API_KEY:** ❌ NOT SET
- **Claude API Test:** ❌ FAILED - No API key

---

## 2. API Endpoints Test

- `https://maurinventuresinternal.com/api/health`: ✅ 200
- `https://maurinventuresinternal.com/api/auth/me`: ✅ 401
- `https://maurinventuresinternal.com/api/library/videos`: ✅ 401
- `https://maurinventuresinternal.com/api/library/audio`: ✅ 401
- `https://maurinventuresinternal.com/api/conversations`: ✅ 404
- `POST /api/chat`: ✅ SUCCESS (Model: None)

---

## 3. Credentials File

❌ **Credentials File:** FAILED
- Error: No module named 'config.credentials'

---

## 4. Recent Errors

**Error Count (Last 50 log entries):** 6

**Recent Errors:**
```
Jan 08 21:01:24 ip-172-31-39-143.ec2.internal gunicorn[3956202]: AttributeError: 'Flask' object has no attribute 'session_cookie_name'
Jan 08 21:01:48 ip-172-31-39-143.ec2.internal gunicorn[3956203]: Error fetching transcripts: 'Transcript' object has no attribute 'content'
Jan 08 21:01:48 ip-172-31-39-143.ec2.internal gunicorn[3956203]: [AI_LOG ERROR] Failed to log AI call: badly formed hexadecimal UUID string
Jan 08 21:01:48 ip-172-31-39-143.ec2.internal gunicorn[3956198]: [2026-01-08 21:01:48 +0000] [3956198] [ERROR] Worker (pid:3956202) was sent SIGTERM!
Jan 08 21:01:48 ip-172-31-39-143.ec2.internal gunicorn[3956198]: [2026-01-08 21:01:48 +0000] [3956198] [ERROR] Worker (pid:3956203) was sent SIGTERM!
Jan 08 21:08:04 ip-172-31-39-143.ec2.internal gunicorn[3957625]: [2026-01-08 21:08:04 +0000] [3957625] [ERROR] Worker (pid:3957626) was sent SIGTERM!
```

---

## 5. Recent Changes

**Last 5 Commits:**
```
3f95ad6 Update: Frontend submodule with enforced 2FA login flow
5568e50 Enforce 2FA verification on every login
03f2457 Fix: Correct Flask session cookie name in logout endpoint
0b845b2 Update: Frontend submodule with complete auth state management fixes
eb78fff Fix: Backend authentication improvements
```

---

## Summary

**Overall Status:** 5/7 components healthy

🚨 **Multiple system issues detected, immediate attention required**

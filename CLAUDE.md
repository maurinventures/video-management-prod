# Claude Code Rules for Internal Platform

# PROJECT RULES - DO NOT VIOLATE
1. PRODUCTION ONLY: API endpoint is https://maurinventuresinternal.com - never localhost
2. FRONTEND REPO: Digitalbrainplatformuidesign is the only frontend - do not modify internal-platform/frontend/
3. NO UI CHANGES: Never regenerate or restyle UI components from Digitalbrainplatformuidesign

**Project:** Internal Platform
**Architecture:** React frontend + Flask API
**Last Updated:** 2026-01-07

---

## ⚠️ MODEL REQUIREMENT — CRITICAL

**USE ONLY:** Claude Sonnet 4 (`claude-sonnet-4-20250514`)

| Model | Status | Why |
|-------|--------|-----|
| Sonnet 4 | ✅ USE THIS | ~$2-3/session |
| Sonnet 4.5 | ❌ NO | 5x more expensive |
| Opus 4.5 | ❌ NO | 15x more expensive |

If wrong model, stop and run:
```bash
export ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

---

## 🏗️ Architecture

```
React Frontend (port 3000) → Flask API (port 5000) → Services → RDS/S3
     /frontend/                  /web/app.py           /scripts/
```

**UI Components (Figma Make):** `maurinventures/Digitalbrainplatformuidesign`
**Claude Code prompts:** https://www.notion.so/2e071d8cc1fa8191b355d7eba238a28c
**Project specs:** https://www.notion.so/2df71d8cc1fa815aa51cfc1bd4ce7852

---

## 🛑 CRITICAL RULES

### 1. No Breaking Changes
- Test current state BEFORE changing anything
- One small change at a time
- Deploy and verify after each change
- If it worked before, it must work after

### 2. Follow Existing Patterns
- Read existing code before writing new code
- Match the style in app.py and scripts/
- Don't create new patterns when existing ones work

### 3. No Scope Creep
- Do exactly what was asked, nothing more
- "While I'm here..." — NO, that's a separate task
- "I'll also fix..." — NO, not approved

---

## 📁 Protected Files

Extra caution required — these affect everything:

| File | Impact |
|------|--------|
| `web/app.py` | All API routes |
| `scripts/db.py` | All database models |
| `config/credentials.yaml.enc` | All secrets |
| `/frontend/src/lib/api.ts` | All API calls |
| `/frontend/src/components/` | Figma Make exports — pull from GitHub, don't manually edit |

---

## 🚀 Deploy Sequence

```bash
# 1. Build frontend (if changed)
cd frontend && npm run build

# 2. Commit with specific message
git add -A && git commit -m "Fix: [exact thing fixed]"
git push origin main

# 3. Deploy
ssh mv-internal "cd ~/video-management && git pull"
ssh mv-internal "sudo cp -r ~/video-management/frontend/build/* /var/www/html/"
ssh mv-internal "sudo systemctl restart mv-internal"

# 4. Verify (mandatory)
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/api/health
ssh mv-internal "sudo journalctl -u mv-internal -n 10 --no-pager"
```

---

## 🧪 Test After Every Deploy

```bash
# Must return 200
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/api/conversations

# Check for errors
ssh mv-internal "sudo journalctl -u mv-internal -n 20 --no-pager"
```

If ANY test fails → STOP → Check logs → Rollback if needed

---

## 🔄 Rollback

```bash
git revert HEAD --no-edit
git push origin main
ssh mv-internal "cd ~/video-management && git pull"
ssh mv-internal "sudo systemctl restart mv-internal"
```

---

## 📍 Project Constants

| Key | Value |
|-----|-------|
| SSH_HOST | `mv-internal` |
| DOMAIN | `maurinventuresinternal.com` |
| SERVER_IP | `54.198.253.138` |
| REMOTE_PATH | `/home/ec2-user/mv-internal` |
| SERVICE_NAME | `mv-internal` |

### Local Paths
| Path | Contents |
|------|----------|
| `/frontend/src/` | React app |
| `/web/app.py` | Flask API (140KB, all routes) |
| `/scripts/` | Services and utilities |
| `/config/` | Credentials |
| `/_archive/` | Legacy frontend — don't modify |

---

## 💸 AI Cost Warning

This project has terabytes of transcripts. **Do not** pass full transcripts to AI.

| Approach | Cost per query |
|----------|----------------|
| Full transcripts (BAD) | $1.50+ |
| RAG with chunks (GOOD) | $0.01 |

Use RAG (Prompts 13-18 in instructions) before heavy AI usage.

---

## ✅ Session Start

Before making changes, confirm:

```
✅ Model: Claude Sonnet 4

Task: [What I will do]
Files: [What I will modify]
Preserving: [What must still work after]

Proceed? (yes/no)
```

Wait for approval.

---

## 🆘 If Everything Breaks

1. STOP making changes
2. Document what broke
3. Rollback using procedure above
4. If rollback fails, user will restore manually

## PROTECTED CODE - DO NOT MODIFY WITHOUT EXPLICIT PERMISSION

These changes have been debugged and verified. Do not revert, overwrite, refactor, or "clean up" unless explicitly asked.

### Authentication (LOCKED)
- `UserContext.tsx` - fetches real user from /api/auth/me
- Session uses 14-day persistent cookie, not session cookie
- 2FA required on every login
- Sidebar and all components read user from UserContext

### CORS (LOCKED)
- `web/app.py` CORS origins must include:
  - `http://localhost:3000`
  - `https://maurinventuresinternal.com`

### API Integration (LOCKED)
- `chat-screen.tsx` calls `/api/chat` - no setTimeout mocks
- `library-screen.tsx` calls `/api/library/videos` and `/api/library/audio` - no mock data imports
- All fetch() calls include `credentials: 'include'`

### Model Names (LOCKED)
- Anthropic: `claude-sonnet-4-20250514` (NOT claude-3-5-sonnet)
- Do not change model strings without explicit permission

### Data Sources (LOCKED)
- Library data comes from API, NOT from `src/app/data/library-data.ts`
- User data comes from UserContext, NOT hardcoded names
- Do not import mock data files in production components

### Script Generation UI (LOCKED)
- `ScriptGenerationResponse` component must be used for script responses
- Script responses must be transformed to `ScriptGenerationData` format
- Do not render script responses as plain markdown text

## Before Modifying Protected Code
1. STOP
2. Tell the user which protected file you need to change and why
3. Wait for explicit approval
4. Make the change
5. Verify you didn't break other protected items


# Claude Code Rules for MV Internal

**Last Updated:** 2026-01-05

---

## ⚠️ MODEL REQUIREMENT — CRITICAL COST CONTROL ⚠️

**MANDATORY: Use Claude Sonnet 4 (`claude-sonnet-4-20250514`) ONLY**

| Model | Status | Cost |
|-------|--------|------|
| Sonnet 4 (`claude-sonnet-4-20250514`) | ✅ USE THIS | ~$2-3/30min |
| Sonnet 4.5 (`claude-sonnet-4-5-20250929`) | ❌ DO NOT USE | ~$10/30min |
| Opus 4.5 (`claude-opus-4-5-20251101`) | ❌ DO NOT USE | ~$30/30min |

If session starts with wrong model, STOP and tell user to run:
```bash
export ANTHROPIC_MODEL=claude-sonnet-4-20250514
claude
```

---

## 🛑 CRITICAL: NO BREAKING CHANGES RULE 🛑

### Before ANY code change, you MUST:

1. **TEST THE CURRENT STATE FIRST**
   ```bash
   curl -s https://maurinventuresinternal.com/chat | head -20
   curl -s https://maurinventuresinternal.com/chat/recents | head -20
   curl -s https://maurinventuresinternal.com/projects | head -20
   ```

2. **IDENTIFY EXACTLY WHAT YOU'RE CHANGING**
   - List EVERY file you will modify
   - List EVERY function you will change
   - List EVERY CSS class you will modify

3. **PRESERVE WORKING FUNCTIONALITY**
   - If chat sending works → it MUST still work after
   - If sidebar renders → it MUST still render after
   - If navigation works → it MUST still work after

4. **ONE SMALL CHANGE AT A TIME**
   - Make ONE change
   - Deploy and TEST
   - Confirm it works
   - THEN make the next change

### NEVER do these in a single session:
- ❌ Refactor multiple files at once
- ❌ Change both HTML structure AND CSS at the same time
- ❌ Modify backend AND frontend simultaneously
- ❌ "While I'm here, let me also fix..."

---

## 🔒 PROTECTED FILES — EXTRA CAUTION REQUIRED

| File | What it does | Extra review required |
|------|--------------|----------------------|
| `web/app.py` | All routes and API | YES - test every endpoint |
| `web/templates/base.html` | Master layout | YES - affects ALL pages |
| `web/templates/_sidebar.html` | Sidebar | YES - appears everywhere |
| `web/static/js/shared.js` | Core JavaScript | YES - all interactivity |
| `web/static/css/base.css` | Core styles | YES - affects everything |

### Before modifying a PROTECTED FILE:

```
⚠️ PROTECTED FILE MODIFICATION

File: [filename]
Current behavior I am PRESERVING:
1. [Thing that works now]
2. [Another thing that works]

Specific change I am making:
- [Exact change, line numbers if possible]

I confirm this change will NOT break:
- [ ] Chat sending
- [ ] Chat loading
- [ ] Sidebar rendering
- [ ] Navigation
- [ ] API endpoints

Proceed? (yes/no)
```

---

## 🔍 TECHNICAL DEBT AUDIT PROTOCOL

### Triggering an Audit

When user says: "run audit", "analyze tech debt", "find duplication", or "check code quality"

### Audit Mode Rules

1. **DO NOT modify any code**
2. **Read and analyze only**
3. **Output report to `logs/audit_YYYYMMDD_HHMM.md`**

### Audit Report Format

```markdown
# Tech Debt Audit - [DATE]

## Summary
- Total issues found: X
- High priority: X
- Medium priority: X
- Low priority: X

## 1. Duplicated Code
| Location 1 | Location 2 | Lines | Similarity |
|------------|------------|-------|------------|
| file.py:45-60 | other.py:100-115 | 15 | ~90% |

## 2. Long Functions (>50 lines)
| File | Function | Lines | Recommendation |
|------|----------|-------|----------------|
| app.py | handle_chat() | 87 | Split into 2-3 functions |

## 3. Hardcoded Values (should be constants)
| File | Line | Value | Suggested Constant |
|------|------|-------|-------------------|
| app.py | 23 | "sk-xxx" | API_KEY |

## 4. Dead Code (potentially unused)
| File | Lines | Code | Confidence |
|------|-------|------|------------|
| shared.js | 200-215 | oldFunction() | 70% - verify before removing |

## 5. Pattern Inconsistencies
| Issue | Examples | Recommendation |
|-------|----------|----------------|
| Mixed quote styles | file1.py uses ", file2.py uses ' | Standardize on " |

## Recommended Fix Order
1. [Safest, highest impact fix]
2. [Next safest]
3. [etc.]
```

### After Audit

**STOP and wait for user to pick which item to fix.**

---

## 🔧 SAFE REFACTORING PROTOCOL

### BANNED WORDS - Never interpret these loosely

| Word | Problem | Say instead |
|------|---------|-------------|
| "Refactor" | Too vague, leads to rewrites | "Move function X to file Y" |
| "Clean up" | Subjective, causes deletions | "Add comments to function X" |
| "Simplify" | Removes "unnecessary" code that's needed | "Remove only variable Z" |
| "Improve" | License to rewrite everything | [Be specific or don't ask] |
| "Make it better" | Meaningless, dangerous | [Be specific] |

### Safe Refactoring Steps

**For ANY structural change, follow this exact sequence:**

#### Step 1: Create, Don't Modify
```
# NEVER modify working code directly
# ALWAYS create new version first

# Bad:
def get_users():  # Modified existing function
    new_implementation

# Good:
def get_users_v2():  # New function, old one untouched
    new_implementation
```

#### Step 2: Show Before Applying
```
Before making this change, I will show you:

CURRENT CODE (lines X-Y):
[existing code]

PROPOSED CODE:
[new code]

WHAT CHANGES:
- Line 45: added parameter
- Line 52: changed return value

WHAT STAYS THE SAME:
- All other logic unchanged

Apply this change? (yes/no)
```

#### Step 3: One Micro-Change at a Time

| Task | Break into |
|------|------------|
| Extract duplicated code | 1. Create shared function (don't use it yet) → 2. Update first usage → test → 3. Update second usage → test |
| Move function to new file | 1. Copy to new file → 2. Add import → test → 3. Delete from old file → test |
| Rename function | 1. Create alias with new name → 2. Update callers one by one → test each → 3. Remove old name |
| Change function signature | 1. Create new function with new signature → 2. Migrate callers one by one → 3. Deprecate old |

#### Step 4: Verify After Each Micro-Change
```bash
# After EVERY micro-change, run:
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/chat
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/chat/recents

# If not 200, STOP and rollback
```

### Refactoring Session Format

When user approves a fix from the audit:

```
🔧 REFACTORING: [Description]

Audit item: #[number] from [audit file]

This will be done in [N] micro-steps:

Step 1/N: [Exact action]
- File: [path]
- Change: [specific change]
- Risk: LOW

[Show code diff]

Apply step 1? (yes/no)
```

**Wait for approval before each step.**

---

## 🚫 REFACTORING HARD LIMITS

### Never Do These During Refactoring

- ❌ "While I'm here, I noticed..." — STOP, that's a separate task
- ❌ "This would be cleaner if..." — STOP, not approved
- ❌ "I'll also fix this small thing..." — STOP, scope creep
- ❌ Change ANY code not explicitly discussed
- ❌ Delete code because it "looks unused"
- ❌ Rename variables for "clarity"
- ❌ Reorder functions for "organization"
- ❌ Add error handling that "should be there"

### Always Do These During Refactoring

- ✅ Touch ONLY the code explicitly approved
- ✅ Show diff before applying
- ✅ Wait for approval at each step
- ✅ Test after each step
- ✅ Stop if anything breaks
- ✅ Keep old code until new code is verified

---

## 🧪 MANDATORY TESTING PROTOCOL

### After EVERY deployment:

```bash
# 1. Check service is running
ssh mv-internal "sudo systemctl status mv-internal"

# 2. Check for Python errors
ssh mv-internal "sudo journalctl -u mv-internal -n 20 --no-pager"

# 3. Test critical pages load
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/chat
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/chat/recents
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/projects

# 4. Test API endpoints
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/api/conversations
```

### If ANY test fails:
1. STOP immediately
2. Check logs for error
3. ROLLBACK if needed
4. Do NOT continue with more changes

---

## 📋 CHANGE SIZE LIMITS

| Change Type | Max Files | Max Lines Changed | Requires |
|-------------|-----------|-------------------|----------|
| Bug fix | 1-2 | <50 | Test after |
| Small feature | 2-3 | <100 | Test after |
| UI tweak | 1-2 | <30 | Visual check |
| Single refactor step | 1 | <20 | Approval + test |
| "Make it like X" | N/A | N/A | BREAK INTO PHASES |

### If user asks for large changes:

```
⚠️ LARGE CHANGE DETECTED

This request would modify [X] files and [Y] lines.

To prevent breaking the app, I recommend:

Phase 1: [Small specific change]
- Files: [list]
- Test: [how to verify]

Phase 2: [Next small change]
- Files: [list]  
- Test: [how to verify]

Which phase should I start with?
```

---

## 🔄 ROLLBACK PROCEDURE

If ANYTHING breaks after a deploy:

```bash
# 1. Check what broke
ssh mv-internal "sudo journalctl -u mv-internal -n 50 --no-pager"

# 2. See recent commits
git log --oneline -5

# 3. Revert the last commit
git revert HEAD --no-edit
git push origin main

# 4. Redeploy
ssh mv-internal "cd ~/video-management && git pull && rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'"
ssh mv-internal "sudo systemctl restart mv-internal"

# 5. Verify fixed
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/chat
```

---

## ✅ SESSION START — REQUIRED CONFIRMATION

At the START of every session, output:

```
✅ Model: Claude Sonnet 4 (claude-sonnet-4-20250514)

📋 TASK CONFIRMATION

I will:
1. [First thing - SPECIFIC]
2. [Second thing - SPECIFIC]

Files I will modify:
- path/to/file.html (lines X-Y)

I will NOT touch:
- [Files staying unchanged]

Current functionality I am PRESERVING:
- [Thing that works now]
- [Another thing that works]

Risk level: LOW / MEDIUM / HIGH

Proceed? (yes/no)
```

**Wait for user confirmation before proceeding.**

---

## 🚫 BANNED PATTERNS

```python
# ❌ BAD: Changing function signature that's called elsewhere
def get_config(key, default):  # Was: def get_config()

# ❌ BAD: Renaming CSS classes without updating all references  
.chat-input-box  # Was: .input-box

# ❌ BAD: Changing HTML structure that JS depends on
<div class="new-structure">  # JS expects old structure

# ❌ BAD: Removing code "to clean up"
# Deleted unused function  # It wasn't unused!

# ❌ BAD: "Improving" working code
# Refactored for clarity  # Now it's broken
```

```python
# ✅ GOOD: Add new code, don't modify working code
def get_config_v2(key, default):  # New function, old one still works

# ✅ GOOD: Add CSS classes, don't rename existing
.chat-input-box-new { }  # New class, old one still works

# ✅ GOOD: Test before AND after
# Tested: chat loads, messages send, sidebar renders
```

---

## 📍 PROJECT CONSTANTS — SINGLE SOURCE OF TRUTH

### Server & Deployment

| Key | Value |
|-----|-------|
| SSH_HOST | `mv-internal` |
| DOMAIN | `maurinventuresinternal.com` |
| SERVER_IP | `54.198.253.138` |
| SSH_USER | `ec2-user` |
| SSH_KEY | `~/Documents/keys/per_aspera/per-aspera-key.pem` |
| REMOTE_PATH | `/home/ec2-user/mv-internal` |
| GIT_REPO_PATH | `/home/ec2-user/video-management` |
| SERVICE_NAME | `mv-internal` |

### Local Development

| Key | Value |
|-----|-------|
| TEMPLATES | `web/templates/` |
| STATIC | `web/static/` |
| SHARED_JS | `web/static/js/shared.js` |
| APP_ENTRY | `web/app.py` |

### URLs (Production)

| Route | URL |
|-------|-----|
| Home | `https://maurinventuresinternal.com/chat` |
| Chats List | `https://maurinventuresinternal.com/chat/recents` |
| Projects List | `https://maurinventuresinternal.com/projects` |
| Single Project | `https://maurinventuresinternal.com/project/{id}` |
| Single Chat | `https://maurinventuresinternal.com/chat/{id}` |

---

## 🚀 CANONICAL DEPLOY SEQUENCE

```bash
# 1. Commit with SPECIFIC message
git add -A && git commit -m "Fix: [exact thing fixed]"

# 2. Push
git push origin main

# 3. Deploy
ssh mv-internal "cd ~/video-management && git pull && rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'"

# 4. Restart
ssh mv-internal "sudo systemctl restart mv-internal"

# 5. VERIFY (mandatory)
curl -s -o /dev/null -w "%{http_code}" https://maurinventuresinternal.com/chat
ssh mv-internal "sudo journalctl -u mv-internal -n 10 --no-pager"
```

---

## 📝 SESSION LOGGING

Logs go in `/logs` folder, NOT project root.

| Situation | Create Log? |
|-----------|-------------|
| Major feature completed | ✅ Yes |
| Complex bug fix | ✅ Yes |
| Audit completed | ✅ Yes (audit report) |
| Refactoring session | ✅ Yes (what changed) |
| Small single-file change | ❌ No |
| Quick config tweak | ❌ No |

---

## 🔧 DEBUGGING

| Symptom | Check |
|---------|-------|
| SSH fails | ~/.ssh/config |
| Service won't start | `sudo journalctl -u mv-internal -n 50` |
| Changes not appearing | Did you restart service? |
| Sidebar inconsistent | Must use `_sidebar.html` partial |
| API returns error | Check app.py function signatures |
| JS not working | Check browser console, verify selectors exist |

---

## 🔌 SSH CONFIG

```
Host mv-internal
    HostName 54.198.253.138
    User ec2-user
    IdentityFile ~/Documents/keys/per_aspera/per-aspera-key.pem
```

---

## 🆘 EMERGENCY

If everything is broken and you can't fix it:

1. STOP making changes
2. Document what broke
3. User will restore from backup or fix manually

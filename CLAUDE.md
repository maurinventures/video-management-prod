# Claude Code Rules for MV Internal

**Last Updated:** 2026-01-05 08:20 UTC

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

## SESSION START — REQUIRED CONFIRMATION

At the START of every session, output:

```
✅ Model: Claude Sonnet 4 (claude-sonnet-4-20250514)

📋 TASK CONFIRMATION

I will:
1. [First thing]
2. [Second thing]
3. [Third thing]

Files I will modify:
- path/to/file.html

I will NOT:
- [Out of scope items]

Proceed? (yes/no)
```

**Wait for user confirmation before proceeding.**

**MANDATORY:** After user confirmation, immediately explore the current codebase structure relative to CLAUDE.md guidelines using the Task tool with subagent_type=Explore.

---

## SESSION LOGGING — DO NOT BLOAT THE REPO

### ⚠️ IMPORTANT: Logs go in `/logs` folder, NOT project root

```bash
# CORRECT - logs folder (gitignored)
mkdir -p logs
logs/session_20260105_081500.md

# WRONG - project root (bloats repo)
session_20260105_081500.md  # ❌ DO NOT CREATE HERE
```

### Ensure .gitignore includes:

```
logs/
session_*.md
```

### When to create session logs

| Situation | Create Log? |
|-----------|-------------|
| Major feature completed | ✅ Yes |
| Complex bug fix | ✅ Yes |
| Small single-file change | ❌ No |
| Quick config tweak | ❌ No |
| User says "skip the log" | ❌ No |

### Log format (keep it brief)

```bash
mkdir -p logs
cat > "logs/session_$(date +%Y%m%d_%H%M%S).md" << 'EOF'
# Session: [DATE]
## Summary
[1-2 sentences max]
## Changes
- file.html: [brief description]
## Status
Working / Needs follow-up
EOF
```

**NO verbose templates. Keep logs SHORT.**

---

## PROJECT CONSTANTS — SINGLE SOURCE OF TRUTH

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

## ARCHITECTURE — SINGLE SOURCE OF TRUTH

### Principle

Every component, style, and data source must be defined **ONCE** and reused everywhere.

### Template Architecture

| File | Purpose |
|------|---------|
| `base.html` | Master layout — ALL templates extend this |
| `_sidebar.html` | Sidebar partial — included in base.html |
| `_dropdown_menu.html` | Shared dropdown — included in base.html |

**Pattern:**
```html
<!-- base.html includes shared components ONCE -->
{% include '_sidebar.html' %}

<!-- Every page extends base.html -->
{% extends 'base.html' %}
{% block content %}...{% endblock %}
```

### CSS Architecture

| File | Purpose |
|------|---------|
| `base.css` | Variables, reset, typography |
| `sidebar.css` | Sidebar styles ONLY |
| `components.css` | Buttons, inputs, cards, menus |

**Rules:**
- NO inline `<style>` blocks
- NO duplicate CSS across files
- One component = one place in CSS

### JavaScript Architecture

- ALL shared code in `shared.js`
- Use event delegation for dynamic elements
- No inline `onclick` handlers

### Flask Architecture

```python
def get_sidebar_data():
    """Call in EVERY route"""
    return {
        'recent_projects': get_projects_with_recent_chats(),
        'standalone_chats': get_standalone_recent_chats(),
        'user': get_current_user()
    }

def render_with_sidebar(template, active_page, **kwargs):
    context = get_sidebar_data()
    context['active_page'] = active_page
    context.update(kwargs)
    return render_template(template, **context)

# All routes use this:
@app.route('/videos')
def videos():
    return render_with_sidebar('videos.html', active_page='videos', videos=get_all_videos())
```

---

## RULES — DO NOT VIOLATE

### Rule 1: NEVER INVENT

Never invent hostnames, paths, endpoints, CSS classes. If not in this file or existing code, **ASK**.

### Rule 2: VERIFY BEFORE EXECUTE

```bash
echo "Will run: ssh $SSH_HOST ..."
# Then execute
```

### Rule 3: CANONICAL DEPLOY SEQUENCE

```bash
git add -A && git commit -m "Description"
git push origin main
ssh mv-internal "cd ~/video-management && git pull && rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'"
ssh mv-internal "sudo systemctl restart mv-internal"
```

### Rule 4: ONE CHANGE AT A TIME

Never batch multiple unrelated changes.

### Rule 5: NO DUPLICATION

Before adding code, check if similar exists:
```bash
grep -rn "pattern" web/
```

### Rule 6: CSS/HTML CONSISTENCY

```bash
grep -n "\.classname" web/templates/*.html web/static/css/*.css
```

### Rule 7: SERVER-SIDE RENDERING FOR SIDEBAR

Sidebar must be Jinja-rendered, not JavaScript-fetched.

### Rule 8: PARTIALS FOR SHARED COMPONENTS

Any HTML on multiple pages → extract to partial.

---

## TESTING CHECKLIST

After ANY change:

- [ ] Hard refresh `/chat` — no console errors
- [ ] Sidebar renders immediately — no jitter
- [ ] Sidebar IDENTICAL on all pages
- [ ] Service restarts without error

---

## SESSION END — REQUIRED VALIDATION

At the END of every session, **MANDATORY:**

Explore the current codebase structure relative to CLAUDE.md guidelines using the Task tool with subagent_type=Explore to verify:

- [ ] Architecture principles are still being followed
- [ ] No new duplication was introduced
- [ ] All changes align with established patterns
- [ ] Single source of truth maintained
- [ ] Template/CSS/JS structure remains consistent

Output a brief validation summary of adherence to CLAUDE.md guidelines.

---

## ROLLBACK PROCEDURE

```bash
ssh mv-internal "sudo journalctl -u mv-internal -n 50 --no-pager"
git log --oneline -10
git revert HEAD --no-edit
git push origin main
ssh mv-internal "cd ~/video-management && git pull && rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'"
ssh mv-internal "sudo systemctl restart mv-internal"
```

---

## SSH CONFIG

```
Host mv-internal
    HostName 54.198.253.138
    User ec2-user
    IdentityFile ~/Documents/keys/per_aspera/per-aspera-key.pem
```

---

## DEBUGGING

| Symptom | Check |
|---------|-------|
| SSH fails | ~/.ssh/config |
| Service won't start | `sudo journalctl -u mv-internal -n 50` |
| Changes not appearing | Did you restart service? |
| Sidebar inconsistent | Must use `_sidebar.html` partial |

---

## SECRETS

```bash
# Decrypt
openssl aes-256-cbc -d -pbkdf2 -in config/credentials.yaml.enc -out config/credentials.yaml

# Re-encrypt
openssl aes-256-cbc -salt -pbkdf2 -in config/credentials.yaml -out config/credentials.yaml.enc
```

---

## CLEANUP TASKS

### Remove existing session logs from repo root

```bash
# Move existing logs to logs folder
mkdir -p logs
mv session_*.md logs/ 2>/dev/null

# Add to gitignore if not already
echo "logs/" >> .gitignore
echo "session_*.md" >> .gitignore

# Commit cleanup
git add -A && git commit -m "Move session logs to /logs folder, update gitignore"
git push origin main
```

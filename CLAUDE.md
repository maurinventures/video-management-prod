# Claude Code Rules for MV Internal

**Last Updated:** 2026-01-05 04:00 UTC

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

---

## PROJECT CONSTANTS — SINGLE SOURCE OF TRUTH

### Server & Deployment

| Key | Value | Notes |
|-----|-------|-------|
| SSH_HOST | `mv-internal` | SSH config alias |
| DOMAIN | `maurinventuresinternal.com` | NO subdomain |
| SERVER_IP | `54.198.253.138` | EC2 instance |
| SSH_USER | `ec2-user` | |
| SSH_KEY | `~/Documents/keys/per_aspera/per-aspera-key.pem` | |
| REMOTE_PATH | `/home/ec2-user/mv-internal` | NOT /var/www/ |
| GIT_REPO_PATH | `/home/ec2-user/video-management` | Git repo |
| SERVICE_NAME | `mv-internal` | systemd service |

### Local Development

| Key | Value |
|-----|-------|
| LOCAL_WEB_PATH | `web/` |
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

Every component, style, and data source must be defined **ONCE** and reused everywhere. Duplication leads to inconsistency.

### Template Architecture

| File | Purpose | Used By |
|------|---------|---------|
| `base.html` | Master layout (head, body, scripts) | ALL templates extend this |
| `_sidebar.html` | Sidebar partial | Included in base.html |
| `_dropdown_menu.html` | Shared dropdown menu | Included in base.html |
| `_chat_input.html` | Chat input component | Chat pages |
| `_message.html` | Chat message component | Chat pages |

**Template Pattern:**
```html
<!-- base.html -->
<!DOCTYPE html>
<html>
<head>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/base.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/sidebar.css') }}">
    <link rel="stylesheet" href="{{ url_for('static', filename='css/components.css') }}">
    {% block head %}{% endblock %}
</head>
<body>
    <div class="app-layout">
        {% include '_sidebar.html' %}
        <main class="main-content">
            {% block content %}{% endblock %}
        </main>
    </div>
    {% include '_dropdown_menu.html' %}
    <script src="{{ url_for('static', filename='js/shared.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>

<!-- Any page (e.g., videos.html) -->
{% extends 'base.html' %}
{% block title %}Videos - MV Internal{% endblock %}
{% block content %}
<div class="videos-page">
    <!-- Page-specific content only -->
</div>
{% endblock %}
```

### CSS Architecture

| File | Purpose |
|------|---------|
| `base.css` | Variables, reset, typography |
| `layout.css` | App structure, grid |
| `sidebar.css` | Sidebar styles ONLY |
| `components.css` | Buttons, inputs, cards, menus, tables |

**Rules:**
- NO inline `<style>` blocks in templates
- NO duplicate CSS across files
- Use CSS variables for colors, sizes
- One component = one place in CSS

### JavaScript Architecture

| File | Purpose |
|------|---------|
| `shared.js` | ALL shared functionality |

**shared.js Structure:**
```javascript
// Sidebar management
const Sidebar = {
    init() { },
    toggle(sectionId) { },
    saveState() { },
    restoreState() { }
};

// Dropdown menu management  
const DropdownMenu = {
    show(event, targetId, targetType) { },
    hide() { },
    handleAction(action) { }
};

// Chat actions
const ChatActions = {
    star(chatId) { },
    rename(chatId) { },
    delete(chatId) { }
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    Sidebar.init();
});
```

### Flask Architecture

**Every route must use shared helper:**

```python
# In app.py

def get_sidebar_data():
    """Get data needed for sidebar - call in EVERY route"""
    return {
        'recent_projects': get_projects_with_recent_chats(),
        'standalone_chats': get_standalone_recent_chats(),
        'user': get_current_user()
    }

def render_with_sidebar(template, active_page, **kwargs):
    """Render any template with sidebar data included"""
    context = get_sidebar_data()
    context['active_page'] = active_page
    context.update(kwargs)
    return render_template(template, **context)

# All routes use this pattern:
@app.route('/videos')
def videos():
    return render_with_sidebar('videos.html',
        active_page='videos',
        videos=get_all_videos()
    )
```

### Why This Matters

| Problem | Cause | Solution |
|---------|-------|----------|
| Sidebar looks different on /videos vs /chat | Duplicate sidebar HTML in each template | Single `_sidebar.html` partial |
| CSS inconsistent across pages | Inline styles or duplicate CSS | Single CSS files, no inline |
| Forgot to pass sidebar data to one route | Each route manually builds context | `render_with_sidebar()` helper |
| Changed button style, only updated one place | Button CSS in multiple files | Single `components.css` |

---

## RULES — DO NOT VIOLATE

### Rule 1: NEVER INVENT

Never invent, guess, or interpolate:
- Hostnames or subdomains
- File paths
- API endpoints
- SSH aliases
- CSS class names

If a value is not in this file or in existing code, **ASK**.

### Rule 2: VERIFY BEFORE EXECUTE

Before running any destructive or remote command:
```bash
echo "Will run: ssh $SSH_HOST ..."
# Then execute
```

### Rule 3: CANONICAL DEPLOY SEQUENCE

```bash
# 1. Commit and push
git add -A && git commit -m "Description of change"
git push origin main

# 2. Pull on server and sync
ssh mv-internal "cd ~/video-management && git pull && rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'"

# 3. Restart service
ssh mv-internal "sudo systemctl restart mv-internal"

# 4. Verify running
ssh mv-internal "sudo systemctl status mv-internal --no-pager | head -5"
```

### Rule 4: ONE CHANGE AT A TIME

1. State what you will change and why
2. Show the exact before/after
3. Make the change
4. Verify it works
5. Commit with descriptive message
6. Provide rollback command

**Never batch multiple unrelated changes.**

### Rule 5: NO DUPLICATION

Before adding ANY code:
```bash
# Check if similar code exists
grep -rn "similar pattern" web/

# Check if it belongs in shared location
# - HTML component → create partial in templates/
# - CSS → add to appropriate .css file
# - JavaScript → add to shared.js
# - Flask logic → add helper function
```

### Rule 6: CSS/HTML CONSISTENCY

Before using a CSS class:
```bash
grep -n "\.classname" web/templates/*.html web/static/css/*.css
```

**Use existing class names exactly. Never create variants.**

### Rule 7: SERVER-SIDE RENDERING FOR SIDEBAR

Sidebar content must be **server-rendered via Jinja**, not JavaScript fetch.

**Why:** JavaScript-loaded content causes layout jitter.

### Rule 8: PARTIALS FOR SHARED COMPONENTS

Any HTML that appears on multiple pages MUST be a partial:

```bash
# Check if component is duplicated
grep -l "component-html" web/templates/*.html | wc -l
# If > 1, extract to partial
```

---

## TESTING CHECKLIST

After ANY frontend change:

- [ ] Hard refresh `/chat` — no console errors
- [ ] Sidebar renders immediately — no jitter
- [ ] Click sidebar items — navigation works
- [ ] Collapse/expand sections — state persists
- [ ] Sidebar IDENTICAL on /chat, /projects, /videos, /audio, /personas

After ANY backend change:

- [ ] Service restarts without error
- [ ] `curl https://maurinventuresinternal.com/chat` returns 200

---

## AUTOMATED SITE AUDIT

### Run Audit

```bash
node tests/full-site-audit.js
```

### When to Run

| Situation | Run Audit? |
|-----------|------------|
| After fixing navigation bugs | ✅ Yes |
| After changing sidebar | ✅ Yes |
| After adding new routes | ✅ Yes |
| Before marking feature complete | ✅ Yes |

---

## ROLLBACK PROCEDURE

```bash
# 1. Check what broke
ssh mv-internal "sudo journalctl -u mv-internal -n 50 --no-pager"

# 2. Find last working commit
git log --oneline -10

# 3. Revert
git revert HEAD --no-edit

# 4. Redeploy
git push origin main
ssh mv-internal "cd ~/video-management && git pull && rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'"
ssh mv-internal "sudo systemctl restart mv-internal"
```

---

## SSH CONFIG REFERENCE

```
Host mv-internal
    HostName 54.198.253.138
    User ec2-user
    IdentityFile ~/Documents/keys/per_aspera/per-aspera-key.pem
```

---

## DEBUGGING CHECKLIST

| Symptom | Check |
|---------|-------|
| SSH fails | `~/.ssh/config` matches above |
| Path not found | Use `/home/ec2-user/mv-internal` |
| Service won't start | `sudo journalctl -u mv-internal -n 50` |
| Changes not appearing | Did you `systemctl restart`? |
| CSS not working | Grep to verify class name |
| Sidebar inconsistent | Must use `_sidebar.html` partial |
| Sidebar jitters | Must be server-rendered |

---

## SESSION LOGGING — REQUIRED

At END of every session:

```bash
SESSION_LOG="session_$(date +%Y%m%d_%H%M%S).md"
cat > "$SESSION_LOG" << 'EOF'
# Session Log: [DATE]

## Model Used
claude-sonnet-4-20250514

## Summary
[What was accomplished]

## Changes Made
| File | Change |
|------|--------|
| path/to/file | Description |

## Verification
- [ ] Tested X — PASS/FAIL
EOF
echo "Session log: $SESSION_LOG"
```

---

## SECRETS

```bash
# Decrypt
openssl aes-256-cbc -d -pbkdf2 -in config/credentials.yaml.enc -out config/credentials.yaml

# Re-encrypt
openssl aes-256-cbc -salt -pbkdf2 -in config/credentials.yaml -out config/credentials.yaml.enc
```

---

## AFTER EVERY SESSION

1. Create session log
2. Update CHANGELOG.md
3. Inform user of log location

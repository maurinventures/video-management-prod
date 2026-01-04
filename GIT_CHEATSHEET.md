# Git Cheat Sheet for MV Internal

A simple guide for working with this repo.

---

## First Time Setup (Once Only)

```bash
# Clone the repo to your computer
git clone https://github.com/maurinventures/video-management-prod.git

# Go into the folder
cd video-management-prod
```

---

## Daily Workflow

### Before You Start Working
```bash
# Get the latest changes from GitHub
git pull
```

### After You Make Changes
```bash
# See what files you changed
git status

# Stage all your changes
git add -A

# Save your changes with a message
git commit -m "Describe what you changed"

# Send your changes to GitHub
git push
```

### One-Liner (Stage + Commit + Push)
```bash
git add -A && git commit -m "Your message here" && git push
```

---

## Common Commands

| Command | What It Does |
|---------|--------------|
| `git status` | See what files changed |
| `git pull` | Download latest from GitHub |
| `git add -A` | Stage all changes |
| `git add filename` | Stage one specific file |
| `git commit -m "msg"` | Save changes locally |
| `git push` | Upload to GitHub |
| `git log --oneline -5` | See last 5 commits |
| `git diff` | See what changed (before staging) |

---

## Fixing Common Issues

### "I forgot to pull and now I can't push"
```bash
git pull --rebase
git push
```

### "I want to undo my last commit" (before pushing)
```bash
git reset --soft HEAD~1
```

### "I want to discard all my local changes"
```bash
git checkout .
```

### "I accidentally edited the wrong file"
```bash
git checkout filename
```

---

## Deploying to Production

After pushing to GitHub, deploy to the live server:

```bash
# Connect to server
ssh -i ~/Documents/keys/per_aspera/per-aspera-key.pem ec2-user@54.198.253.138

# Pull latest code
cd ~/video-management && git pull

# Sync to production directory
rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'

# Restart the app
sudo systemctl restart mv-internal.service

# Check it's running
sudo systemctl status mv-internal.service
```

See `INFRASTRUCTURE.md` for full deployment details.

---

## Quick Reference

```
YOUR COMPUTER                    GITHUB                      SERVER
     │                             │                           │
     │  git push                   │                           │
     │ ─────────────────────────>  │                           │
     │                             │                           │
     │  git pull                   │      ssh + git pull       │
     │ <─────────────────────────  │ ───────────────────────>  │
     │                             │                           │
```

---

## Golden Rules

1. **Always `git pull` before starting work** - Get the latest changes first
2. **Commit often** - Small commits are easier to understand
3. **Write clear commit messages** - Future you will thank you
4. **Push when you're done** - Don't leave commits sitting locally

---

## Need Help?

```bash
# Get help on any command
git help <command>

# Example
git help commit
```

Or ask in the team chat!

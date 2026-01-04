# Claude Code Rules for MV Internal

## Deployment

**Always deploy to production**: https://maurinventuresinternal.com

Never use localhost for testing. After making changes, deploy to the EC2 server.

### EC2 Server
- **IP Address**: 54.198.253.138
- **SSH Key**: `~/Documents/keys/per_aspera/per-aspera-key.pem`
- **User**: ec2-user

### Deploy Commands
```bash
# SSH to server (using alias from ~/.ssh/config)
ssh mv-internal

# Or with full command:
ssh -i ~/Documents/keys/per_aspera/per-aspera-key.pem ec2-user@54.198.253.138

# Pull and sync
cd ~/video-management && git pull
rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'

# Restart service
sudo systemctl restart mv-internal.service
```

Or as a one-liner:
```bash
ssh mv-internal "cd ~/video-management && git pull && rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' && sudo systemctl restart mv-internal.service"
```

## Secrets

Credentials are **encrypted** with OpenSSL AES-256-CBC and stored in `config/credentials.yaml.enc`.

- **Encrypted file**: `config/credentials.yaml.enc` (committed to git)
- **Template**: `config/credentials.yaml.template` (shows structure)
- **Decrypted file**: `config/credentials.yaml` (gitignored, never commit)

### What's encrypted
- AWS credentials (S3, RDS access)
- Database connection (PostgreSQL on RDS)
- API keys (OpenAI, Anthropic, Notion)
- EC2 instance details

### To decrypt
```bash
openssl aes-256-cbc -d -pbkdf2 -in config/credentials.yaml.enc -out config/credentials.yaml
# Password: Ask project owner or check 1Password
```

### To re-encrypt after changes
```bash
openssl aes-256-cbc -salt -pbkdf2 -in config/credentials.yaml -out config/credentials.yaml.enc
```

## Database

- **Type**: PostgreSQL on AWS RDS
- **Credentials**: In encrypted `config/credentials.yaml.enc`

## Project Structure

- `web/app.py` - Main Flask application
- `web/templates/` - Jinja2 HTML templates
- `scripts/` - CLI tools and database models
- `config/` - Settings and encrypted credentials

## Code Style

- Use existing patterns from the codebase
- Keep UI consistent across all pages (sidebar, styling, interactions)
- Don't create unnecessary files or documentation unless asked

## Git

- Commit changes with clear messages
- Push to `main` branch
- Deploy after pushing

## After Every Task

Append a summary to `/docs/CHANGELOG.md` with:
- What you changed and why
- Files modified
- Any issues encountered
- Current state of the feature

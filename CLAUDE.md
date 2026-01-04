# Claude Code Rules for MV Internal

## Deployment

**Always deploy to production**: https://maurinventuresinternal.com

Never use localhost for testing. After making changes, deploy to the EC2 server:

```bash
# SSH to server
ssh -i ~/Documents/keys/per_aspera/per-aspera-key.pem ec2-user@54.198.253.138

# Pull and sync
cd ~/video-management && git pull
rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'

# Restart service
sudo systemctl restart mv-internal.service
```

## Database

- **Host**: PostgreSQL on AWS RDS
- **Credentials**: Stored encrypted in `config/credentials.yaml.enc`
- **Decrypt with**: `openssl aes-256-cbc -d -pbkdf2 -in config/credentials.yaml.enc -out config/credentials.yaml`

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

# MV Internal Infrastructure
**Last Updated: 2026-01-04**

---

## QUICK REFERENCE

| Service | Value |
|---------|-------|
| **Domain** | https://maurinventuresinternal.com |
| **EC2 IP** | 54.198.253.138 |
| **RDS Host** | mv-database.cshawwjevydx.us-east-1.rds.amazonaws.com |
| **S3 Bucket** | mv-brain |

---

## DOMAIN & WEB

| Item | Value |
|------|-------|
| Domain | maurinventuresinternal.com |
| SSL | Let's Encrypt (auto-renew via Certbot) |
| Web Server | nginx (port 80/443) |
| App Server | gunicorn (port 5001) |
| App Service | mv-internal.service |

---

## EC2 INSTANCE

| Item | Value |
|------|-------|
| Name | mv-brain |
| Instance ID | i-030b974c11cf175cd |
| Public IP | 54.198.253.138 |
| Region | us-east-1 |
| SSH User | ec2-user |
| SSH Key | ~/Documents/keys/per_aspera/per-aspera-key.pem |
| Production Dir | /home/ec2-user/mv-internal |
| Git Repo Dir | /home/ec2-user/video-management |

### SSH Command
```bash
ssh -i ~/Documents/keys/per_aspera/per-aspera-key.pem ec2-user@54.198.253.138
```

---

## RDS DATABASE

| Item | Value |
|------|-------|
| Instance ID | mv-database |
| Host | mv-database.cshawwjevydx.us-east-1.rds.amazonaws.com |
| Port | 5432 |
| Engine | PostgreSQL 17 |
| Database | video_management |
| Username | postgres |
| **Password** | See `config/credentials.yaml` |

### Connect Command
```bash
# Password is in config/credentials.yaml
psql -h mv-database.cshawwjevydx.us-east-1.rds.amazonaws.com -U postgres -d video_management
```

---

## S3 BUCKET

| Item | Value |
|------|-------|
| Bucket Name | mv-brain |
| Region | us-east-1 |
| Prefixes | videos/, transcripts/, clips/, compiled/ |

---

## AWS CREDENTIALS

| Item | Value |
|------|-------|
| Access Key ID | See `~/.aws/credentials` or `config/credentials.yaml` |
| Secret Access Key | See `~/.aws/credentials` or `config/credentials.yaml` |
| Region | us-east-1 |

---

## API KEYS

| Service | Location |
|---------|----------|
| OpenAI | See `config/credentials.yaml` |
| Anthropic | See `config/credentials.yaml` |
| Notion | See `config/credentials.yaml` |

---

## CREDENTIALS FILE ENCRYPTION

| Item | Value |
|------|-------|
| Encrypted File | config/credentials.yaml.enc |
| **Encryption Password** | Ask team lead or check 1Password |

### Decrypt
```bash
openssl aes-256-cbc -d -pbkdf2 -in config/credentials.yaml.enc -out config/credentials.yaml
# Enter password when prompted
```

### Encrypt
```bash
openssl aes-256-cbc -salt -pbkdf2 -in config/credentials.yaml -out config/credentials.yaml.enc
# Use the same password as decrypt
```

---

## SYSTEMD SERVICES

| Service | Status | Port | Directory |
|---------|--------|------|-----------|
| mv-internal.service | **ACTIVE** | 5001 | ~/mv-internal |
| video-management.service | DISABLED | 5001 | ~/video-management |
| gunicorn.service | DISABLED | 5000 | ~/projects/team-email-processor |

### Service Commands
```bash
# Restart app
sudo systemctl restart mv-internal.service

# View logs
sudo journalctl -u mv-internal.service -f

# Check status
sudo systemctl status mv-internal.service
```

---

## DEPLOYMENT

To deploy changes to production:
```bash
# 1. SSH to EC2
ssh -i ~/Documents/keys/per_aspera/per-aspera-key.pem ec2-user@54.198.253.138

# 2. Pull latest code
cd ~/video-management && git pull

# 3. Sync to production directory
rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'

# 4. Restart service
sudo systemctl restart mv-internal.service
```

---

## DIRECTORY STRUCTURE (EC2)

```
/home/ec2-user/
├── mv-internal/           # PRODUCTION (served by nginx)
│   ├── config/
│   │   └── credentials.yaml
│   ├── web/
│   │   └── app.py
│   └── ...
├── video-management/      # GIT REPO (source of truth)
│   ├── .git/
│   ├── config/
│   └── ...
└── INFRASTRUCTURE.md      # This reference doc
```

---

## NOTES

1. **Production uses ~/mv-internal**, NOT ~/video-management
2. Always sync changes from video-management to mv-internal before restarting
3. The video-management.service is DISABLED to prevent port conflicts
4. Credentials are stored in ~/mv-internal/config/credentials.yaml (unencrypted on server)

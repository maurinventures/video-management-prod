# Configuration

## Encrypted Credentials

The `credentials.yaml.enc` file contains encrypted secrets.

### To decrypt:
```bash
openssl aes-256-cbc -d -pbkdf2 -in config/credentials.yaml.enc -out config/credentials.yaml
# Password: Ask team lead or check 1Password
```

### To encrypt after changes:
```bash
openssl aes-256-cbc -salt -pbkdf2 -in config/credentials.yaml -out config/credentials.yaml.enc
# Use same password as decrypt
```

## Key Credentials Reference

All credentials are stored in `credentials.yaml` after decryption:
- RDS Database (host, username, password)
- AWS Keys
- API Keys (OpenAI, Anthropic, Notion)

### EC2 Production
- IP: 54.198.253.138
- SSH Key: ~/Documents/keys/per_aspera/per-aspera-key.pem
- Production Dir: /home/ec2-user/mv-internal
- Service: mv-internal.service

## Deployment

To deploy changes to production:
```bash
# SSH to EC2
ssh -i ~/Documents/keys/per_aspera/per-aspera-key.pem ec2-user@54.198.253.138

# Pull latest code
cd ~/video-management && git pull

# Sync to production directory
rsync -av ~/video-management/ ~/mv-internal/ --exclude='.git' --exclude='__pycache__' --exclude='*.pyc'

# Restart the service
sudo systemctl restart mv-internal.service
```

See `INFRASTRUCTURE.md` for full server documentation.

# Configuration

## Encrypted Credentials

The `credentials.yaml.enc` file contains encrypted secrets.

### To decrypt:
```bash
openssl aes-256-cbc -d -pbkdf2 -in config/credentials.yaml.enc -out config/credentials.yaml
```

### To encrypt after changes:
```bash
openssl aes-256-cbc -salt -pbkdf2 -in config/credentials.yaml -out config/credentials.yaml.enc
```

Password: Ask the project owner.

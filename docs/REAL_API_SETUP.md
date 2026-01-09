# 🔑 Real API Keys Setup Guide

## Option 1: Automated Setup (Recommended)

Run the interactive setup script:

```bash
python3 setup_api_keys.py
```

This script will:
1. Guide you through getting API keys
2. Test your keys (if possible)
3. Create the credentials file automatically
4. Verify integration

## Option 2: Manual Setup

### Step 1: Get Your API Keys

**🎯 Anthropic (Claude) API Key:**
1. Go to: https://console.anthropic.com/
2. Create account or sign in
3. Navigate to "API Keys"
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-`)

**💡 OpenAI (GPT) API Key:**
1. Go to: https://platform.openai.com/api-keys
2. Create account or sign in
3. Click "Create new secret key"
4. Give it a name (e.g., "Internal Platform")
5. Copy the key (starts with `sk-`)

### Step 2: Create Credentials File

```bash
cd /Users/josephs./internal-platform
cp config/credentials.yaml.template config/credentials.yaml
```

Edit `config/credentials.yaml`:

```yaml
# AI API Keys (REQUIRED)
anthropic:
  api_key: sk-ant-YOUR_ANTHROPIC_API_KEY_HERE

openai:
  api_key: sk-YOUR_OPENAI_API_KEY_HERE

# Other services (can be left as placeholders)
aws:
  access_key_id: YOUR_AWS_ACCESS_KEY_ID
  secret_access_key: YOUR_AWS_SECRET_ACCESS_KEY

rds:
  host: YOUR_RDS_ENDPOINT.us-east-1.rds.amazonaws.com
  username: YOUR_DB_USERNAME
  password: YOUR_DB_PASSWORD
```

### Step 3: Restart Flask Server

```bash
# Stop current server (Ctrl+C if running)
python3 web/app.py
```

### Step 4: Test Real API Integration

```bash
python3 test_ai_integration.py
```

You should see real AI responses instead of "Demo Response" messages!

## 🧪 Quick Test Commands

**Test Anthropic (Claude):**
```bash
curl -X POST http://localhost:5001/api/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello Claude!", "model": "claude-haiku"}'
```

**Test OpenAI (GPT):**
```bash
curl -X POST http://localhost:5001/api/chat/test \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello GPT!", "model": "gpt-3.5-turbo"}'
```

## 💰 API Costs (Approximate)

| Model | Provider | Cost per 1M tokens |
|-------|----------|-------------------|
| Claude Haiku | Anthropic | $0.25 (input) / $1.25 (output) |
| Claude Sonnet | Anthropic | $3 (input) / $15 (output) |
| Claude Opus | Anthropic | $15 (input) / $75 (output) |
| GPT-3.5 Turbo | OpenAI | $0.50 (input) / $1.50 (output) |
| GPT-4 Turbo | OpenAI | $10 (input) / $30 (output) |
| GPT-4o | OpenAI | $2.50 (input) / $10 (output) |

**Tip:** Start with cheaper models (Claude Haiku, GPT-3.5) for testing!

## 🔒 Security Notes

- **Never commit** `credentials.yaml` to version control
- Store API keys securely
- Use environment variables in production
- Monitor usage on provider dashboards

## ✅ Expected Results

Once configured, you should see:

```
🤖 AI Model Integration Test:
✅ Claude Sonnet → Real AI Response: "Hello! I'm Claude..."
✅ GPT-4 Omni → Real AI Response: "Hi there! I'm GPT-4..."
```

Instead of:
```
🤖 Demo Response from CLAUDE-SONNET
```

## 🆘 Troubleshooting

**"Still seeing demo responses":**
- Check credentials.yaml file exists and has correct keys
- Restart Flask server after adding keys
- Verify no typos in API keys

**"API key not working":**
- Check key format (sk-ant-... for Anthropic, sk-... for OpenAI)
- Verify account has credits/billing set up
- Test keys on provider websites first

**"Server errors":**
- Check Flask server logs
- Verify all required packages installed
- Make sure credentials.yaml is readable

## 📞 Need Help?

1. Run the automated setup: `python3 setup_api_keys.py`
2. Check server logs for detailed error messages
3. Verify API keys work on provider websites first
4. Test with cheapest models first (Claude Haiku, GPT-3.5)
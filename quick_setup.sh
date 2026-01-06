#!/bin/bash
# Quick API Keys Setup Script
# Run this after getting your API keys

echo "🔑 Quick API Keys Setup"
echo "======================="
echo ""

# Check if template exists
if [ ! -f "config/quick_credentials_template.yaml" ]; then
    echo "❌ Template file not found"
    exit 1
fi

echo "📝 Please enter your API keys:"
echo ""

# Get Anthropic key
read -p "🎯 Anthropic API key (sk-ant-...): " ANTHROPIC_KEY
if [[ ! $ANTHROPIC_KEY =~ ^sk-ant- ]]; then
    echo "❌ Invalid Anthropic key format"
    exit 1
fi

# Get OpenAI key
read -p "💡 OpenAI API key (sk-...): " OPENAI_KEY
if [[ ! $OPENAI_KEY =~ ^sk- ]]; then
    echo "❌ Invalid OpenAI key format"
    exit 1
fi

echo ""
echo "🔧 Creating credentials.yaml..."

# Copy template and replace keys
sed -e "s/sk-ant-YOUR_ANTHROPIC_API_KEY_HERE/$ANTHROPIC_KEY/" \
    -e "s/sk-YOUR_OPENAI_API_KEY_HERE/$OPENAI_KEY/" \
    config/quick_credentials_template.yaml > config/credentials.yaml

echo "✅ Credentials file created!"
echo ""
echo "🚀 Next steps:"
echo "1. Restart Flask server: python3 web/app.py"
echo "2. Test integration: python3 test_ai_integration.py"
echo "3. Visit: http://localhost:3000"
echo ""
echo "🎉 You should now see real AI responses!"